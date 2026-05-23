from django.urls import path
from . import auth_views

urlpatterns = [
    path('auth/login/', auth_views.login_view, name='login'),
    path('auth/register/', auth_views.register_view, name='register'),
]