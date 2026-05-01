from django.db import models
from django.utils import timezone
from django.contrib.auth import get_user_model
import uuid

User = get_user_model()


class Zone(models.Model):
    """Типы парковочной зоны"""
    ZONE_TYPES = [
        ('entrance', 'у входа'),
        ('far', 'дальние места'),
        ('disabled', 'инвалидные места'),
        ('vip', 'VIP'),
        ('cargo', 'грузовые'),
    ]

    name = models.CharField(max_length=50, unique=True)
    zone_type = models.CharField(max_length=20, choices=ZONE_TYPES, default='entrance')
    description = models.TextField(blank=True)
    capacity = models.IntegerField(default=10)
    priority = models.IntegerField(default=0, help_text='Приоритет для рекомендации.')
    hourly_rate = models.DecimalField(max_digits=10, decimal_places=2, default=100)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_zone_type_display()})"
    
    def get_current_load(self):
        """Показывает текущую загруженность зоны в процентах"""
        if self.capacity == 0:
            return 0.0
        
        active_reservations = Reservation.objects.filter(
            slot__zone=self,
            status='active',
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now()
        ).count()
        
        return (active_reservations / self.capacity) * 100

    class Meta:
        verbose_name = 'Зона'
        verbose_name_plural = 'Зоны'
        ordering = ['priority', 'name']


class ParkingSlot(models.Model):
    """Парковочное место"""
    number = models.CharField(max_length=10)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='slots')

    # Статусы
    is_occupied = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_disabled = models.BooleanField(default=False)

    # Координаты для карты
    position_x = models.IntegerField(null=True, blank=True)
    position_y = models.IntegerField(null=True, blank=True)

    # Камера
    camera_id = models.CharField(max_length=50, blank=True, help_text='ID камеры для данного места')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.zone.name} - Место {self.number}"

    def is_available_for_booking(self, start_time, end_time):
        """Проверка доступности на время"""
        if not self.is_active:
            return False
        overlapping = Reservation.objects.filter(
            slot=self,
            status__in=['active', 'pending'],
            start_time__lte=end_time,
            end_time__gte=start_time
        )
        return not overlapping.exists()

    def get_least_loaded_zone(self):
        """Greedy-algorithm: выбирает наименьшую загруженную зону"""
        zones = Zone.objects.all()
        min_load = 100
        best_zone = None

        for zone in zones:
            load = zone.get_current_load()
            if load < min_load:
                min_load = load
                best_zone = zone
        return best_zone

    class Meta:
        verbose_name = 'Парковочное место'
        verbose_name_plural = 'Парковочные места'
        unique_together = ['zone', 'number']
        ordering = ['zone', 'number']
        indexes = [models.Index(fields=['is_active', 'is_occupied'])]


class Reservation(models.Model):
    """Бронирование парковочного места"""
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
        ('no_show', 'Не явился'),
    ]

    booking_code = models.CharField(max_length=10, unique=True, editable=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='reservations')
    
    # Для гостей
    is_guest = models.BooleanField(default=False)
    guest_name = models.CharField(max_length=100, blank=True)
    guest_email = models.EmailField(blank=True, default='')
    guest_phone = models.CharField(max_length=20, blank=True)
    
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='reservations')
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    
    # Оплата
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    
    # Камера
    camera_recording = models.BooleanField(default=False)
    
    # Временные метки
    confirmed_at = models.DateTimeField(null=True, blank=True)
    cancelled_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Бронь {self.booking_code} - {self.slot}"
    
    def save(self, *args, **kwargs):
        if not self.booking_code:
            self.booking_code = self._generate_booking_code()
        
        if self.slot and self.start_time and self.end_time:
            try:
                duration = (self.end_time - self.start_time).total_seconds() / 3600
                hourly_rate = float(self.slot.zone.hourly_rate) if self.slot.zone.hourly_rate else 100.0
                self.total_price = float(duration) * float(hourly_rate)
            except:
                self.total_price = 0.0
        
        super().save(*args, **kwargs)
    
    def _generate_booking_code(self):
        """Генерация уникального кода бронирования"""
        return f"PRK{uuid.uuid4().hex[:6].upper()}"
    
    def get_user_name(self):
        if self.is_guest:
            return self.guest_name
        return self.user.username if self.user else "Аноним"
    
    def get_user_email(self):
        if self.is_guest:
            return self.guest_email
        return self.user.email if self.user else ""
    
    def get_user_phone(self):
        if self.is_guest:
            return self.guest_phone
        return self.user.phone_number if hasattr(self.user, 'phone_number') else ""

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['status', 'start_time']),
            models.Index(fields=['booking_code']),
        ]


class OccupancyHistory(models.Model):
    """История загруженности для ML прогнозов"""
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='occupancy_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    occupied_count = models.IntegerField(default=0)
    total_capacity = models.IntegerField(default=0)
    occupancy_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    day_of_week = models.IntegerField(help_text='0=Понедельник, 6=Воскресенье')
    hour = models.IntegerField(help_text='0-23')
    is_holiday = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.zone.name} - {self.timestamp} ({self.occupancy_rate}%)"
    
    def save(self, *args, **kwargs):
        if self.total_capacity > 0:
            self.occupancy_rate = (self.occupied_count / self.total_capacity) * 100
        super().save(*args, **kwargs)

    class Meta:
        verbose_name = 'История загруженности'
        verbose_name_plural = 'История загруженности'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['zone', 'timestamp']),
            models.Index(fields=['day_of_week', 'hour']),
        ]


class TheftReport(models.Model):
    """Заявление об угоне/краже"""
    STATUS_CHOICES = [
        ('new', 'Новое'),
        ('in_progress', 'В обработке'),
        ('resolved', 'Решено'),
        ('false_alarm', 'Ложная тревога'),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='theft_reports')
    user_name = models.CharField(max_length=100)
    user_phone = models.CharField(max_length=20)
    user_email = models.EmailField(null=True, blank=True)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True, help_text='Заметки сотрудника')

    def __str__(self):
        return f"Заявление #{self.id} - {self.user_name}"

    class Meta:
        verbose_name = 'Заявление об угоне'
        verbose_name_plural = 'Заявления об угоне'
        ordering = ['-reported_at']


class CameraLog(models.Model):
    """Логи записи с камер"""
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='camera_logs')
    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, null=True, blank=True, related_name='camera_logs')
    recording_started = models.DateTimeField()
    recording_ended = models.DateTimeField(null=True, blank=True)
    video_path = models.CharField(max_length=255, blank=True, help_text='Путь к видеофайлу')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Камера {self.slot.camera_id or self.slot.number} - {self.recording_started}"

    class Meta:
        verbose_name = 'Лог камеры'
        verbose_name_plural = 'Логи камер'
        ordering = ['-created_at']