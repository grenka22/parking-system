from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView, TokenVerifyView

from parking.views import (
    ZoneViewSet, ParkingSlotViewSet, ReservationViewSet,
    TheftReportViewSet, CameraViewSet, CameraRecordingViewSet
)
from parking.auth_views import RegisterView, ProfileView

router = DefaultRouter()
router.register(r'zones', ZoneViewSet, basename='zone')
router.register(r'slots', ParkingSlotViewSet, basename='slot')
router.register(r'reservations', ReservationViewSet, basename='reservation')
router.register(r'theft-reports', TheftReportViewSet, basename='theft-report')
router.register(r'cameras', CameraViewSet, basename='camera')
router.register(r'camera-recordings', CameraRecordingViewSet, basename='camera-recording')

urlpatterns = [
    path('admin/', admin.site.urls),
    
    # Аутентификация (совпадает с ожиданиями фронтенда)
    path('api/auth/register/', RegisterView.as_view(), name='register'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/auth/verify/', TokenVerifyView.as_view(), name='token_verify'),
    path('api/auth/profile/', ProfileView.as_view(), name='profile'),
    
    # Остальные API
    path('api/', include(router.urls)),
]