from django.urls import path

from .views import *

urlpatterns = [
    path('environment/', EnvironmentView.as_view()),
    path('service/', ServiceView.as_view()),
]