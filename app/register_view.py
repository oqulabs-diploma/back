from django.contrib.auth import login, logout
from django.http import HttpResponseRedirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

from app.forms import UserRegistrationModelForm
from utils.forms.helpers import get_first_error_text


@api_view(['POST'])
@permission_classes([AllowAny])
def register_api(request):
    if request.user.is_authenticated:
        return HttpResponseRedirect('/')

    form = UserRegistrationModelForm(request.data)
    if not form.is_valid():
        return Response(
            {"error": get_first_error_text(form)},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = form.save()
    login(request, user)
    return Response({"detail": "Пользователь успешно зарегистрирован."}, status=status.HTTP_201_CREATED)


@api_view(['GET'])
@permission_classes([AllowAny])
def logout_api(request):
    logout(request)
    return Response({"detail": "Пользователь разлогинен."}, status=status.HTTP_200_OK)