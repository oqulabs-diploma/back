from typing import Any
import random

from django.conf import settings
from django.contrib.auth import logout, login
from django.contrib.auth.models import User
from django.http import (
    HttpResponse,
    HttpResponseRedirect,
)

from app.models import ForgotPassword

from django.shortcuts import render, redirect
from django.core.handlers.wsgi import WSGIRequest

from app.forms import (
    UserRegistrationModelForm,
    UserLoginModelForm,
    UserForgotPasswordForm,
    UserForgotPasswordFormStep2,
)
from app.decorators import (
    redirect_authenticated_user,
    redirect_non_authenticated_user,
)
from utils.forms.helpers import get_first_error_text


@redirect_authenticated_user(redirect_to="/")
def login_url(
    request: WSGIRequest,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any]
) -> HttpResponse | HttpResponseRedirect:

    if request.method == 'POST':
        email = request.POST.get("email").lower()
        if "super." in email and settings.ALLOW_DEBUG_LOGIN:
            user = User.objects.filter(email=email.replace("super.", "")).first()
            if user:
                login(request=request, user=user)
                return redirect('/')

        form: UserLoginModelForm = UserLoginModelForm(request.POST)
        if not form.is_valid():
            return render(
                request=request,
                template_name="login.html",
                context={
                    "error": get_first_error_text(form),
                }
            )
        user: User = form.cleaned_data.get('user')
        login(request=request, user=user)
        return redirect('/')
    return render(request=request, template_name="login.html")


@redirect_non_authenticated_user(redirect_to="/login")
def logout_url(
    request: WSGIRequest,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any]
) -> HttpResponseRedirect:
    logout(request)
    return redirect('/login')


@redirect_authenticated_user(redirect_to="/")
def register_url(
    request: WSGIRequest,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any]
) -> HttpResponse | HttpResponseRedirect:
    context = {
        "type": "student"
    }

    if request.method == 'POST':
        form: UserRegistrationModelForm = UserRegistrationModelForm(request.POST)
        if not form.is_valid():
            return render(
                request=request,
                template_name="register.html",
                context={
                    "error": get_first_error_text(form),
                }
            )
        user: User = form.save()
        login(request=request, user=user)
        return redirect('/')
    return render(request, "register.html", context)


@redirect_authenticated_user(redirect_to="/")
def forgot_url(
    request: WSGIRequest,
) -> HttpResponse | HttpResponseRedirect:
    context = {
        "type": "forgot"
    }
    if request.method == 'POST':
        form: UserForgotPasswordForm = UserForgotPasswordForm(request.POST)
        if not form.is_valid():
            return render(
                request=request,
                template_name="forgot.html",
                context={
                    "error": get_first_error_text(form),
                }
            )
        try:
            email = form.cleaned_data.get('email').lower()
            user = User.objects.get(email=email)
            ForgotPassword.objects.filter(user=user).delete()
            forgot_password = ForgotPassword.objects.create(
                user=user,
                token=random.randint(1000, 9999),
            )
            forgot_password.send_email()
        except User.DoesNotExist:
            pass

        return redirect('/forgot/step2')

    return render(request, "forgot.html", context)


@redirect_authenticated_user(redirect_to="/")
def forgot_step_2_url(
    request: WSGIRequest,
) -> HttpResponse | HttpResponseRedirect:
    context = {
        "type": "forgot"
    }
    if request.method == 'POST':
        form: UserForgotPasswordFormStep2 = UserForgotPasswordFormStep2(request.POST)
        if not form.is_valid():
            return render(
                request=request,
                template_name="forgot2.html",
                context={
                    "error": get_first_error_text(form),
                }
            )
        try:
            email = form.cleaned_data.get('email').lower()
            user = User.objects.get(email=email)
            token = form.cleaned_data.get('token')
            new_password = form.cleaned_data.get('new_password')
            ForgotPassword.objects.get(user=user, token=token)
            user.set_password(new_password)
            user.save()
            ForgotPassword.objects.filter(user=user).delete()
        except Exception as e:
            pass

        return redirect('/')

    return render(request, "forgot2.html", context)


@redirect_authenticated_user(redirect_to="/")
def teacher_registration(
    request: WSGIRequest,
    *args: tuple[Any, ...],
    **kwargs: dict[str, Any]
) -> HttpResponse | HttpResponseRedirect:
    context = {
        "type": "teacher"
    }
    if request.method == 'POST':
        form: UserRegistrationModelForm = UserRegistrationModelForm(request.POST)
        if not form.is_valid():
            return render(
                request=request,
                template_name="register.html",
                context={
                    "error": get_first_error_text(form),
                }
            )
        user: User = form.save()
        user.is_staff = True
        user.save()
        login(request=request, user=user)
        return redirect('/')
    return render(request, "register.html", context)


def home(request):
    if not request.user.is_anonymous:
        return redirect('/courses')

    return redirect('/login')
