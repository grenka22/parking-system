from django.contrib import admin
from django.utils.html import format_html
from .models import Zone, ParkingSlot, Reservation, OccupancyHistory, TheftReport, CameraLog

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'zone_type', 'capacity', 'get_current_load_display', 'priority', 'created_at']
    list_filter = ['zone_type', 'priority']
    search_fields = ['name', 'description']
    ordering = ['priority', 'name']

    def get_current_load_display(self, obj):
        """Отображение загруженности зоны"""
        try:
            # Получаем загруженность
            load = obj.get_current_load()
            
            # Гарантируем что это число
            if isinstance(load, str):
                # Если строка - пытаемся конвертировать
                load = float(load.replace('%', '').strip())
            else:
                load = float(load) if load is not None else 0.0
            
            # Определяем цвет
            if load < 50:
                color = 'green'
            elif load < 80:
                color = 'orange'
            else:
                color = 'red'
            
            # Возвращаем HTML
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color, load
            )
        except (ValueError, TypeError, AttributeError) as e:
            # Если ошибка - показываем "N/A"
            return format_html('<span style="color: gray;">N/A</span>')
    
    get_current_load_display.short_description = 'Загруженность'


@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ['number', 'zone', 'is_occupied', 'is_active', 'is_disabled', 'created_at' ]
    list_filter = ['zone', 'is_occupied', 'is_active', 'is_disabled']
    search_fields = ['number', 'zone__name']
    ordering = ['zone', 'number']
    actions = ['make_occupied', 'make_free', 'deactivate_slots']

    
    def make_occupied(self, request, queryset):
        queryset.update(is_occupied=True)
        self.message_user(request, f'{queryset.count()} мест занято')
    make_occupied.short_description = 'Пометить как занятые'

    def make_free(self, request, queryset):
        queryset.update(is_occupied=False)
        self.message_user(request, f'{queryset.count()} мест помечено как свободные')
    make_free.short_description = 'Пометить как свободные'


    def deactivate_slots(self, request, queryset):
        queryset.update(is_active=False)
        self.message_user(request, f'{queryset.count()} мест деактивированы')
    deactivate_slots.short_description = 'Деактивировать места'


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['booking_code', 'get_user_name', 'slot', 'zone_display','start_time', 'end_time', 'status', 'is_guest','camera_recording', 'created_at']
    list_filter = ['status', 'is_guest', 'camera_recording', 'slot__zone']
    search_fields = ['user_name', 'user_phone', 'user_email', 'booking_code', 'slot__number']
    ordering = ['-created_at']
    date_hierarchy = 'start_time'
    actions = ['confirm_reservations', 'cancel_reservations', 'mark_completed']
    readonly_fields = ['booking_code', 'created_at', 'updated_at']

    def zone_display(self, obj):
        return obj.slot.zone.name
    zone_display.short_description = 'Зона'

    def confirm_reservations(self, request, queryset):
        from django.utils import timezone
        queryset.filter(start_time__gte=timezone.now()).update(
            status='active',
            confirmed_at=timezone.now()
        )
        self.message_user(request, f'{queryset.count()} бронирований подтверждено')
    confirm_reservations.short_description = 'Подтвердить выбранные'

    def cancel_reservations(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='cancelled',cancelled_at=timezone.now())
        self.message_user(request, f'{queryset.count()} бронирований отменено')
    cancel_reservations.short_description = 'Отменить выбранные'

    def mark_completed(self, request, queryset):
        queryset.update(status = 'completed')
        self.message_user(request, f'{queryset.count()} бронирований завершено')
    mark_completed.short_description = 'Пометить как завершенные'

@admin.register(OccupancyHistory)
class OccupancyHistoryAdmin(admin.ModelAdmin):
    list_display = ['zone', 'timestamp', 'occupied_count', 'total_capacity', 'occupancy_rate', 'day_of_week', 'hour', 'is_holiday']
    list_filter = ['zone', 'day_of_week', 'hour', 'is_holiday']
    search_fields = ['zone__name']
    ordering = ['-timestamp']
    readonly_fields = ['timestamp', 'day_of_week', 'hour', 'occupancy_rate']


@admin.register(TheftReport)
class TheftReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reservation', 'user_name', 'status', 'reported_at', 'resolved_at']
    list_filter = ['status']
    search_fields = ['user_name', 'user_phone', 'reservation__booking_code']
    ordering = ['-reported_at']
    readonly_fields = ['reported_at', 'resolved_at']
    actions = ['mark_in_progress', 'mark_resolved', 'mark_false_alarm']

    def mark_in_progress(self, request, queryset):
        queryset.update(status = 'in_progress')
        self.message_user(request, f'{queryset.count()} заявлений в обработке')
    mark_in_progress.short_description = 'Взять в работу'

    def mark_resolved(self, request, queryset):
        from django.utils import timezone
        queryset.update(status = 'resolved', resolved_at = timezone.now())
        self.message_user(request, f'{queryset.count()} заявлений решено')

    def mark_false_alarm(self, request, queryset):
        from django.utils import timezone
        queryset.update(status='false_alarm', resolved_at=timezone.now())
        self.message_user(request, f'{queryset.count()} заявлений - ложная тревога')

    mark_false_alarm.short_description = 'Ложная тревога'

@admin.register(CameraLog)
class CameraLogAdmin(admin.ModelAdmin):
    list_display = ['slot', 'reservation', 'recording_started', 'recording_ended', 'created_at']
    list_filter = ['slot__zone']
    search_fields = ['slot__number', 'reservation__booking_code']
    ordering = ['-created_at']
    readonly_fields = ['created_at']
