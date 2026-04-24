"""Модели данных приложения parking.

Содержит модели:
- Zone — зоны парковки
- ParkingSlot — парковочные места
- Reservation — бронирования
- OccupancyHistory — история загруженности для ML
- TheftReport — заявления об угоне
- CameraLog — логи камер видеонаблюдения
"""

from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone
from datetime import timedelta
import random
import string


class Zone(models.Model):
    """Модель зоны парковки.

    Attributes:
        name (str): Название зоны (уникальное)
        zone_type (str): Тип зоны (у входа, дальние, инвалидные, VIP, грузовые)
        description (str): Описание зоны
        capacity (int): Вместимость зоны
        priority (int): Приоритет для рекомендации мест
        created_at (datetime): Дата создания
    """

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
        """Возвращает текущую загруженность зоны в процентах.

        Returns:
            float: Процент занятых мест в зоне (0-100)
        """
        active_reservations = Reservation.objects.filter(
            slot__zone=self,
            status='active',
            start_time__lte=timezone.now(),
            end_time__gte=timezone.now()
        ).count()
        return active_reservations / self.capacity * 100 if self.capacity > 0 else 0

    class Meta:
        verbose_name = 'Зона'
        verbose_name_plural = 'Зоны'
        ordering = ['priority', 'name']


class ParkingSlot(models.Model):
    """Модель парковочного места.

    Attributes:
        number (str): Номер места
        zone (Zone): Зона, к которой относится место
        is_occupied (bool): Занято ли место (по камерам)
        is_active (bool): Доступно ли место для бронирования
        is_disabled (bool): Место для инвалидов
        position_x (int): Координата X для карты
        position_y (int): Координата Y для карты
        camera_id (str): ID камеры для данного места
        created_at (datetime): Дата создания
    """

    number = models.CharField(max_length=10)
    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='slots')

    is_occupied = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_disabled = models.BooleanField(default=False)

    position_x = models.IntegerField(null=True, blank=True)
    position_y = models.IntegerField(null=True, blank=True)

    camera_id = models.CharField(max_length=50, blank=True, help_text='ID камеры для данного места')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.zone.name} - Место {self.number}"

    def is_available_for_booking(self, start_time, end_time):
        """Проверяет, доступно ли место для бронирования на указанный интервал.

        Args:
            start_time (datetime): Начало интервала
            end_time (datetime): Конец интервала

        Returns:
            bool: True, если место доступно, иначе False
        """
        if not self.is_active:
            return False
        overlapping = Reservation.objects.filter(
            slot=self,
            status='active',
            start_time__lte=end_time,
            end_time__gte=start_time
        )
        return not overlapping.exists()

    def get_least_loaded_zone(self):
        """Greedy-algorithm — выбирает наименее загруженную зону.

        Returns:
            Zone: Зона с минимальной загруженностью
        """
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
        indexes = [
            models.Index(fields=['is_active', 'is_occupied']),
        ]


class Reservation(models.Model):
    """Модель бронирования парковочного места.

    Attributes:
        slot (ParkingSlot): Забронированное место
        user (User): Пользователь (null для гостей)
        user_name (str): Имя пользователя
        user_phone (str): Телефон пользователя
        user_email (str): Email пользователя
        is_guest (bool): Гостевое бронирование
        start_time (datetime): Начало бронирования
        end_time (datetime): Конец бронирования
        status (str): Статус бронирования
        booking_code (str): Уникальный 6-символьный код
        camera_recording (bool): Идёт ли запись с камер
        camera_recording_started (datetime): Время начала записи
        created_at (datetime): Дата создания
        updated_at (datetime): Дата обновления
        confirmed_at (datetime): Дата подтверждения
        canceled_at (datetime): Дата отмены
    """

    STATUS_CHOICES = [
        ('pending', 'Ожидает подтверждения'),
        ('active', 'Активно'),
        ('completed', 'Завершено'),
        ('cancelled', 'Отменено'),
        ('no_show', 'Не явился'),
    ]

    slot = models.ForeignKey(ParkingSlot, on_delete=models.CASCADE, related_name='reservations')
    user = models.ForeignKey(
        'auth.User', on_delete=models.CASCADE, null=True, blank=True,
        related_name='reservations', help_text='Пользователь (null для гостей)'
    )

    user_name = models.CharField(max_length=100)
    user_phone = models.CharField(max_length=20)
    user_email = models.EmailField(blank=True)
    is_guest = models.BooleanField(default=False, help_text='Гостевое бронирование')

    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    booking_code = models.CharField(max_length=10, unique=True, editable=False)

    camera_recording = models.BooleanField(default=False, help_text='Идет запись с камер')
    camera_recording_started = models.DateTimeField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    canceled_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user_name} - {self.slot} ({self.start_time})"

    def save(self, *args, **kwargs):
        """Генерирует уникальный код бронирования перед сохранением."""
        if not self.booking_code:
            self.booking_code = self._generate_booking_code()
        super().save(*args, **kwargs)

    def _generate_booking_code(self):
        """Генерирует уникальный 6-символьный код бронирования.

        Returns:
            str: Уникальный код (буквы A-Z и цифры 0-9)
        """
        while True:
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))
            if not Reservation.objects.filter(booking_code=code).exists():
                return code

    def clean(self):
        """Валидация бронирования: проверка времени и отсутствия пересечений."""
        if self.end_time <= self.start_time:
            raise ValidationError('Время окончания должно быть позже начала.')

        overlapping = Reservation.objects.filter(
            slot=self.slot,
            status__in=['active', 'pending'],
            start_time__lt=self.end_time,
            end_time__gt=self.start_time
        )
        if self.pk:
            overlapping = overlapping.exclude(pk=self.pk)

        if overlapping.exists():
            raise ValidationError('Это место уже забронировано на выбранное время')

    def can_cancel(self):
        """Проверяет, можно ли отменить бронирование (не менее чем за 30 минут до начала).

        Returns:
            bool: True, если отмена возможна, иначе False
        """
        if self.status != 'active':
            return False
        return timezone.now() < self.start_time - timedelta(minutes=30)

    def is_available(self):
        """Проверяет, доступно ли место на время бронирования.

        Returns:
            bool: True, если место свободно, иначе False
        """
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
    """Модель истории загруженности для ML-прогнозирования.

    Attributes:
        zone (Zone): Зона парковки
        timestamp (datetime): Время записи
        occupied_count (int): Количество занятых мест
        total_capacity (int): Общая вместимость зоны
        occupancy_rate (float): Процент загруженности
        day_of_week (int): День недели (0-6)
        hour (int): Час (0-23)
        is_holiday (bool): Праздничный ли день
    """

    zone = models.ForeignKey(Zone, on_delete=models.CASCADE, related_name='occupancy_history')
    timestamp = models.DateTimeField(auto_now_add=True)
    occupied_count = models.IntegerField()
    total_capacity = models.IntegerField()
    occupancy_rate = models.FloatField()
    day_of_week = models.IntegerField()
    hour = models.IntegerField()
    is_holiday = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        """Вычисляет день недели, час и процент загруженности перед сохранением."""
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
    """Модель заявления об угоне.

    Attributes:
        reservation (Reservation): Связанное бронирование
        user_name (str): Имя заявителя
        user_phone (str): Телефон заявителя
        description (str): Описание инцидента
        status (str): Статус обработки
        reported_at (datetime): Дата заявления
        resolved_at (datetime): Дата разрешения
        police_report_number (str): Номер заявления в полиции
    """

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
    """Модель логов записей с камер видеонаблюдения.

    Attributes:
        slot (ParkingSlot): Парковочное место
        reservation (Reservation): Связанное бронирование
        recording_started (datetime): Время начала записи
        recording_ended (datetime): Время окончания записи
        video_path (str): Путь к файлу записи
        snapshot_path (str): Путь к скриншоту
        created_at (datetime): Дата создания записи
    """

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