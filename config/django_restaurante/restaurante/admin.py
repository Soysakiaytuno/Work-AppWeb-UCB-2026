from django.contrib import admin
from .models import Restaurante, Plato, Pedido, ItemPedido


@admin.register(Restaurante)
class RestauranteAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'direccion', 'telefono')
    search_fields = ('nombre', 'direccion')
    ordering = ('nombre',)


@admin.register(Plato)
class PlatoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'restaurante', 'precio', 'disponible')
    list_filter = ('restaurante', 'disponible')
    search_fields = ('nombre', 'descripcion')
    ordering = ('restaurante', 'nombre')


class ItemPedidoInline(admin.TabularInline):
    model = ItemPedido
    extra = 0
    fields = ('plato', 'cantidad', 'precio_unitario')
    # R3.3: Los precios de los ítems son de solo lectura
    readonly_fields = ('precio_unitario',)


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    # R3.1: Columnas útiles
    list_display = ('id', 'cliente', 'restaurante', 'estado', 'fecha', 'total')
    # R3.1: Filtros por estado y restaurante
    list_filter = ('estado', 'restaurante')
    # R3.1: Búsqueda por cliente (sub de Auth0)
    search_fields = ('cliente',)
    # R3.3: El total es de solo lectura (nadie lo edita a mano)
    readonly_fields = ('total', 'fecha')
    # R3.2: Ítems en línea dentro del pedido
    inlines = [ItemPedidoInline]
    ordering = ('-fecha',)
