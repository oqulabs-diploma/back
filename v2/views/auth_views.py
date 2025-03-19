from django.contrib.auth import logout, login
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status
from v2.serializers import *
from utils.forms.helpers import get_first_error_text


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
