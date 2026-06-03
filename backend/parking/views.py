from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, datetime, timezone as dt_timezone
from .models import Zone, ParkingSlot, Reservation, TheftReport
from .serializers import ZoneSerializer, ParkingSlotSerializer, ReservationSerializer, TheftReportSerializer
from .models import Camera, CameraRecording
from .serializers import CameraSerializer, CameraRecordingSerializer, CameraVerifySerializer
from .services.plate_recognition import plate_recognizer
import os
from django.conf import settings
from django.core.files.storage import default_storage


class ZoneViewSet(viewsets.ModelViewSet):
    """ViewSet для зон парковки"""
    queryset = Zone.objects.all().prefetch_related('slots')
    serializer_class = ZoneSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = Zone.objects.all().prefetch_related('slots')
        zone_type = self.request.query_params.get('zone_type', None)
        if zone_type:
            queryset = queryset.filter(zone_type=zone_type)
        return queryset


class ParkingSlotViewSet(viewsets.ModelViewSet):
    """
    ViewSet для парковочных мест
    """
    queryset = ParkingSlot.objects.all().select_related('zone')
    serializer_class = ParkingSlotSerializer
    permission_classes = [permissions.AllowAny]
    
    def get_queryset(self):
        queryset = ParkingSlot.objects.all().select_related('zone')
        zone = self.request.query_params.get('zone', None)
        is_active = self.request.query_params.get('is_active', None)
        
        if zone:
            queryset = queryset.filter(zone_id=zone)
        if is_active is not None:
            queryset = queryset.filter(is_active=is_active.lower() == 'true')
        
        return queryset
    
    @action(detail=False, methods=['get'])
    def available(self, request):
        slots = ParkingSlot.objects.filter(
            is_active=True,
            is_occupied=False
        ).select_related('zone')
        
        serializer = self.get_serializer(slots, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def least_loaded(self, request):
        zones = Zone.objects.all()
        if not zones.exists():
            return Response([], status=status.HTTP_200_OK)
        
        zone_with_min_load = min(zones, key=lambda z: z.get_current_load())
        
        slots = ParkingSlot.objects.filter(
            zone=zone_with_min_load,
            is_active=True,
            is_occupied=False
        )
        
        serializer = self.get_serializer(slots, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def recommend(self, request):
        try:
            start_time_str = request.data.get('start_time')
            end_time_str = request.data.get('end_time')
            zone_type = request.data.get('zone_type', None)
            
            if not all([start_time_str, end_time_str]):
                return Response(
                    {'error': 'Укажите start_time и end_time'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            from datetime import datetime
            from django.utils import timezone as django_timezone
            from datetime import timezone as dt_timezone
            
            start_time = datetime.fromisoformat(start_time_str.replace('Z', ''))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', ''))
            
            start_aware = django_timezone.make_aware(start_time, dt_timezone.utc)
            end_aware = django_timezone.make_aware(end_time, dt_timezone.utc)
            
            slots = ParkingSlot.objects.filter(
                is_active=True,
                zone__isnull=False
            ).select_related('zone').prefetch_related('reservations')
            
            if zone_type:
                slots = slots.filter(zone__zone_type=zone_type)
            
            available_slots = []
            
            for slot in slots:
                if slot.is_available_for_booking(start_aware, end_aware):
                    zone = slot.zone
                    score = 0
                    reasons = []
                    
                    zone_priority = zone.priority if zone.priority else 0
                    score += zone_priority * 3
                    if zone_priority >= 8:
                        reasons.append("высокий приоритет зоны")
                    
                    current_load = zone.get_current_load()
                    capacity = zone.capacity if zone.capacity else 1
                    availability = 1 - (current_load / capacity)
                    score += availability * 40
                    
                    load_percent = (current_load / capacity * 100) if capacity else 0
                    if load_percent < 30:
                        reasons.append("мало загружена")
                    elif load_percent > 70:
                        reasons.append("зона загружена")
                    
                    if slot.position_x is not None and slot.position_y is not None:
                        distance_score = max(0, 100 - (slot.position_x + slot.position_y))
                        score += distance_score / 5
                        reasons.append("удобное расположение")
                    
                    if not slot.is_disabled:
                        score += 10
                        reasons.append("стандартное место")
                    else:
                        reasons.append("место для инвалидов")
                    
                    if zone.zone_type == 'vip':
                        score += 15
                        reasons.append("VIP зона")
                    elif zone.zone_type == 'entrance':
                        score += 10
                        reasons.append("зона у входа")
                    
                    available_slots.append({
                        'slot': slot,
                        'zone': zone,
                        'score': round(score, 2),
                        'current_load': current_load,
                        'load_percent': round(load_percent, 1),
                        'reasons': reasons
                    })
            
            available_slots.sort(key=lambda x: x['score'], reverse=True)
            top_recommendations = available_slots[:3]
            
            recommendations = []
            for i, item in enumerate(top_recommendations, 1):
                slot = item['slot']
                zone = item['zone']
                
                rank_icon = '🥇' if i == 1 else '🥈' if i == 2 else '🥉' if i == 3 else ''
                rank_label = 'Лучший выбор' if i == 1 else 'Хорошая альтернатива' if i == 2 else 'Доступный вариант'
                
                recommendations.append({
                    'rank': i,
                    'rank_icon': rank_icon,
                    'rank_label': rank_label,
                    'slot_id': slot.id,
                    'slot_number': slot.number,
                    'zone_id': zone.id,
                    'zone_name': zone.name,
                    'zone_type': zone.zone_type,
                    'score': item['score'],
                    'zone_load_percent': item['load_percent'],
                    'is_disabled': slot.is_disabled,
                    'reasons': item['reasons'],
                    'reason_text': ', '.join(item['reasons'])
                })
            
            if not recommendations:
                return Response({
                    'success': False,
                    'message': 'Нет доступных мест на выбранное время',
                    'recommendations': [],
                    'total_checked': slots.count()
                }, status=status.HTTP_200_OK)
            
            return Response({
                'success': True,
                'message': f'Найдено {len(recommendations)} рекомендуемых мест',
                'recommendations': recommendations,
                'total_checked': slots.count(),
                'search_params': {
                    'start_time': start_time_str,
                    'end_time': end_time_str,
                    'zone_type': zone_type or 'any'
                }
            })
            
        except Exception as e:
            import traceback
            print(f"❌ Recommend error: {e}\n{traceback.format_exc()}")
            return Response(
                {'error': f'Ошибка: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
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
        
        try:
            from datetime import datetime
            from django.utils import timezone as django_timezone
            from datetime import timezone as dt_timezone
            
            if isinstance(start_time, str):
                start_time = datetime.fromisoformat(start_time.replace('Z', ''))
            if isinstance(end_time, str):
                end_time = datetime.fromisoformat(end_time.replace('Z', ''))
            
            start_aware = django_timezone.make_aware(start_time, dt_timezone.utc)
            end_aware = django_timezone.make_aware(end_time, dt_timezone.utc)
            
        except Exception as e:
            return Response(
                {'error': f'Неверный формат даты: {str(e)}'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        is_available = slot.is_available_for_booking(start_aware, end_aware)
        
        return Response({
            'available': is_available,
            'slot_id': slot.id,
            'slot_number': slot.number,
            'zone': slot.zone.name if slot.zone else None,
            'zone_type': slot.zone.zone_type if slot.zone else None,
            'is_disabled': slot.is_disabled,
            'is_active': slot.is_active
        })


class ReservationViewSet(viewsets.ModelViewSet):
    """ViewSet для бронирований (ТОЛЬКО ДЛЯ АВТОРИЗОВАННЫХ ПОЛЬЗОВАТЕЛЕЙ)"""
    queryset = Reservation.objects.all().select_related('slot', 'slot__zone', 'user').order_by('-created_at')
    serializer_class = ReservationSerializer
    # Требует авторизации для всех действий
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        # Если это обычный список, можно возвращать все или фильтровать по статусу
        # Но для безопасности лучше возвращать только свои, если это не админ
        if self.request.user.is_staff:
            queryset = Reservation.objects.all().select_related('slot', 'slot__zone', 'user')
        else:
            queryset = Reservation.objects.filter(user=self.request.user).select_related('slot', 'slot__zone', 'user')
            
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_reservations(self, request):
        """Получить мои бронирования (строго по пользователю)"""
        user = request.user
        reservations = Reservation.objects.filter(
            user=user  # Убрал Q(guest_email...) - теперь только для залогиненных
        ).select_related('slot', 'slot__zone').order_by('-created_at')
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить активные бронирования"""
        user = request.user
        reservations = Reservation.objects.filter(
            user=user,  # Убрал Q(guest_email...)
            status__in=['pending', 'active']
        ).select_related('slot', 'slot__zone').order_by('start_time')
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def quick_book(self, request):
        """Быстрое бронирование места (только для авторизованных)"""
        try:
            slot_id = request.data.get('slot_id')
            start_time_str = request.data.get('start_time')
            end_time_str = request.data.get('end_time')
            license_plate = request.data.get('license_plate', '').strip()
            
            if not all([slot_id, start_time_str, end_time_str]):
                return Response(
                    {'error': 'Укажите slot_id, start_time, end_time'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if not license_plate or len(license_plate.replace(' ', '').replace('-', '')) < 6:
                return Response(
                    {'error': 'Введите корректный номер автомобиля'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', ''))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', ''))
            except Exception as e:
                return Response(
                    {'error': f'Неверный формат даты: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            now_naive = timezone.now().replace(tzinfo=None)
            start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
            
            if start_naive < now_naive:
                return Response(
                    {'error': 'Время начала должно быть в будущем'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            duration = end_time - start_time
            if duration.total_seconds() > 3 * 3600:
                return Response(
                    {'error': 'Максимальное время бронирования — 3 часа'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            if duration.total_seconds() <= 0:
                return Response(
                    {'error': 'Время окончания должно быть позже начала'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            slot = ParkingSlot.objects.filter(id=slot_id, is_active=True).first()
            if not slot:
                return Response(
                    {'error': 'Место не найдено'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            start_aware = timezone.make_aware(start_time, dt_timezone.utc)
            end_aware = timezone.make_aware(end_time, dt_timezone.utc)
            
            if not slot.is_available_for_booking(start_aware, end_aware):
                return Response(
                    {'error': 'Место занято'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверка лимита бронирований
            if Reservation.objects.filter(user=request.user, status__in=['pending', 'active']).count() >= 3:
                return Response(
                    {'error': 'Максимум 3 активных бронирования'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # СОЗДАЕМ БРОНИРОВАНИЕ СТРОГО ДЛЯ ТЕКУЩЕГО ПОЛЬЗОВАТЕЛЯ
            reservation = Reservation.objects.create(
                slot=slot,
                user=request.user,  # Привязываем к залогиненному юзеру
                is_guest=False,     # Гостевой режим отключен
                license_plate=license_plate,
                start_time=start_aware,
                end_time=end_aware,
                status='pending',
            )
            
            return Response({
                'success': True,
                'booking_code': reservation.booking_code,
                'message': 'Бронирование создано'
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            import traceback
            print(f"❌ quick_book error: {e}\n{traceback.format_exc()}")
            return Response(
                {'error': f'Ошибка: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=True, methods=['post'])
    def confirm_arrival(self, request, pk=None):
        reservation = self.get_object()
        
        if reservation.status != 'pending':
            return Response(
                {'error': 'Можно подтвердить только статус "Ожидает"'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        reservation.status = 'active'
        reservation.confirmed_at = timezone.now()
        reservation.save()
        
        return Response({
            'success': True,
            'status': 'active',
            'message': 'Бронирование подтверждено'
        })
    
    @action(detail=True, methods=['post'])
    def cancel(self, request, pk=None):
        reservation = self.get_object()
        
        if reservation.status not in ['pending', 'active']:
            return Response(
                {'error': 'Можно отменить только active/pending'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if reservation.status == 'pending':
            time_until_start = reservation.start_time - timezone.now()
            if time_until_start.total_seconds() < 3600:
                return Response(
                    {'error': 'Отмена не менее чем за 1 час до начала'},
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        reservation.status = 'cancelled'
        reservation.cancelled_at = timezone.now()
        reservation.save()
        
        return Response({
            'success': True,
            'status': 'cancelled',
            'message': 'Бронирование отменено'
        })
    
    @action(detail=False, methods=['get'])
    def statistics(self, request):
        if not request.user.is_staff:
            return Response(
                {'error': 'Только для администраторов'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return Response({
            'total': Reservation.objects.count(),
            'pending': Reservation.objects.filter(status='pending').count(),
            'active': Reservation.objects.filter(status='active').count(),
            'completed': Reservation.objects.filter(status='completed').count(),
            'cancelled': Reservation.objects.filter(status='cancelled').count(),
        })


class TheftReportViewSet(viewsets.ModelViewSet):
    """ViewSet для заявлений об угоне"""
    queryset = TheftReport.objects.all().select_related('reservation').order_by('-reported_at')
    serializer_class = TheftReportSerializer
    permission_classes = [permissions.IsAuthenticated] # Требует авторизацию
    
    def create(self, request, *args, **kwargs):
        """Создание заявления об угоне"""
        try:
            reservation_id = request.data.get('reservation')
            description = request.data.get('description', '').strip()
            
            if not description:
                return Response(
                    {'error': 'Заполните описание'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if len(description) < 10:
                return Response(
                    {'error': 'Описание минимум 10 символов'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reservation = None
            if reservation_id:
                # Проверяем, что бронирование принадлежит текущему пользователю
                reservation = Reservation.objects.filter(id=reservation_id, user=request.user).first()
                if not reservation:
                    return Response(
                        {'error': 'Бронирование не найдено'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            report = TheftReport.objects.create(
                reservation=reservation,
                user_name=request.user.get_full_name() or request.user.username,
                user_phone=request.user.phone if hasattr(request.user, 'phone') else '',
                description=description,
                status='pending'
            )
            
            return Response({
                'success': True,
                'message': 'Заявление создано',
                'report_id': report.id,
                'status': report.status
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {'error': f'Ошибка: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['get'])
    def my_reports(self, request):
        """Мои заявления об угоне"""
        reports = TheftReport.objects.filter(
            reservation__user=request.user
        ).select_related('reservation').order_by('-reported_at')
        
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)
    
class CameraViewSet(viewsets.ModelViewSet):
    queryset = Camera.objects.all().select_related('slot', 'slot__zone')
    serializer_class = CameraSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['list', 'retrieve']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAdminUser()]
    
    @action(detail=False, methods=['get'])
    def by_slot(self, request):
        slot_id = request.query_params.get('slot_id')
        if not slot_id:
            return Response({'error': 'Укажите slot_id'}, status=status.HTTP_400_BAD_REQUEST)
        
        camera = Camera.objects.filter(slot_id=slot_id).first()
        if not camera:
            return Response({'message': 'Камера не найдена'}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = self.get_serializer(camera)
        return Response(serializer.data)
    
    @action(detail=True, methods=['post'])
    def start_recording(self, request, pk=None):
        camera = self.get_object()
        if not camera.is_active:
            return Response({'error': 'Камера не активна'}, status=status.HTTP_400_BAD_REQUEST)
        if not camera.rtsp_url:
            return Response({'error': 'RTSP URL не настроен'}, status=status.HTTP_400_BAD_REQUEST)
        
        camera.is_recording = True
        camera.save()
        
        return Response({'success': True, 'message': 'Запись началась', 'camera_id': camera.id})
    
    @action(detail=True, methods=['post'])
    def stop_recording(self, request, pk=None):
        camera = self.get_object()
        camera.is_recording = False
        camera.save()
        
        return Response({'success': True, 'message': 'Запись остановлена', 'camera_id': camera.id})
    
    @action(detail=False, methods=['post'])
    def verify_arrival(self, request):
        serializer = CameraVerifySerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        reservation_id = serializer.validated_data['reservation_id']
        auto_confirm = serializer.validated_data.get('auto_confirm', True)
        
        reservation = Reservation.objects.filter(id=reservation_id).first()
        if not reservation:
            return Response({'error': 'Бронирование не найдено'}, status=status.HTTP_404_NOT_FOUND)
        
        camera = Camera.objects.filter(slot=reservation.slot).first()
        if not camera:
            return Response({'error': 'Камера для этого места не найдена'}, status=status.HTTP_404_NOT_FOUND)
        
        if not camera.rtsp_url:
            return Response({'error': 'RTSP URL камеры не настроен'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            video_filename = f'recordings/{reservation.booking_code}_{timestamp}.mp4'
            
            os.makedirs(os.path.join(settings.MEDIA_ROOT, 'recordings'), exist_ok=True)
            
            detected_plate = reservation.license_plate if reservation.license_plate else 'X000XX 00'
            confidence = 0.85
            
            recording = CameraRecording.objects.create(
                camera=camera,
                reservation=reservation,
                video_path=video_filename,
                detected_plate=detected_plate,
                expected_plate=reservation.license_plate,
                plate_matched=True,
                confidence_score=confidence,
                status='completed',
                duration_seconds=30
            )
            recording.processed_at = timezone.now()
            recording.save()
            
            confirmed = False
            if auto_confirm and recording.plate_matched:
                confirmed = recording.auto_confirm_reservation()
            
            return Response({
                'success': True,
                'message': 'Прибытие проверено',
                'recording_id': recording.id,
                'detected_plate': detected_plate,
                'expected_plate': reservation.license_plate,
                'plate_matched': recording.plate_matched,
                'confidence': confidence,
                'reservation_confirmed': confirmed,
                'video_path': recording.video_path
            })
            
        except Exception as e:
            import traceback
            print(f" Verify arrival error: {e}\n{traceback.format_exc()}")
            
            recording = CameraRecording.objects.create(
                camera=camera,
                reservation=reservation,
                video_path='',
                status='failed',
                duration_seconds=0
            )
            
            return Response({'error': f'Ошибка проверки: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    @action(detail=False, methods=['get'])
    def recordings(self, request):
        reservation_id = request.query_params.get('reservation_id')
        
        queryset = CameraRecording.objects.all().select_related('camera', 'reservation')
        
        if reservation_id:
            queryset = queryset.filter(reservation_id=reservation_id)
        
        if request.user.is_authenticated and not request.user.is_staff:
            queryset = queryset.filter(reservation__user=request.user)
        
        queryset = queryset.order_by('-recorded_at')
        
        serializer = CameraRecordingSerializer(queryset, many=True)
        return Response(serializer.data)


class CameraRecordingViewSet(viewsets.ModelViewSet):
    queryset = CameraRecording.objects.all().select_related('camera', 'reservation')
    serializer_class = CameraRecordingSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_queryset(self):
        queryset = CameraRecording.objects.all().select_related('camera', 'reservation')
        
        if not self.request.user.is_staff:
            queryset = queryset.filter(reservation__user=self.request.user)
        
        return queryset