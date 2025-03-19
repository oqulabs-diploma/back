from django.urls import path
from v2.views import *

urlpatterns = [
    path('register', register),
    path('logout', logout_url)
]