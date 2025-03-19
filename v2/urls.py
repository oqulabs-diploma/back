from django.urls import path
from v2.views import courses_view, auth_views

urlpatterns = [
    path('register', auth_views.register),
    path('login', auth_views.login),
    path('logout', auth_views.logout_url),
    path('courses', courses_view.courses_student)
]