"""
api module 
реализует CRUD-операции и кастомные эндпоинты для управления:
- Парковочными зонами (Zone)
- Парковочными местами (ParkingSlot)
- Бронированиями (Reservation)
- Заявлениями об угоне (TheftReport)

возможности:
- Проверка доступности мест на заданное время
- Защита от double booking через транзакции БД
- Статистика и аналитика бронирований
- Экстренная кнопка сообщения об угоне

эндпоинты:
- /api/zones/ — управление зонами
- /api/slots/ — управление местами
- /api/reservations/ — управление бронированиями
- /api/theft-reports/ — управление заявлениями об угон
"""
import email
from email.policy import default


from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.utils import timezone
from django.db import transaction
from django.db.models import Count, Q
from .models import Zone, ParkingSlot, Reservation, TheftReport
from .serializers import (
    ZoneSerializer, ParkingSlotSerializer,
    ReservationSerializer, ReservationCreateSerializer,
    TheftReportSerializer
)
class ZoneViewSet(viewsets.ModelViewSet):
    queryset = Zone.objects.all()
    serializer_class = ZoneSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def availability(self, request):
        zones = Zone.objects.all()
        data = []

        for zone in zones:
            load = zone.get_current_load()
            data.append({
                'id': zone.id,
                'name': zone.name,
                'zone_type': zone.zone_type,
                'capacity': zone.capacity,
                'load_percentage': round(load,2),
                'availability_probability': round(max(0,100 - load), 2)

            })

        return Response(data)

    @action(detail=False, methods=['get'])
    def recommendations(self, request):
        zones = Zone.objects.all()
        recommendations = []

        for zone in zones:
            load = zone.get_current_load()
            recommendations.append({
                'zone_id': zone.id,
                'zone_name': zone.name,
                'zone_type': zone.zone_type,
                'load_percentage': round(load, 2),
                'recommendation_score': round(100 - load, 2),
                'message': self._get_recommendation_message(load)
            })

        recommendations.sort(key=lambda x: x['recommendation_score'], reverse=True)

        return Response(recommendations)

    def _get_recommendation_message(self, load):

        if load < 30:
            return "Много свободных мест"
        elif load < 60:
            return "Нормальная загруженность"
        elif load < 80:
            return "Высокая загруженность, рассмотрите альтернативу"
        else:
            return "Очень высокая загруженность"

class ParkingSlotViewSet(viewsets.ModelViewSet):
    queryset = ParkingSlot.objects.all()
    serializer_class = ParkingSlotSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['get'])
    def available(self, request):
        now = timezone.now()
        slots = ParkingSlot.objects.filter(
            is_active=True,
            is_occupied=False
        ).exclude(
            reservations__status__in=['active', 'pending'],
            reservations__start_time__lte=now,
            reservations__end_time__gt=now
        )

        serializer = self.get_serializer(slots, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def least_loaded(self, request):
        best_zone = ParkingSlot.get_least_loaded_zone()

        if not best_zone:
            return Response(
                {'error': 'Нет доступных зон'},
                status=status.HTTP_404_NOT_FOUND
            )

        now = timezone.now()
        available_slot = ParkingSlot.objects.filter(
            zone=best_zone,
            is_active=True,
            is_occupied=False
        ).exclude(
            reservations__status__in=['active', 'pending'],
            reservations__start_time__lte=now,
            reservations__end_time__gt=now
        ).first()

        if not available_slot:
            return Response({
                'zone_id': best_zone.id,
                'zone_name': best_zone.name,
                'zone_load': round(best_zone.get_current_load(), 2),
                'message': 'В этой зоне нет свободных мест',
                'alternative': 'Рассмотрите другую зону',
                'algorithm': 'greedy_least_loaded'
            })

        return Response({
            'zone_id': best_zone.id,
            'zone_name': best_zone.name,
            'zone_type': best_zone.zone_type,
            'zone_load': round(best_zone.get_current_load(), 2),
            'recommended_slot_id': available_slot.id,
            'recommended_slot_number': available_slot.number,
            'algorithm': 'greedy_least_loaded'
        })

    @action(detail=True, methods=['post'])
    def check_availability(self, request, pk=None):
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
            'slot_number': slot.number,
            'zone_name': slot.zone.name,
            'is_available': is_available
        })

    @action(detail=False, methods=['get'])
    def map(self, request):
        slots = ParkingSlot.objects.filter(is_active=True).select_related('zone')
        now = timezone.now()

        data = []
        for slot in slots:
            is_booked = slot.reservations.filter(
                status__in = ['active', 'pending'],
                start_time__lte=now,
                end_time__gte=now
            ).exists()

            data.append({
                'id': slot.id,
                'number': slot.number,
                'zone_id': slot.zone.id,
                'zone_name': slot.zone.name,
                'zone_type': slot.zone.zone_type,
                'position_x': slot.position_x,
                'position_y': slot.position_y,
                'is_occupied': slot.is_occupied,
                'is_booked': is_booked,
                'is_available': not slot.is_occupied and not is_booked
            })

        return Response(data)

class ReservationViewSet(viewsets.ModelViewSet):
    queryset = Reservation.objects.all()
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == 'create':
            return ReservationCreateSerializer
        return ReservationSerializer

    @action(detail=False, methods=['get'])
    def statistics(self,request):
        now = timezone.now()
        stats = {
            'total': Reservation.objects.count(),
            'active': Reservation.objects.filter(status='active').count(),
            'pending': Reservation.objects.filter(status='pending').count(),
            'completed': Reservation.objects.filter(status='completed').count(),
            'cancelled': Reservation.objects.filter(status='cancelled').count(),
            'no_show': Reservation.objects.filter(status='no_show').count(),
            'today': Reservation.objects.filter(
                start_time__date=now.date()
            ).count(),
            'this_week': Reservation.objects.filter(
                start_time__gte=now - timezone.timedelta(days=7)
            ).count()
        }

        return Response(stats)

    @action(detail=False, methods=['get'])
    def active(self,request):
        active_reservations = Reservation.objects.filter(status='active')
        serializer = self.get_serializer(active_reservations, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=['get'])
    def my_reservations(self,request):
        email = request.query_params.get('email')
        phone = request.query_params.get('phone')

        if not email and not phone:
            return Response(
                {'error': 'Укажите email или phone'},
                status=status.HTTP_400_BAD_REQUEST
            )

        query = Q()
        if email:
            query |= Q(user_email=email)
        if phone:
            query |= Q(user_phone=phone)

        reservations = Reservation.objects.filter(
            query,
            status__in=['active', 'pending']
        )

        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=['post'])
    def cancel(self,request,pk = None):
        reservation = self.get_object()

        if not reservation.can_cancel:
            return Response(
                {'error' : 'Отмена возможно не позднее чем за 30 минут.'},
                status=status.HTTP_400_BAD_REQUEST
            )

        reservation.status = 'cancelled'
        reservation.canceled_at = timezone.now()
        reservation.save()

        return Response({
            'status' : 'canceled',
            'booking_code': reservation.booking_code,
            'message' : 'Бронирование отменено'
        })

    @action(detail=True, methods=['post'])
    def confrim(self,request, pk=None):
        reservation = self.get_object()
        reservation.status = 'active'
        reservation.confirmed_at = timezone.now()
        reservation.save()

        return Response({
            'status': 'confirmed',
            'booking_code': reservation.booking_code
        })

    @action(detail=False, methods=['get'])
    def check_conflicts(self, request):
        slot_id = request.query_params.get('slot_id')
        start_time = request.query_params.get('start_time')
        end_time = request.query_params.get('end_time')

        if not all([slot_id, start_time, end_time]):
            return Response(
                {'error': 'Укажите slot_id, start_time и end_time'},
                status=status.HTTP_400_BAD_REQUEST
            )

        conflicts = Reservation.objects.filter(
            slot_id=slot_id,
            status__in=['active', 'pending'],
            start_time__lt=end_time,
            end_time__gt=start_time
        )

        return Response({
            'has_conflicts': conflicts.exists(),
            'conflicts_count': conflicts.count()
        })

    @action(detail=False, methods=['post'])
    def quick_book(self,request):

        from django.db import DatabaseError

        slot_id = request.data.get('slot_id')
        user_name = request.data.get('user_name')
        user_phone = request.data.get('user_phone')
        user_email = request.data.get('user_email')
        start_time = request.data.get('start_time')
        end_time = request.data.get('end_time')
        is_guest = request.data.get('is_guest', True)

        if not all([slot_id, user_name, user_phone, start_time, end_time]):
            return Response(
                {'error' : 'Укажите обязатаельные поля'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            with transaction.atomic():
                slot = ParkingSlot.objects.select_fot_update().get(id=slot_id)

                if not slot.is_active:
                    return Response({'error' : 'Место временно недоступно'}, status=status.HTTP_400_BAD_REQUEST)

                if not slot.is_available_for_booking(start_time, end_time):
                    return Response({'error' : 'Место забронировано на это время'}, status=status.HTTP_400_BAD_REQUEST)

                reservation = Reservation.objects.create(
                    slot = slot,
                    user_name = user_name,
                    user_phone=user_phone,
                    user_email=user_email,
                    is_guest=is_guest,
                    start_time=start_time,
                    end_time=end_time,
                    status='pending'
                )

                serializer = ReservationSerializer(reservation)

                return Response({
                    'success': True,
                    'booking_code': reservation.booking_code,
                    'message': 'Бронирование создано',
                    'data': serializer.data
                }, status=status.HTTP_201_CREATED)

        except ParkingSlot.DoesNotExist:
            return Response(
                {'error': 'Место не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )
        except DatabaseError as e:
            return Response(
                {'error': 'Ошибка базы данных. Попробуйте ещё раз.'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class TheftReportViewSet(viewsets.ModelViewSet):
    queryset = TheftReport.objects.all()
    serializer_class = TheftReportSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=['post'])
    def emergency(self, request):
        booking_code = request.data.get('booking_code')
        user_name = request.data.get('user_name')
        user_phone = request.data.get('user_phone')
        description = request.data.get('description', '')

        if not booking_code:
            return Response(
                {'error': 'Укажите код бронирования'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            reservation = Reservation.objects.get(booking_code=booking_code)
        except Reservation.DoesNotExist:
            return Response(
                {'error': 'Бронирование не найдено'},
                status=status.HTTP_404_NOT_FOUND
            )

        report = TheftReport.objects.create(
            reservation=reservation,
            user_name=user_name or reservation.user_name,
            user_phone=user_phone or reservation.user_phone,
            description=description
        )

        return Response({
            'report_id': report.id,
            'status': 'new',
            'message': 'Заявление отправлено. Ожидайте связи.',
            'police_info': 'Также рекомендуем обратиться в полицию по телефону 102'
        }, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        report = self.get_object()
        new_status = request.data.get('status')

        valid_statuses = ['new', 'in_progress', 'resolved', 'false_alarm']
        if new_status not in valid_statuses:
            return Response(
                    {'error': f'Допустимые статусы: {valid_statuses}'},
                    status=status.HTTP_400_BAD_REQUEST
            )

        report.status = new_status
        if new_status in ['resolved', 'false_alarm']:
            from django.utils import timezone
            report.resolved_at = timezone.now()
        report.save()

        return Response({
            'status': report.status,
            'resolved_at': report.resolved_at
        })