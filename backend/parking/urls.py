# backend/parking/urls.py
from django.urls import path

# Если роутер уже подключён в config/urls.py — этот файл может быть пустым
# или содержать только специфичные эндпоинты

urlpatterns = [
    # Пример дополнительного эндпоинта (если нужен):
    # path('slots/<int:pk>/check/', SlotCheckView.as_view(), name='slot-check'),
]