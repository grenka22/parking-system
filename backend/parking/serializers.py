from rest_framework import serializers
from django.utils import timezone
from datetime import timedelta



from .models import Zone, ParkingSlot, Reservation, TheftReport

class ZoneSerializer(serializers.ModelSerializer):
    slots_count = serializers.SerializerMethodField()
    current_load = serializers.SerializerMethodField()
    availability_probability = serializers.SerializerMethodField()

    class Meta:
        model = Zone
        fields = [
            'id', 'name', 'zone_type', 'description', 'capacity', 'priority', 'slots_count', 'current_load', 'availability_probability', 'created_at'
        ]
        read_only_fields = ['created_at']

    def get_slots_count(self, obj):
        return obj.slots.count()

    def get_current_load(self, obj):
        return obj.get_current_load()

    def get_availability_probability(self, obj):
        load = obj.get_current_load()
        return max(0,100 - load )


class ParkingSlotSerializer(serializers.ModelSerializer):
    zone_name = serializers.CharField(source='zone.name', read_only=True)
    zone_type = serializers.CharField(source='zone.zone_type' , read_only=True)
    is_available = serializers.SerializerMethodField()

    class Meta:
        model = ParkingSlot
        fields = ['id', 'number', 'zone' , 'zone_name', 'zone_type', 'is_occupied', 'is_active', 'is_disabled', 'position_x', 'position_y', 'is_available', 'created_at']
        read_only_fields = ['created_at']

    def get_is_available (self, obj):
        now = timezone.now()
        return obj.is_available_for_booking(now, now + timedelta(hours=2))

class ReservationSerializer(serializers.ModelSerializer):
    slot_number = serializers.CharField(source='slot.number', read_only=True)
    zone_name = serializers.CharField(source='slot.zone_name', read_only=True)
    zone_type = serializers.CharField(source='slot.zone_type', read_only=True)
    can_cancel = serializers.SerializerMethodField()

    class Meta:
        model = Reservation
        fields = [
            'id', 'booking_code', 'slot', 'slot_number', 'zone_name', 'zone_type', 'user_name' , 'user_phone', 'user_email', 'is_guest', 'start_time', 'end_time', 'status', 'can_cancel', 'camera_recording', 'confirmed_at', 'canceled_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [ 'booking_code'  ,'created_at', 'updated_at']

    def get_can_cancel(self, obj):
        return obj.can_cancel()

    def get_time_until_start(self, obj):
        delta = obj.start_time - timezone.now()
        return int(delta.total_seconds() / 60)

class ReservationCreateSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reservation
        fields = ['slot', 'user_name', 'user_phone', 'user_email', 'start_time', 'end_time', 'is_guest']

    def validate_user_phone(self, value):
        if not value:
            raise serializers.ValidationError("Номер телефона обязателен")
        clean_phone = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        if not clean_phone.starstwith('+'):
            raise serializers.ValidationError("Номер телефона должен начинаться с +")
        digits = ''.join(filter(str.isdigit, clean_phone))

        if len(digits) < 11:
            raise serializers.ValidationError("Некорректный ввод")

        if len(digits) > 11:
            raise serializers.ValidationError("Некорректный ввод")

        return clean_phone

    def validate_user_email(self,value):
        if  value:
            from django.core.validators import validate_email
            from django.core.exceptions import ValidationError

            try:
                validate_email(value)
            except ValidationError:
                raise serializers.ValidationError("Некорректный ввод")

            if len(value) > 254:
                raise serializers.ValidationError("Некорректный ввод")

        return value.lower().strip()

    def validate_start_time(self, value):
        if value < timezone.now():
            raise serializers.ValidationError("Ошибка")

        if value > timezone.now() + timedelta(days = 7):
            raise serializers.ValidationError("Можно бронировать не более чем на 7 дней вперед")

        return value

    def validate(self,data):
        start_time = data.get('start_time')
        end_time = data.get('end_time')

        if start_time and end_time:
            if end_time <= start_time:
                raise serializers.ValidationError({'end time' : 'Время окончания должно быть позже времени начала'
                })

            duration = end_time - start_time
            if duration > timedelta(hours=3):
                raise serializers.ValidationError({
                    'end_time': 'Максимальное время бронирования 3 часа'
                })

            if duration < timedelta(minutes=30):
                raise serializers.ValidationError({
                    'start_time': 'Минимальное время бронирования - 30 минут'
                })

        slot = data.get('slot')
        if slot and not slot.is_active:
            raise serializers.ValidationError({
                'slot': 'Это место временно недоступно для бронирования'
            })
        return data

    def create(self, validated_data):
        slot = validated_data.get('slot')
        start_time = validated_data.get('start_time')
        end_time = validated_data.get('end_time')

        if not slot.is_available_for_booking(start_time, end_time):
            raise serializers.ValidationError({'slot' : 'Данное место забронировано на выбранное время'})
        return super().create(validated_data)


class TheftReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = TheftReport
        fields = ['id', 'reservation', 'user_name', 'user_phone', 'description', 'status', 'reported_at', 'resolved_at']
        read_only_fields = ['reported_at', 'resolved_at', 'status']

    def validate_description(self, value):
        if not value or len(value.strip()) < 10:
            raise serializers.ValidationError("Опишите ситуацию подробнее (минимум 10 символов)")

        return value.strip()

    def validate_user_phone(self, value):

        if not value:
            raise serializers.ValidationError("Телефон обязателен")

        clean_phone = value.replace(' ', '').replace('-', '').replace('(', '').replace(')', '')

        if not clean_phone.startswith('+'):
            raise serializers.ValidationError("Телефон должен начинаться с +")

        digits = ''.join(filter(str.isdigit, clean_phone))
        if len(digits) < 10:
            raise serializers.ValidationError("Телефон должен содержать минимум 10 цифр")

        return clean_phone