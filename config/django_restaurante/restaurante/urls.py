from django.urls import path
from . import views

urlpatterns = [
    # Endpoints API JSON auxiliares
    path('salud', views.salud, name='salud'),
    path('personas', views.listar_personas, name='listar_personas'),
    path('personas/<uuid:person_id>', views.obtener_persona, name='obtener_persona'),
]
