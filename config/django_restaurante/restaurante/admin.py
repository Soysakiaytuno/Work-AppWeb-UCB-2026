from django.contrib import admin
from .models import (
    Usuario,
    Cliente,
    RolEmpleado,
    Empleado,
    Mesa,
    CategoriaProducto,
    Producto,
    Recibo,
    ReciboDetalle,
)


@admin.register(Usuario)
class UsuarioAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'email', 'telefono')
    search_fields = ('nombre', 'email', 'telefono')
    ordering = ('nombre',)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'get_email', 'get_telefono')
    search_fields = ('usuario__nombre', 'usuario__email')

    @admin.display(description='Correo Electrónico')
    def get_email(self, obj):
        return obj.usuario.email

    @admin.display(description='Teléfono')
    def get_telefono(self, obj):
        return obj.usuario.telefono


@admin.register(RolEmpleado)
class RolEmpleadoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Empleado)
class EmpleadoAdmin(admin.ModelAdmin):
    list_display = ('usuario', 'rol', 'get_email')
    list_filter = ('rol',)
    search_fields = ('usuario__nombre', 'usuario__email')

    @admin.display(description='Correo Electrónico')
    def get_email(self, obj):
        return obj.usuario.email


@admin.register(Mesa)
class MesaAdmin(admin.ModelAdmin):
    list_display = ('numero', 'capacidad')
    list_filter = ('capacidad',)
    search_fields = ('numero',)
    ordering = ('numero',)


@admin.register(CategoriaProducto)
class CategoriaProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'descripcion')
    search_fields = ('nombre',)


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'categoria', 'precio')
    list_filter = ('categoria',)
    search_fields = ('nombre', 'descripcion', 'ingredientes')
    ordering = ('categoria', 'nombre')


class ReciboDetalleInline(admin.TabularInline):
    model = ReciboDetalle
    extra = 1
    fields = ('producto', 'cantidad', 'precio_unitario')


@admin.register(Recibo)
class ReciboAdmin(admin.ModelAdmin):
    list_display = (
        'id',
        'cliente',
        'mesero',
        'mesa',
        'tipo_pedido',
        'total',
        'metodo_pago',
        'creation_date',
    )
    list_filter = ('tipo_pedido', 'metodo_pago', 'creation_date')
    search_fields = ('cliente__usuario__nombre', 'mesero__usuario__nombre')
    date_hierarchy = 'creation_date'
    ordering = ('-creation_date',)
    inlines = [ReciboDetalleInline]


@admin.register(ReciboDetalle)
class ReciboDetalleAdmin(admin.ModelAdmin):
    list_display = ('recibo', 'producto', 'cantidad', 'precio_unitario')
    list_filter = ('producto',)
    search_fields = ('producto__nombre',)
