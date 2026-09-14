import uuid
from django.db import models

class Usuario(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    email = models.CharField(max_length=150, unique=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'usuario'

    def __str__(self):
        return f'{self.nombre} ({self.email})'

    def format(self):
        return {
            'id': str(self.id) if self.id else None,
            'nombre': self.nombre,
            'email': self.email,
            'telefono': self.telefono
        }


class Mesa(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    numero = models.IntegerField(unique=True)
    capacidad = models.IntegerField()

    class Meta:
        managed = False
        db_table = 'mesa'

    def __str__(self):
        return f'Mesa {self.numero} (Capacidad: {self.capacidad})'

    def format(self):
        return {
            'id': str(self.id) if self.id else None,
            'numero': self.numero,
            'capacidad': self.capacidad
        }


class CategoriaProducto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'categoria_producto'

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    categoria = models.ForeignKey(CategoriaProducto, on_delete=models.CASCADE, db_column='categoria_id')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True, null=True)
    ingredientes = models.TextField(blank=True, null=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        managed = False
        db_table = 'producto'

    def __str__(self):
        return f'{self.nombre} - ${self.precio}'

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
    cliente_id = models.UUIDField()
    mesero_id = models.UUIDField(blank=True, null=True)
    mesa_id = models.UUIDField(blank=True, null=True)
    tipo_pedido = models.CharField(max_length=50, default='Local')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)
    metodo_pago = models.CharField(max_length=50, blank=True, null=True)
    creation_date = models.DateField()

    class Meta:
        managed = False
        db_table = 'recibo'

    def __str__(self):
        return f'Recibo {self.id} - ${self.total}'

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
