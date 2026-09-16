import uuid
from django.db import models

class Usuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    email = models.CharField(max_length=150, unique=True, verbose_name="Correo Electrónico")
    telefono = models.CharField(max_length=20, blank=True, null=True, verbose_name="Teléfono")

    class Meta:
        managed = False
        db_table = 'usuario'
        verbose_name = 'Usuario'
        verbose_name_plural = 'Usuarios'
        ordering = ['nombre']

    def __str__(self):
        return f"{self.nombre} ({self.email})"

    def format(self):
        return {
            'id': str(self.id) if self.id else None,
            'nombre': self.nombre,
            'email': self.email,
            'telefono': self.telefono
        }


class Cliente(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        db_column='usuario_id',
        related_name='cliente_perfil',
        verbose_name="Usuario"
    )

    class Meta:
        managed = False
        db_table = 'cliente'
        verbose_name = 'Cliente'
        verbose_name_plural = 'Clientes'

    def __str__(self):
        return f"Cliente: {self.usuario.nombre}"


class RolEmpleado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=50, unique=True, verbose_name="Nombre del Rol")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    class Meta:
        managed = False
        db_table = 'rol_empleado'
        verbose_name = 'Rol de Empleado'
        verbose_name_plural = 'Roles de Empleados'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Empleado(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    usuario = models.OneToOneField(
        Usuario,
        on_delete=models.CASCADE,
        db_column='usuario_id',
        related_name='empleado_perfil',
        verbose_name="Usuario"
    )
    rol = models.ForeignKey(
        RolEmpleado,
        on_delete=models.PROTECT,
        db_column='rol_id',
        related_name='empleados',
        verbose_name="Rol"
    )

    class Meta:
        managed = False
        db_table = 'empleado'
        verbose_name = 'Empleado'
        verbose_name_plural = 'Empleados'

    def __str__(self):
        return f"{self.usuario.nombre} - {self.rol.nombre}"


class Mesa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.IntegerField(unique=True, verbose_name="Número de Mesa")
    capacidad = models.IntegerField(verbose_name="Capacidad de Personas")

    class Meta:
        managed = False
        db_table = 'mesa'
        verbose_name = 'Mesa'
        verbose_name_plural = 'Mesas'
        ordering = ['numero']

    def __str__(self):
        return f"Mesa #{self.numero} (Capacidad: {self.capacidad})"

    def format(self):
        return {
            'id': str(self.id) if self.id else None,
            'numero': self.numero,
            'capacidad': self.capacidad
        }


class CategoriaProducto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100, verbose_name="Categoría")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")

    class Meta:
        managed = False
        db_table = 'categoria_producto'
        verbose_name = 'Categoría de Producto'
        verbose_name_plural = 'Categorías de Productos'
        ordering = ['nombre']

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categoria = models.ForeignKey(
        CategoriaProducto,
        on_delete=models.CASCADE,
        db_column='categoria_id',
        related_name='productos',
        verbose_name="Categoría"
    )
    nombre = models.CharField(max_length=100, verbose_name="Nombre")
    descripcion = models.TextField(blank=True, null=True, verbose_name="Descripción")
    ingredientes = models.TextField(blank=True, null=True, verbose_name="Ingredientes")
    precio = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio ($)")

    class Meta:
        managed = False
        db_table = 'producto'
        verbose_name = 'Producto'
        verbose_name_plural = 'Productos'
        ordering = ['categoria', 'nombre']

    def __str__(self):
        return f"{self.nombre} (${self.precio})"

    def format(self):
        return {
            'id': str(self.id) if self.id else None,
            'categoria_id': str(self.categoria_id) if self.categoria_id else None,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'ingredientes': self.ingredientes,
            'precio': float(self.precio) if self.precio is not None else 0.0
        }


class Recibo(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        db_column='cliente_id',
        related_name='recibos',
        verbose_name="Cliente"
    )
    mesero = models.ForeignKey(
        Empleado,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_column='mesero_id',
        related_name='recibos_atendidos',
        verbose_name="Mesero"
    )
    mesa = models.ForeignKey(
        Mesa,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        db_column='mesa_id',
        related_name='recibos',
        verbose_name="Mesa"
    )
    tipo_pedido = models.CharField(max_length=50, default='Local', verbose_name="Tipo de Pedido")
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Total ($)")
    metodo_pago = models.CharField(max_length=50, blank=True, null=True, verbose_name="Método de Pago")
    creation_date = models.DateField(auto_now_add=False, verbose_name="Fecha de Creación")

    class Meta:
        managed = False
        db_table = 'recibo'
        verbose_name = 'Recibo'
        verbose_name_plural = 'Recibos'
        ordering = ['-creation_date']

    def __str__(self):
        return f"Recibo {self.id} | {self.tipo_pedido} - ${self.total}"

    def format(self):
        return {
            'id': str(self.id) if self.id else None,
            'cliente_id': str(self.cliente_id) if self.cliente_id else None,
            'mesero_id': str(self.mesero_id) if self.mesero_id else None,
            'mesa_id': str(self.mesa_id) if self.mesa_id else None,
            'tipo_pedido': self.tipo_pedido,
            'total': float(self.total) if self.total is not None else 0.0,
            'metodo_pago': self.metodo_pago,
            'creation_date': str(self.creation_date) if self.creation_date else None
        }


class ReciboDetalle(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recibo = models.ForeignKey(
        Recibo,
        on_delete=models.CASCADE,
        db_column='recibo_id',
        related_name='detalles',
        verbose_name="Recibo"
    )
    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        db_column='producto_id',
        related_name='detalles_consumo',
        verbose_name="Producto"
    )
    cantidad = models.IntegerField(default=1, verbose_name="Cantidad")
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Precio Unitario ($)")

    class Meta:
        managed = False
        db_table = 'recibo_detalle'
        verbose_name = 'Detalle de Recibo'
        verbose_name_plural = 'Detalles de Recibos'

    def __str__(self):
        return f"{self.cantidad}x {self.producto.nombre} (${self.precio_unitario})"
