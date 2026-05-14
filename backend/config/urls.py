from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# ✅ Импорты из parking.views (ТВОИ ViewSet'ы)
from parking.views import (
    ZoneViewSet,
    ParkingSlotViewSet,
    ReservationViewSet,
    TheftReportViewSet,
)

# ✅ Импорты кастомных auth views
from parking.auth_views import RegisterView, ProfileView

# ✅ Импорты JWT views из simplejwt (ТОЛЬКО JWT!)
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
    TokenVerifyView,
)

# Роутер для основных API
router = DefaultRouter()
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'slots', ParkingSlotViewSet, basename='slot')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'theft-reports', TheftReportViewSet, basename='theft-report')

urlpatterns = [
    # Админка Django
    path('admin/', admin.site.urls),
    
    # 🔐 Аутентификация
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/profile/', ProfileView.as_view(), name='profile'),
    
    # 🔌 Основные API через router
    path('api/', include(router.urls)),
]