from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta
from .models import Zone, ParkingSlot, Reservation, TheftReport
from .models import Camera, CameraRecording


class ZoneSerializer(serializers.ModelSerializer):
    """Сериализатор для зон"""
    slots_count = serializers.SerializerMethodField()
    current_load = serializers.SerializerMethodField()
    availability_probability = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        # ✅ Только существующие поля модели + вычисляемые
        fields = [
            'id', 'name', 'zone_type', 'capacity', 
            'priority', 'created_at',
            'slots_count', 'current_load', 'availability_probability'
        ]
        read_only_fields = ['created_at']

    def get_slots_count(self, obj):
        return obj.slots.count()

    def get_current_load(self, obj):
        return obj.get_current_load()

    def get_availability_probability(self, obj):
        load = obj.get_current_load()
        return max(0, 100 - load)


class ParkingSlotSerializer(serializers.ModelSerializer):
    """Сериализатор для парковочных мест"""
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    zone_type = serializers.CharField(source='zone.zone_type', read_only=True)
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = ParkingSlot
        fields = [
            'id', 'number', 'zone', 'zone_name', 'zone_type',
            'is_occupied', 'is_active', 'is_disabled',
            'position_x', 'position_y', 'is_available', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_is_available(self, obj):
        now = timezone.now()
        return obj.is_available_for_booking(now, now + timedelta(hours=2))


class ReservationSerializer(serializers.ModelSerializer):
    """Сериализатор для бронирований"""
    slot_number = serializers.CharField(source='slot.number', read_only=True)
    zone_name = serializers.CharField(source='slot.zone.name', read_only=True)
    user_display_name = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'id', 'booking_code', 'slot', 'slot_number', 'zone_name',
            'user', 'is_guest', 'guest_name', 'guest_email', 'guest_phone',
            'start_time', 'end_time', 'status', 'is_paid',
            'camera_recording', 'confirmed_at', 'cancelled_at',
            'created_at', 'updated_at', 'user_display_name'
        ]
        read_only_fields = ['booking_code', 'created_at', 'updated_at']

    class Meta:
        model = Reservation
        fields = [
            'id', 'booking_code', 'slot', 'slot_number', 'zone_name',
            'user', 'is_guest', 'guest_name', 'guest_email', 'guest_phone',
            'license_plate',  # ← Добавь это поле!
            'start_time', 'end_time', 'status', 'is_paid',
            'camera_recording', 'confirmed_at', 'cancelled_at',
            'created_at', 'updated_at', 'user_display_name'
        ]
        read_only_fields = ['booking_code', 'created_at', 'updated_at']

    def get_user_display_name(self, obj):
        if obj.is_guest:
            return obj.guest_name
        return obj.user.username if obj.user else "Аноним"


class TheftReportSerializer(serializers.ModelSerializer):
    """Сериализатор для заявлений об угоне"""
    class Meta:
        model = TheftReport
        fields = [
            'id', 'reservation', 'user_name', 'user_phone',
            'description', 'status', 'reported_at', 'resolved_at'
        ]
        read_only_fields = ['reported_at', 'resolved_at', 'status']


class CameraSerializer(serializers.ModelSerializer):
    slot_number = serializers.IntegerField(source='slot.number', read_only=True)
    zone_name = serializers.CharField(source='slot.zone.name', read_only=True)

    class Meta:
        model = Camera
        fields = [
            'id', 'name', 'slot', 'slot_number', 'zone_name',
            'rtsp_url', 'is_active', 'is_recording', 'location',
            'created_at', 'updated_at'
        ]
        read_only_fields = ['created_at', 'updated_at']


class CameraRecordingSerializer(serializers.ModelSerializer):
    camera_name = serializers.CharField(source='camera.name', read_only=True)
    reservation_code = serializers.CharField(source='reservation.booking_code', read_only=True)

    class Meta:
        model = CameraRecording
        fields = [
            'id', 'camera', 'camera_name', 'reservation', 'reservation_code',
            'video_path', 'thumbnail_path', 'detected_plate', 'expected_plate',
            'plate_matched', 'confidence_score', 'status', 'duration_seconds',
            'recorded_at', 'processed_at'
        ]
        read_only_fields = ['recorded_at', 'processed_at']


class CameraVerifySerializer(serializers.Serializer):
    """
    Сервер для проверки прибытия через камеру
    """
    reservation_id = serializers.IntegerField(required=True)
    auto_confirm = serializers.BooleanField(default=True, required=False)