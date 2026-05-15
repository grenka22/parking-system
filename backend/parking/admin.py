from django.contrib import admin
from .models import Zone, ParkingSlot, Reservation, TheftReport
from django.contrib import admin
from .models import Camera, CameraRecording

@admin.register(Zone)
class ZoneAdmin(admin.ModelAdmin):
    list_display = ['name', 'zone_type', 'capacity', 'priority', 'hourly_rate', 'created_at']
    list_filter = ['zone_type', 'priority']
    search_fields = ['name']

@admin.register(ParkingSlot)
class ParkingSlotAdmin(admin.ModelAdmin):
    list_display = ['number', 'zone', 'is_active', 'is_occupied', 'is_disabled', 'created_at']
    list_filter = ['zone', 'is_active', 'is_occupied', 'is_disabled']
    search_fields = ['number']

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ['booking_code', 'slot', 'start_time', 'end_time', 'status', 'is_guest', 'created_at']
    list_filter = ['status', 'is_guest', 'created_at']
    search_fields = ['booking_code', 'guest_name', 'guest_email', 'user__username']
    
    actions = ['confirm_reservations', 'cancel_reservations', 'mark_as_completed']
    
    def confirm_reservations(self, request, queryset):
        updated = queryset.update(status='active')
        self.message_user(request, f'{updated} бронирований подтверждено')
    confirm_reservations.short_description = "Подтвердить выбранные"
    
    def cancel_reservations(self, request, queryset):
        updated = queryset.update(status='cancelled')
        self.message_user(request, f'{updated} бронирований отменено')
    cancel_reservations.short_description = "Отменить выбранные"
    
    def mark_as_completed(self, request, queryset):
        updated = queryset.update(status='completed')
        self.message_user(request, f'{updated} бронирований завершено')
    mark_as_completed.short_description = "Пометить как завершенные"

@admin.register(TheftReport)
class TheftReportAdmin(admin.ModelAdmin):
    list_display = ['id', 'reservation', 'user_name', 'status', 'reported_at', 'resolved_at']
    list_filter = ['status', 'reported_at']
    search_fields = ['user_name', 'user_phone', 'description']

from .models import Camera, CameraRecording
from django.contrib import admin

@admin.register(Camera)
class CameraAdmin(admin.ModelAdmin):
    list_display = ['name', 'slot', 'is_active', 'is_recording', 'location', 'created_at']
    list_filter = ['is_active', 'is_recording', 'slot__zone']
    search_fields = ['name', 'location', 'slot__number']
    readonly_fields = ['created_at', 'updated_at']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slot', 'location')
        }),
        ('Настройки', {
            'fields': ('rtsp_url', 'is_active', 'is_recording')
        }),
        ('Системная информация', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )


@admin.register(CameraRecording)
class CameraRecordingAdmin(admin.ModelAdmin):
    list_display = ['camera', 'reservation', 'detected_plate', 'expected_plate', 
                    'plate_matched', 'confidence_score', 'status', 'recorded_at']
    list_filter = ['status', 'plate_matched', 'camera', 'recorded_at']
    search_fields = ['detected_plate', 'expected_plate', 'reservation__booking_code']
    readonly_fields = ['recorded_at', 'processed_at', 'video_path', 'thumbnail_path']
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('camera', 'reservation', 'status')
        }),
        ('Распознавание номера', {
            'fields': ('detected_plate', 'expected_plate', 'plate_matched', 'confidence_score')
        }),
        ('Файлы', {
            'fields': ('video_path', 'thumbnail_path', 'duration_seconds')
        }),
        ('Временные метки', {
            'fields': ('recorded_at', 'processed_at'),
            'classes': ('collapse',)
        }),
    )