"""Конфигурация приложения parking для Django.

Регистрирует приложение в проекте и задаёт тип автоматического поля по умолчанию.
"""

from django.apps import AppConfig


class ParkingConfig(AppConfig):
    """Конфигурация приложения parking."""
    
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'parking'