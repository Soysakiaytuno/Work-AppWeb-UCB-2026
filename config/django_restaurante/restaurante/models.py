from django.db import models
from django.core.validators import MinValueValidator


class Restaurante(models.Model):
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    direccion = models.CharField(max_length=200, verbose_name="Dirección")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")

    class Meta:
        verbose_name = "Restaurante"
        verbose_name_plural = "Restaurantes"
        ordering = ["nombre"]

    def __str__(self):
        return self.nombre


class Plato(models.Model):
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name="platos",
        verbose_name="Restaurante"
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre del Plato")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        verbose_name="Precio ($)"
    )
    disponible = models.BooleanField(default=True, verbose_name="Disponible")

    class Meta:
        verbose_name = "Plato"
        verbose_name_plural = "Platos"
        ordering = ["restaurante", "nombre"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(precio__gte=0),
                name="check_plato_precio_no_negativo"
            )
        ]

    def __str__(self):
        return f"{self.nombre} (${self.precio}) - {self.restaurante.nombre}"


class Pedido(models.Model):
    ESTADOS_VALIDOS = [
        ('pendiente', 'Pendiente'),
        ('en_preparacion', 'En Preparación'),
        ('listo', 'Listo'),
        ('entregado', 'Entregado'),
        ('cancelado', 'Cancelado'),
    ]

    # El cliente se identifica por el 'sub' del token de Auth0 (ej. auth0|65f...)
    cliente = models.CharField(max_length=150, verbose_name="ID Cliente (Auth0 sub)")
    restaurante = models.ForeignKey(
        Restaurante,
        on_delete=models.CASCADE,
        related_name="pedidos",
        verbose_name="Restaurante"
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADOS_VALIDOS,
        default='pendiente',
        verbose_name="Estado"
    )
    fecha = models.DateTimeField(auto_now_add=True, verbose_name="Fecha y Hora")
    total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0.00,
        validators=[MinValueValidator(0.00)],
        verbose_name="Total ($)"
    )

    class Meta:
        verbose_name = "Pedido"
        verbose_name_plural = "Pedidos"
        ordering = ["-fecha"]
        constraints = [
            models.CheckConstraint(
                condition=models.Q(estado__in=['pendiente', 'en_preparacion', 'listo', 'entregado', 'cancelado']),
                name="check_pedido_estado_valido"
            ),
            models.CheckConstraint(
                condition=models.Q(total__gte=0),
                name="check_pedido_total_no_negativo"
            )
        ]

    def __str__(self):
        return f"Pedido #{self.id} - {self.restaurante.nombre} [{self.estado}] - ${self.total}"


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido,
        on_delete=models.CASCADE,
        related_name="items",
        verbose_name="Pedido"
    )
    plato = models.ForeignKey(
        Plato,
        on_delete=models.PROTECT,
        related_name="items_pedidos",
        verbose_name="Plato"
    )
    cantidad = models.IntegerField(
        default=1,
        validators=[MinValueValidator(1)],
        verbose_name="Cantidad"
    )
    precio_unitario = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0.00)],
        verbose_name="Precio Unitario ($)"
    )

    class Meta:
        verbose_name = "Ítem de Pedido"
        verbose_name_plural = "Ítems de Pedidos"
        constraints = [
            models.CheckConstraint(
                condition=models.Q(cantidad__gt=0),
                name="check_item_cantidad_positiva"
            ),
            models.CheckConstraint(
                condition=models.Q(precio_unitario__gte=0),
                name="check_item_precio_no_negativo"
            )
        ]

    def __str__(self):
        return f"{self.cantidad}x {self.plato.nombre} (${self.precio_unitario})"
