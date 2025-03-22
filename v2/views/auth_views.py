from django.contrib.auth import logout, login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from v2.serializers import *
from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model

@api_view(['POST'])
@permission_classes([AllowAny])
def register(request):
    serializer = UserRegistrationSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"error": serializer.errors},
            status=status.HTTP_400_BAD_REQUEST
        )

    serializer.save()
    return Response({"detail": "Пользователь успешно зарегистрирован."}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def logout_url(request):
    logout(request)
    return Response({"detail": "Пользователь разлогинен."}, status=status.HTTP_200_OK)

@api_view(["POST"])
@permission_classes([AllowAny])
def login(request):
    """Custom login view that returns JWT token."""
    email = request.data.get("email")
    password = request.data.get("password")

    User = get_user_model()

    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)

    user = authenticate(username=user.username, password=password)
    if user is not None:
        from rest_framework_simplejwt.tokens import RefreshToken

        refresh = RefreshToken.for_user(user)

        if user.is_superuser:
            role = 'admin'
        elif user.is_staff:
            role = 'teacher'
        else:
            role = 'student'

        return Response(
            {
                "refresh": str(refresh),
                "access": str(refresh.access_token),
                "role": role,
            },
            status=status.HTTP_200_OK,
        )

    return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)