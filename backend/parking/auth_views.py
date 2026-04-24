"""Вьюхи для аутентификации пользователей.

Содержит:
- RegisterView — регистрация нового пользователя
- LoginView — вход и получение JWT-токенов
- LogoutView — выход (blacklist refresh-токена)
- RefreshTokenView — обновление access-токена
- ProfileView — получение профиля текущего пользователя
"""

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
    """Регистрация нового пользователя.

    Ожидает JSON с полями:
        - username (str): Имя пользователя
        - email (str): Email
        - password (str): Пароль (минимум 8 символов)
        - password_confirm (str): Подтверждение пароля
        - phone (str, опционально): Номер телефона

    Returns:
        201 Created: Пользователь создан, возвращает access_token и refresh_token
        400 Bad Request: Ошибки валидации (не все поля, пароль короткий, email некорректный,
                         пароли не совпадают, пользователь уже существует)
    """

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
    """Аутентификация пользователя и выдача JWT-токенов.

    Ожидает JSON с полями:
        - username (str): Имя пользователя
        - password (str): Пароль

    Returns:
        200 OK: Возвращает access_token и refresh_token
        400 Bad Request: Отсутствуют username или password
        401 Unauthorized: Неверные учётные данные
    """

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
    """Выход пользователя (blacklist refresh-токена).

    Ожидает JSON с полем:
        - refresh_token (str): Refresh-токен для инвалидации

    Returns:
        200 OK: Токен добавлен в blacklist
        400 Bad Request: Неверный или отсутствующий токен
    """

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
    """Обновление access-токена по refresh-токену.

    Ожидает JSON с полем:
        - refresh_token (str): Действующий refresh-токен

    Returns:
        200 OK: Новый access_token
        400 Bad Request: Отсутствует или неверный refresh_token
    """

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
    """Получение профиля текущего авторизованного пользователя.

    Returns:
        200 OK: Данные пользователя (id, username, email, first_name, last_name, date_joined, last_login)
        401 Unauthorized: Пользователь не авторизован
    """

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