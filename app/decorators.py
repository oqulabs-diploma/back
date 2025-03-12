# Python
from functools import wraps
from typing import Callable, Any

# Django
from django.http import HttpResponseRedirect
from django.core.handlers.wsgi import WSGIRequest
from django.shortcuts import redirect


def redirect_authenticated_user(redirect_to: str = "/") -> Callable:
    def decorator(view_func: Callable[[WSGIRequest, tuple[Any, ...], dict[str, Any]], Any]) -> Callable:
        @wraps(view_func)
        def _wrapped_view(
            request: WSGIRequest,
            *args: tuple[Any, ...],
            **kwargs: dict[str, Any]
        ) -> HttpResponseRedirect | Any:
            if request.user.is_authenticated:
                return redirect(redirect_to)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator


def redirect_non_authenticated_user(redirect_to: str = "/login") -> Callable:
    def decorator(view_func: Callable[[WSGIRequest, tuple[Any, ...], dict[str, Any]], Any]) -> Callable:
        @wraps(view_func)
        def _wrapped_view(
            request: WSGIRequest,
            *args: tuple[Any, ...],
            **kwargs: dict[str, Any]
        ) -> HttpResponseRedirect | Any:
            if not request.user.is_authenticated:
                return redirect(redirect_to)
            return view_func(request, *args, **kwargs)
        return _wrapped_view
    return decorator
