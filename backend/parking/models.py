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
    total_price = models.DecimalField(max_digits=10, decimal_places=2, default=0)
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