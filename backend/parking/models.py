from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta
import secrets

User = get_user_model()

class Zone(models.Model):
    name = models.CharField(max_length=100)
    zone_type = models.CharField(max_length=50, choices=[
        ('entrance', 'У входа'),
        ('far', 'Дальние места'),
        ('disabled', 'Инвалидные места'),
        ('vip', 'VIP'),
        ('cargo', 'Грузовые'),
    ])
    capacity = models.IntegerField(default=10)
    priority = models.IntegerField(default=1)
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def get_current_load(self):
        occupied = ParkingSlot.objects.filter(zone=self, is_occupied=True).count()
        return int((occupied / self.capacity) * 100) if self.capacity > 0 else 0

    def __str__(self):
        return self.name

class ParkingSlot(models.Model):
    number = models.CharField(max_length=10)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='slots')
    is_occupied = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_disabled = models.BooleanField(default=False)
    position_x = models.IntegerField(null=True, blank=True)
    position_y = models.IntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_available_for_booking(self, start_time, end_time):
        if not self.is_active:
            return False
        overlapping = Reservation.objects.filter(
            slot=self,
            status__in=['active', 'pending'],
            start_time__lte=end_time,
            end_time__gte=start_time
        )
        return not overlapping.exists()

    def __str__(self):
        return f"Zone {self.zone.name} - Место {self.number}"

class Reservation(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
        ('no_show', 'Не явился'),
    ]

    booking_code = models.CharField(max_length=20, unique=True, editable=False)
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='reservations')
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='reservations')
    license_plate = models.CharField(max_length=15,blank=True,null=True,verbose_name='Государственный номер')
    is_guest = models.BooleanField(default=False)
    guest_name = models.CharField(max_length=100, null=True, blank=True)
    guest_email = models.CharField(max_length=254, null=True, blank=True)
    guest_phone = models.CharField(max_length=20, null=True, blank=True)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    is_paid = models.BooleanField(default=False)
    camera_recording = models.BooleanField(default=False)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.booking_code:
            self.booking_code = 'PRK' + secrets.token_hex(4).upper()
        super().save(*args, **kwargs)

    def can_cancel(self):
        return self.status == 'pending' and self.start_time > timezone.now()

    def __str__(self):
        return f"{self.booking_code} - {self.slot}"

class TheftReport(models.Model):
    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE)
    user_name = models.CharField(max_length=100)
    user_phone = models.CharField(max_length=20)
    description = models.TextField()
    status = models.CharField(max_length=20, default='pending')
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)

class Camera(models.Model):
    """
    Камера наблюдения для парковочного места
    """
    slot = models.OneToOneField(
        ParkingSlot,
        on_delete=models.CASCADE,
        related_name='camera',
        null=True,
        blank=True,
        verbose_name='Парковочное место'
    )
    name = models.CharField(max_length=100, verbose_name='Название камеры')
    rtsp_url = models.URLField(
        max_length=500,
        blank=True,
        null=True,
        verbose_name='RTSP URL камеры'
    )
    is_active = models.BooleanField(default=True, verbose_name='Активна')
    is_recording = models.BooleanField(default=False, verbose_name='Идёт запись')
    location = models.CharField(
        max_length=200,
        blank=True,
        verbose_name='Расположение'
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Камера'
        verbose_name_plural = 'Камеры'

    def __str__(self):
        return f'{self.name} (Место {self.slot.number if self.slot else "N/A"})'


class CameraRecording(models.Model):
    """
    Запись с камеры (видео + распознанный номер)
    """
    STATUS_CHOICES = [
        ('pending', 'Ожидает обработки'),
        ('processing', 'Обработка'),
        ('completed', 'Завершено'),
        ('failed', 'Ошибка'),
    ]

    camera = models.ForeignKey(
        Camera,
        on_delete=models.CASCADE,
        related_name='recordings',
        verbose_name='Камера'
    )
    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name='camera_recordings',
        null=True,
        blank=True,
        verbose_name='Бронирование'
    )
    video_path = models.CharField(
        max_length=500,
        verbose_name='Путь к видеофайлу'
    )
    thumbnail_path = models.CharField(
        max_length=500,
        blank=True,
        verbose_name='Путь к превью'
    )
    detected_plate = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Распознанный номер'
    )
    expected_plate = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        verbose_name='Ожидаемый номер (из брони)'
    )
    plate_matched = models.BooleanField(
        default=False,
        verbose_name='Номер совпал'
    )
    confidence_score = models.FloatField(
        default=0.0,
        verbose_name='Точность распознавания (%)'
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        verbose_name='Статус'
    )
    duration_seconds = models.IntegerField(
        default=0,
        verbose_name='Длительность (сек)'
    )
    recorded_at = models.DateTimeField(auto_now_add=True, verbose_name='Время записи')
    processed_at = models.DateTimeField(null=True, blank=True, verbose_name='Время обработки')

    class Meta:
        verbose_name = 'Запись с камеры'
        verbose_name_plural = 'Записи с камер'
        ordering = ['-recorded_at']

    def __str__(self):
        return f'{self.camera.name} - {self.recorded_at.strftime("%Y-%m-%d %H:%M")}'

    def auto_confirm_reservation(self):
        """
        Если номер совпал - автоматически подтвердить бронь
        """
        if self.plate_matched and self.reservation and self.reservation.status == 'pending':
            self.reservation.status = 'active'
            self.reservation.confirmed_at = timezone.now()
            self.reservation.save()
            return True
        return False