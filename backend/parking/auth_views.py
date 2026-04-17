from rest_framework import status, generics
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import re

User = get_user_model()


class RegisterView(generics.CreateAPIView):
 
    queryset = User.objects.all()
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        email = request.data.get('email')
        password = request.data.get('password')
        password_confirm = request.data.get('password_confirm')
        phone = request.data.get('phone', '')


        if not all([username, email, password]):
            return Response(
                {'error': 'Укажите username, email и password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            validate_email(email)
        except ValidationError:
            return Response(
                {'error': 'Некорректный email'},
                status=status.HTTP_400_BAD_REQUEST
            )


        if len(password) < 8:
            return Response(
                {'error': 'Пароль должен содержать минимум 8 символов'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if password != password_confirm:
            return Response(
                {'error': 'Пароли не совпадают'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username=username).exists():
            return Response(
                {'error': 'Пользователь с таким именем уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {'error': 'Пользователь с таким email уже существует'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=username.split()[0] if username else '',
            last_name=username.split()[1] if len(username.split()) > 1 else ''
        )

        refresh = RefreshToken.for_user(user)

        return Response({
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'message': 'Пользователь успешно зарегистрирован'
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):

    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get('username')
        password = request.data.get('password')

        if not all([username, password]):
            return Response(
                {'error': 'Укажите username и password'},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user:
            return Response(
                {'error': 'Неверный username или пароль'},
                status=status.HTTP_401_UNAUTHORIZED
            )

        refresh = RefreshToken.for_user(user)

        return Response({
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'access_token': str(refresh.access_token),
            'refresh_token': str(refresh),
            'message': 'Вход выполнен успешно'
        })


class LogoutView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, *args, **kwargs):
        try:
            refresh_token = request.data.get('refresh_token')
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({
                'success': True,
                'message': 'Выход выполнен успешно'
            })
        except Exception as e:
            return Response({
                'error': 'Неверный токен',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class RefreshTokenView(APIView):
    
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh_token')

        if not refresh_token:
            return Response(
                {'error': 'Укажите refresh_token'},
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            token = RefreshToken(refresh_token)
            access_token = str(token.access_token)

            return Response({
                'success': True,
                'access_token': access_token,
                'message': 'Токен обновлён'
            })
        except Exception as e:
            return Response({
                'error': 'Неверный refresh_token',
                'detail': str(e)
            }, status=status.HTTP_400_BAD_REQUEST)


class ProfileView(APIView):
    
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        
        return Response({
            'user_id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'date_joined': user.date_joined,
            'last_login': user.last_login
        })