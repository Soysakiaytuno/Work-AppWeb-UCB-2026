from django.urls import path
from . import views

urlpatterns = [
    path('salud', views.salud, name='salud'),
]
