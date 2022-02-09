from django.contrib import admin
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from web.views import home

urlpatterns = [
    path('', home, name='home'),
]
