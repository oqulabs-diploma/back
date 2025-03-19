from django.urls import path
from v2 import views

urlpatterns = [
    path('register', views.register_url),
    path('logout', views.logout)
]