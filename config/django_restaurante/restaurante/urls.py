from django.urls import path
from . import views

urlpatterns = [
    # Vistas HTML
    path('', views.vista_usuarios, name='inicio'),
    path('usuarios', views.vista_usuarios, name='usuarios'),
    path('mesas', views.vista_mesas, name='mesas'),
    path('productos', views.vista_productos, name='productos'),
    path('recibos', views.vista_recibos, name='recibos'),

    # Endpoints API JSON
    path('personas', views.listar_personas, name='listar_personas'),
    path('personas/<uuid:person_id>', views.obtener_persona, name='obtener_persona'),
    path('salud', views.salud, name='salud'),
]
