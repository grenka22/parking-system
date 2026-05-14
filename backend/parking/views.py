from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from django.db.models import Q
from django.utils import timezone
from datetime import timedelta, datetime, timezone as dt_timezone
from .models import Zone, ParkingSlot, Reservation, TheftReport
from .serializers import ZoneSerializer, ParkingSlotSerializer, ReservationSerializer, TheftReportSerializer


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
        """
        Оптимизируем запросы с фильтрацией
        """
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
        """
        Получить все свободные места
        """
        slots = ParkingSlot.objects.filter(
            is_active=True,
            is_occupied=False
        ).select_related('zone')
        
        serializer = self.get_serializer(slots, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def least_loaded(self, request):
        """
        Получить места в наименее загруженной зоне
        """
        zones = Zone.objects.all()
        if not zones.exists():
            return Response([], status=status.HTTP_200_OK)
        
        # Находим зону с наименьшей загруженностью
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
        """
        Умная рекомендация лучшего места на основе времени бронирования
        
        Критерии (без учёта цены):
        1. Доступность на всё время бронирования
        2. Приоритет зоны (чем выше — тем лучше)
        3. Загруженность зоны (менее загруженные предпочтительнее)
        4. Расположение места (ближе к входу/выходу)
        5. Тип места (не инвалидное по умолчанию)
        """
        try:
            start_time_str = request.data.get('start_time')
            end_time_str = request.data.get('end_time')
            zone_type = request.data.get('zone_type', None)
            
            if not all([start_time_str, end_time_str]):
                return Response(
                    {'error': 'Укажите start_time и end_time'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Парсинг дат
            from datetime import datetime
            from django.utils import timezone as django_timezone
            from datetime import timezone as dt_timezone
            
            start_time = datetime.fromisoformat(start_time_str.replace('Z', ''))
            end_time = datetime.fromisoformat(end_time_str.replace('Z', ''))
            
            start_aware = django_timezone.make_aware(start_time, dt_timezone.utc)
            end_aware = django_timezone.make_aware(end_time, dt_timezone.utc)
            
            # Получаем все активные места с зонами
            slots = ParkingSlot.objects.filter(
                is_active=True,
                zone__isnull=False
            ).select_related('zone').prefetch_related('reservations')
            
            if zone_type:
                slots = slots.filter(zone__zone_type=zone_type)
            
            # Фильтруем доступные места и рассчитываем score
            available_slots = []
            
            for slot in slots:
                # Проверка доступности на выбранное время
                if slot.is_available_for_booking(start_aware, end_aware):
                    zone = slot.zone
                    score = 0
                    reasons = []
                    
                    # 1. Приоритет зоны (макс +30 баллов)
                    zone_priority = zone.priority if zone.priority else 0
                    score += zone_priority * 3
                    if zone_priority >= 8:
                        reasons.append("высокий приоритет зоны")
                    
                    # 2. Загруженность зоны (макс +40 баллов)
                    current_load = zone.get_current_load()
                    capacity = zone.capacity if zone.capacity else 1
                    availability = 1 - (current_load / capacity)
                    score += availability * 40
                    
                    load_percent = (current_load / capacity * 100) if capacity else 0
                    if load_percent < 30:
                        reasons.append("мало загружена")
                    elif load_percent > 70:
                        reasons.append("зона загружена")
                    
                    # 3. Расположение места (макс +20 баллов)
                    if slot.position_x is not None and slot.position_y is not None:
                        # Ближе к началу координат = ближе к входу = лучше
                        distance_score = max(0, 100 - (slot.position_x + slot.position_y))
                        score += distance_score / 5
                        reasons.append("удобное расположение")
                    
                    # 4. Не инвалидное место (по умолчанию) (макс +10 баллов)
                    if not slot.is_disabled:
                        score += 10
                        reasons.append("стандартное место")
                    else:
                        reasons.append("место для инвалидов")
                    
                    # 5. Бонус за тип зоны
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
            
            # Сортируем по score (по убыванию — лучшие первые)
            available_slots.sort(key=lambda x: x['score'], reverse=True)
            
            # Берем топ-3 рекомендации
            top_recommendations = available_slots[:3]
            
            # Формируем ответ
            recommendations = []
            for i, item in enumerate(top_recommendations, 1):
                slot = item['slot']
                zone = item['zone']
                
                # Определяем ранг и иконку
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
        """
        Проверить доступность конкретного места на указанное время
        """
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
    """ViewSet для бронирований"""
    queryset = Reservation.objects.all().select_related('slot', 'slot__zone', 'user').order_by('-created_at')
    serializer_class = ReservationSerializer
    permission_classes = [permissions.IsAuthenticated]
    
    def get_permissions(self):
        if self.action in ['quick_book']:
            return [permissions.AllowAny()]
        elif self.action in ['my_reservations', 'active']:
            return [permissions.IsAuthenticated()]
        return [permissions.IsAuthenticated()]
    
    def get_queryset(self):
        queryset = Reservation.objects.all().select_related('slot', 'slot__zone', 'user')
        status_param = self.request.query_params.get('status', None)
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset
    
    @action(detail=False, methods=['get'])
    def my_reservations(self, request):
        """Получить мои бронирования"""
        user = request.user
        reservations = Reservation.objects.filter(
            Q(user=user) | Q(guest_email=user.email)
        ).select_related('slot', 'slot__zone').order_by('-created_at')
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['get'])
    def active(self, request):
        """Получить активные бронирования"""
        user = request.user
        reservations = Reservation.objects.filter(
            Q(user=user) | Q(guest_email=user.email),
            status__in=['pending', 'active']
        ).select_related('slot', 'slot__zone').order_by('start_time')
        serializer = self.get_serializer(reservations, many=True)
        return Response(serializer.data)
    
    @action(detail=False, methods=['post'])
    def quick_book(self, request):
        """Быстрое бронирование места"""
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
            
            # Парсинг дат (naive datetime)
            try:
                start_time = datetime.fromisoformat(start_time_str.replace('Z', ''))
                end_time = datetime.fromisoformat(end_time_str.replace('Z', ''))
            except Exception as e:
                return Response(
                    {'error': f'Неверный формат даты: {str(e)}'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Сравнение: делаем ОБА naive
            now_naive = timezone.now().replace(tzinfo=None)
            start_naive = start_time.replace(tzinfo=None) if start_time.tzinfo else start_time
            
            if start_naive < now_naive:
                return Response(
                    {'error': 'Время начала должно быть в будущем'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверка длительности
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
            
            # Получаем место
            slot = ParkingSlot.objects.filter(id=slot_id, is_active=True).first()
            if not slot:
                return Response(
                    {'error': 'Место не найдено'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Проверка доступности (делаем aware для модели)
            start_aware = timezone.make_aware(start_time, dt_timezone.utc)
            end_aware = timezone.make_aware(end_time, dt_timezone.utc)
            
            if not slot.is_available_for_booking(start_aware, end_aware):
                return Response(
                    {'error': 'Место занято'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Лимит 3 брони
            if request.user.is_authenticated:
                if Reservation.objects.filter(user=request.user, status__in=['pending', 'active']).count() >= 3:
                    return Response(
                        {'error': 'Максимум 3 активных бронирования'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            
            
            # Создаём бронирование
            if request.user.is_authenticated and not request.data.get('is_guest', False):
                reservation = Reservation.objects.create(
                    slot=slot,
                    user=request.user,
                    is_guest=False,
                    license_plate=license_plate,
                    start_time=start_aware,
                    end_time=end_aware,
                    status='pending',
                )
            else:
                guest_name = request.data.get('guest_name', '').strip()
                guest_phone = request.data.get('guest_phone', '').strip()
                guest_email = request.data.get('guest_email', '').strip()
                
                if not all([guest_name, guest_phone, guest_email]):
                    return Response(
                        {'error': 'Гость: укажите name, phone, email'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                reservation = Reservation.objects.create(
                    slot=slot,
                    is_guest=True,
                    guest_name=guest_name,
                    guest_phone=guest_phone,
                    guest_email=guest_email,
                    license_plate=license_plate,
                    start_time=start_aware,
                    end_time=end_aware,
                    status='pending',
                    total_price=total_price
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
        """Подтвердить прибытие"""
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
        """Отменить бронирование"""
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
        """Статистика бронирований (для админов)"""
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
    permission_classes = [permissions.AllowAny]
    
    def get_permissions(self):
        if self.action in ['create', 'my_reports']:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated()]
    
    def create(self, request, *args, **kwargs):
        """Создание заявления об угоне"""
        try:
            reservation_id = request.data.get('reservation')
            user_name = request.data.get('user_name', '').strip()
            user_phone = request.data.get('user_phone', '').strip()
            description = request.data.get('description', '').strip()
            
            if not all([user_name, user_phone, description]):
                return Response(
                    {'error': 'Заполните все обязательные поля'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            if len(description) < 10:
                return Response(
                    {'error': 'Описание минимум 10 символов'},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            reservation = None
            if reservation_id:
                reservation = Reservation.objects.filter(id=reservation_id).first()
                if not reservation:
                    return Response(
                        {'error': 'Бронирование не найдено'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
            
            report = TheftReport.objects.create(
                reservation=reservation,
                user_name=user_name,
                user_phone=user_phone,
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
        if request.user.is_authenticated:
            reports = TheftReport.objects.filter(
                Q(reservation__user=request.user) |
                Q(user_phone=request.query_params.get('phone', ''))
            ).select_related('reservation').order_by('-reported_at')
        else:
            phone = request.query_params.get('phone', '')
            if phone:
                reports = TheftReport.objects.filter(user_phone=phone).order_by('-reported_at')
            else:
                reports = TheftReport.objects.none()
        
        serializer = self.get_serializer(reports, many=True)
        return Response(serializer.data)