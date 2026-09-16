from django.contrib import admin
from django.urls import path, include
from django.shortcuts import redirect

admin.site.site_header = "Panel de Administración - Restaurante"
admin.site.site_title = "Restaurante Admin"
admin.site.index_title = "Gestión de Datos del Restaurante"

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', lambda request: redirect('admin/', permanent=False)),
    path('api/', include('restaurante.urls')),
]
