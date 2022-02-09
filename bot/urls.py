from django.contrib import admin
from django.urls import path
from bot.views import *
from django.views.decorators.csrf import csrf_exempt


urlpatterns = [
    path('', csrf_exempt(TutorialBotView.as_view())),
]
