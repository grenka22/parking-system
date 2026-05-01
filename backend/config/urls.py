from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter

# Импортируем ViewSets из parking
from parking.views import ZoneViewSet, ParkingSlotViewSet, ReservationViewSet

# Импортируем auth views
from parking.auth_views import RegisterView, LoginView, LogoutView, RefreshTokenView, ProfileView

# Импортируем JWT views из simplejwt
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)

# Роутер для основных API
router = DefaultRouter()
router.register(r'zones', ZoneViewSet)
router.register(r'slots', ParkingSlotViewSet)
router.register(r'reservations', ReservationViewSet)
#router.register(r'theft-reports', TheftReportViewSet)

# URL паттерны
urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include(router.urls)),
    
    # Аутентификация (наши кастомные)
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/auth/logout/', LogoutView.as_view(), name='logout'),
    path('api/auth/refresh/', RefreshTokenView.as_view(), name='auth_refresh'),
    path('api/auth/profile/', ProfileView.as_view(), name='profile'),
    
    # JWT токены (встроенные из simplejwt)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
]