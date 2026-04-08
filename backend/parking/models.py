from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import random
import string

class Zone(models.Model):
    "типы парковочной зоны"
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
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.get_zone_type_display()})"

    def get_current_load(self):
        "показывает текущую загруженность зоны"
        active_reservations = Reservation.objects.filter(
            slot__zone=self,
            status='active',
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now()).count()
        return active_reservations / self.capacity * 100

    class Meta:
        verbose_name = 'Зона'
        verbose_name_plural = 'Зоны'
        ordering = ['priority' , 'name']

class ParkingSlot(models.Model):
    'парковочное место'
    number = models.CharField(max_length = 10)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='slots')

    #статусы
    is_occupied = models.BooleanField(default=False) #камеры
    is_active = models.BooleanField(default=True) #доступно для бронирования
    is_disabled = models.BooleanField(default=False)  #для инвалидов

    #координаты для карты
    position_x = models.IntegerField(null = True, blank = True)
    position_y = models.IntegerField(null = True, blank = True)

    #камера

    camera_id = models.CharField(max_length = 50,  blank = True, help_text='ID камеры для данного места')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.zone.name} - Место {self.number}"

    def is_available_for_booking(self, start_time, end_time):
        #проверка доступа на время
        if not self.is_active:
            return False
        overlapping = Reservation.objects.filter(
            slot = self,
            status='active',
            start_time__lte=end_time,
            end_time__gte=start_time
        )
        return not overlapping.exists()

    def get_least_loaded_zone(self):
        'greedy-algorithm выбирает наименьшую загруженную зону'
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
        indexes= [ models.Index(fields=['is_active', 'is_occupied']),]

class Reservation(models.Model):
    'бронирование места'
    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('cancelled' , 'Отменено'),
        ('no_show' , 'Не явился')
    ]

    #связи
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='reservations')
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, null = True , blank = True, related_name='reservations' , help_text = 'Пользователь (null для гостей)')

    #данные клиента
    user_name = models.CharField(max_length = 100)
    user_phone = models.CharField(max_length = 20)
    user_email = models.EmailField(blank=True)
    is_guest = models.BooleanField(default=False, help_text = 'Гостевое бронирование')

    #время
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    #статусы
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    #код бронирования
    booking_code = models.CharField(max_length = 10, unique = True, editable = False)

    #камеры
    camera_recording = models.BooleanField(default=False, help_text = 'Идет запись с какмер')
    camera_recording_started = models.DateTimeField(null=True, blank=True)

    #временные метки
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_name} - {self.slot} ({self.start_time})"

    def save(self, *args, **kwargs):
        'генерация кода'
        if not self.booking_code:
            self.booking_code = self._generate_booking_code()
        super().save(*args, **kwargs)

    def _generate_booking_code(self):
        'генерация уникального кода'
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k = 6))
            if not Reservation.objects.filter(booking_code=code).exists():
                return code

    def clean(self):
        'проверка что end>start'
        if self.end_time <= self.start_time:
            raise ValidationError('Время окончания должно быть позже начала.')

        #проверка на пресечение с другой бронью
        if self.pk:
            overlapping = Reservation.objects.filter(
                slot = self.slot,
                status__in=['active', 'pending'],
                start_time__lt = self.end_time,
                end_time__gt = self.start_time

            ).exclude(pk=self.pk)

        else:
            overlapping = Reservation.objects.filter(
                slot = self.slot,
                status__in = ['active', 'pending'],
                start_time__lt = self.end_time,
                end_time__gt = self.start_time
            )
        if overlapping.exists():
            raise ValidationError('Это место уже забронировано на выбранное время')

    def can_cancel(self):
        'можно ли отменить бронирование (>30 мин до начала)'
        if self.status != 'active':
            return False
        return timezone.now() < self.start_time - timedelta(minutes=30)

    def is_available(self):
        'проверить доступно ли место на время бронирования'
        return not Reservation.objects.filter(
            slot=self.slot,
            status__in=['active', 'pending'],
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        ).exists()

    class Meta:
        verbose_name = 'Бронирование'
        verbose_name_plural = 'Бронирования'
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['slot', 'status']),
            models.Index(fields=['start_time', 'end_time']),
            models.Index(fields=['user', 'status']),
            models.Index(fields=['booking_code']),
        ]

class OccupancyHistory(models.Model):
    'история загруженности для ML'
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='occupancy_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    occupied_count = models.IntegerField()
    total_capacity = models.IntegerField()
    occupancy_rate = models.FloatField()  # Процент загруженности
    day_of_week = models.IntegerField()  # 0-6
    hour = models.IntegerField()  # 0-23
    is_holiday = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.timestamp:
            self.day_of_week = self.timestamp.weekday()
            self.hour = self.timestamp.hour
        if self.total_capacity > 0:
            self.occupancy_rate = self.occupied_count / self.total_capacity * 100
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
    'угон'
    STATUS_CHOICES = [
        ('new', 'Новая'),
        ('in_progress', 'В обработке'),
        ('resolved', 'Решено'),
        ('false_alarm', 'Ложная тревога'),
    ]

    reservation = models.ForeignKey(Reservation, on_delete=models.CASCADE, related_name='theft_reports')
    user_name = models.CharField(max_length=100)
    user_phone = models.CharField(max_length=20)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='new')
    reported_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    police_report_number = models.CharField(max_length=50, blank=True)

    def __str__(self):
        return f"Угон: {self.reservation.slot} - {self.user_name}"

    class Meta:
        verbose_name = 'Заявление об угоне'
        verbose_name_plural = 'Заявления об угоне'
        ordering = ['-reported_at']

class CameraLog(models.Model):
    'Логи записей с камер'
    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='camera_logs')
    reservation = models.ForeignKey(Reservation, on_delete=models.SET_NULL, null=True, blank=True)
    recording_started = models.DateTimeField()
    recording_ended = models.DateTimeField(null=True, blank=True)
    video_path = models.CharField(max_length=500, blank=True, help_text='Путь к файлу записи')
    snapshot_path = models.CharField(max_length=500, blank=True, help_text='Путь к скриншоту')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Камера {self.slot} - {self.recording_started}"

    class Meta:
        verbose_name = 'Лог камеры'
        verbose_name_plural = 'Логи камер'
        ordering = ['-created_at']