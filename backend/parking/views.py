from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.db import transaction, DatabaseError
from django.db.models import Q
from django.utils import timezone
from datetime import datetime

from .models import Zone, ParkingSlot, Reservation
from .serializers import (
    ZoneSerializer,
    ParkingSlotSerializer,
    ReservationSerializer,
)


# ============================================================================
# ZONE VIEWSET
# ============================================================================
class ZoneViewSet(viewsets.ModelViewSet):
    """API для управления зонами парковки"""
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [AllowAny()]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    @action(detail=False, methods=['get'])
    def availability(self, request):
        """Получить доступные зоны"""
        zones = Zone.objects.filter(is_active=True)
        serializer = self.get_serializer(zones, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        """Получить рекомендации по зонам"""
        zones = Zone.objects.filter(is_active=True).order_by('priority')
        zones_with_load = []
        for zone in zones:
            load = zone.get_current_load()
            zones_with_load.append({
                'zone': ZoneSerializer(zone).data,
                'load': load
            })
        zones_with_load.sort(key=lambda x: x['load'])
        return Response(zones_with_load[:5])


# ============================================================================
# PARKING SLOT VIEWSET
# ============================================================================
class ParkingSlotViewSet(viewsets.ModelViewSet):
    """API для управления парковочными местами"""
    queryset = ParkingSlot.objects.all().select_related('zone')
    serializer_class = ParkingSlotSerializer
    permission_classes = [AllowAny()]
    
    def get_permissions(self):
        if self.action in ['create', 'update', 'partial_update', 'destroy']:
            return [IsAuthenticated()]
        return [AllowAny()]
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        """Получить свободные места"""
        slots = ParkingSlot.objects.filter(
            is_active=True,
            is_occupied=False
        ).select_related('zone')
        serializer = self.get_serializer(slots, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def least_loaded(self, request):
        """Получить места в наименее загруженной зоне"""
        zones = Zone.objects.filter(is_active=True)
        min_load = 100
        best_zone = None
        for zone in zones:
            load = zone.get_current_load()
            if load < min_load:
                min_load = load
                best_zone = zone
        if best_zone:
            slots = ParkingSlot.objects.filter(
                zone=best_zone,
                is_active=True,
                is_occupied=False
            )
            serializer = self.get_serializer(slots, many=True)
            return Response(serializer.data)
        return Response([])
    
    @action(detail=True, methods=['post'])
    def check_availability(self, request, pk=None):
        """Проверить доступность места на время"""
        slot = self.get_object()
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        if not start_time or not end_time:
            return Response(
                {'error': 'Укажите start_time и end_time'},
                status=status.HTTP_400_BAD_REQUEST
            )
        is_available = slot.is_available_for_booking(start_time, end_time)
        return Response({
            'slot_id': slot.id,
            'available': is_available,
            'start_time': start_time,
            'end_time': end_time
        })


# ============================================================================
# RESERVATION VIEWSET - ИСПРАВЛЕННЫЙ
# ============================================================================
class ReservationViewSet(viewsets.ModelViewSet):
    """API для управления бронированиями"""
    queryset = Reservation.objects.all().select_related('slot', 'slot__zone', 'user')
    serializer_class = ReservationSerializer
    permission_classes = [IsAuthenticated()]
    
    def get_permissions(self):
        if self.action in ['create', 'my_reservations', 'active', 'statistics']:
            return [IsAuthenticated()]
        if self.action in ['quick_book']:
            return [AllowAny()]
        return [IsAuthenticated()]
    
    def get_queryset(self):
        user = self.request.user
        if user.is_staff:
            return Reservation.objects.all()
        return Reservation.objects.filter(
            Q(user=user) | Q(guest_email=user.email)
        )
    
    @action(detail=False, methods=['get'])
    def my_reservations(self, request):
        """Получить мои бронирования"""
        user = request.user
        reservations = Reservation.objects.filter(
            Q(user=user) | Q(guest_email=user.email)
        ).order_by('-created_at')
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить активные бронирования"""
        user = request.user
        reservations = Reservation.objects.filter(
            (Q(user=user) | Q(guest_email=user.email)) &
            Q(status='active') &
            Q(end_time__gte=timezone.now())
        ).order_by('start_time')
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def quick_book(self, request):
        """Быстрое бронирование - С ПОЛНЫМ ЛОГИРОВАНИЕМ"""
        import traceback, logging
        logger = logging.getLogger(__name__)
        
        try:
            logger.warning("=== QUICK_BOOK START ===")
            
            slot_id = request.data.get('slot_id')
            guest_name = request.data.get('guest_name') or request.data.get('user_name')
            guest_phone = request.data.get('guest_phone') or request.data.get('user_phone')
            guest_email = request.data.get('guest_email') or request.data.get('user_email')
            start_time = request.data.get('start_time')
            end_time = request.data.get('end_time')
            is_guest = request.data.get('is_guest', True)
            
            logger.warning(f"Input: slot={slot_id}, guest={guest_name}, times={start_time} to {end_time}")
            
            if not all([slot_id, start_time, end_time]):
                return Response({'error': 'Укажите slot_id, start_time, end_time'}, status=status.HTTP_400_BAD_REQUEST)
            
            # Конвертация дат
            if isinstance(start_time, str):
                start_time = start_time.replace('Z', '')
                start_time = timezone.make_aware(datetime.fromisoformat(start_time))
            if isinstance(end_time, str):
                end_time = end_time.replace('Z', '')
                end_time = timezone.make_aware(datetime.fromisoformat(end_time))
            logger.warning(f"Dates OK: {start_time} - {end_time}")
            
            with transaction.atomic():
                slot = ParkingSlot.objects.select_for_update().get(id=slot_id)
                logger.warning(f"Slot found: {slot}, active={slot.is_active}")
                
                if not slot.is_active:
                    return Response({'error': 'Место недоступно'}, status=status.HTTP_400_BAD_REQUEST)
                
                if not slot.is_available_for_booking(start_time, end_time):
                    return Response({'error': 'Место занято'}, status=status.HTTP_400_BAD_REQUEST)
                
                if is_guest or not request.user.is_authenticated:
                    if not all([guest_name, guest_phone, guest_email]):
                        return Response({'error': 'Заполните имя, телефон, email'}, status=status.HTTP_400_BAD_REQUEST)
                    
                    logger.warning("Creating GUEST reservation")
                    reservation = Reservation.objects.create(
                        slot=slot, is_guest=True,
                        guest_name=guest_name, guest_phone=guest_phone, guest_email=guest_email,
                        start_time=start_time, end_time=end_time, status='pending'
                    )
                else:
                    logger.warning("Creating USER reservation")
                    reservation = Reservation.objects.create(
                        slot=slot, user=request.user, is_guest=False,
                        start_time=start_time, end_time=end_time, status='pending'
                    )
                
                logger.warning(f"✅ Created: {reservation.booking_code}")
                serializer = self.get_serializer(reservation)
                return Response({
                    'success': True, 'booking_code': reservation.booking_code,
                    'message': 'Бронирование создано', 'data': serializer.data
                }, status=status.HTTP_201_CREATED)
                
        except Exception as e:
            logger.error(f"❌ CRITICAL ERROR: {type(e).__name__}: {e}")
            logger.error(f"TRACEBACK:\n{traceback.format_exc()}")
            return Response({'error': f'{type(e).__name__}: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        """Отменить бронирование"""
        reservation = self.get_object()
        if reservation.status == 'completed':
            return Response(
                {'error': 'Нельзя отменить завершённое бронирование'},
                status=status.HTTP_400_BAD_REQUEST
            )
        reservation.status = 'cancelled'
        reservation.cancelled_at = timezone.now()
        reservation.save()
        return Response({'success': True, 'message': 'Бронирование отменено'})
    
    @action(detail=True, methods=['post'])
    def confirm(self, request, pk=None):
        """Подтвердить бронирование"""
        reservation = self.get_object()
        if reservation.status != 'pending':
            return Response(
                {'error': 'Можно подтвердить только ожидающее бронирование'},
                status=status.HTTP_400_BAD_REQUEST
            )
        reservation.status = 'active'
        reservation.confirmed_at = timezone.now()
        reservation.save()
        return Response({'success': True, 'message': 'Бронирование подтверждено'})
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        """Получить статистику бронирований"""
        user = request.user
        total = Reservation.objects.filter(
            Q(user=user) | Q(guest_email=user.email)
        ).count()
        active = Reservation.objects.filter(
            (Q(user=user) | Q(guest_email=user.email)) & Q(status='active')
        ).count()
        completed = Reservation.objects.filter(
            (Q(user=user) | Q(guest_email=user.email)) & Q(status='completed')
        ).count()
        cancelled = Reservation.objects.filter(
            (Q(user=user) | Q(guest_email=user.email)) & Q(status='cancelled')
        ).count()
        return Response({
            'total': total,
            'active': active,
            'completed': completed,
            'cancelled': cancelled
        })

# ============================================================================
# OCCUPANCY HISTORY VIEWSET (закомментирован)
# ============================================================================
# class OccupancyHistoryViewSet(viewsets.ModelViewSet):
#     queryset = OccupancyHistory.objects.all().select_related('zone')
#     serializer_class = OccupancyHistorySerializer
#     permission_classes = [IsAuthenticated]


# ============================================================================
# THEFT REPORT VIEWSET (закомментирован)
# ============================================================================
# class TheftReportViewSet(viewsets.ModelViewSet):
#     queryset = TheftReport.objects.all()
#     serializer_class = TheftReportSerializer
#     permission_classes = [IsAuthenticated]


# ============================================================================
# CAMERA LOG VIEWSET (закомментирован)
# ============================================================================
# class CameraLogViewSet(viewsets.ModelViewSet):
#     queryset = CameraLog.objects.all().select_related('slot', 'reservation')
#     serializer_class = CameraLogSerializer
#     permission_classes = [IsAuthenticated]