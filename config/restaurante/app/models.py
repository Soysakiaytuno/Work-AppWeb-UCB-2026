from datetime import datetime, timezone
from .extensions import db


class Restaurante(db.Model):
    __tablename__ = 'restaurante_restaurante'

    id = db.Column(db.BigInteger, primary_key=True)
    nombre = db.Column(db.String(100), nullable=False)
    direccion = db.Column(db.String(200), nullable=False)
    telefono = db.Column(db.String(20), nullable=True)

    # Relación 1—N con Plato
    platos = db.relationship('Plato', backref='restaurante', lazy=True, cascade='all, delete-orphan')
    pedidos = db.relationship('Pedido', backref='restaurante', lazy=True)

    def __repr__(self):
        return f'<Restaurante id={self.id} nombre={self.nombre}>'

    def format(self):
        return {
            'id': self.id,
            'nombre': self.nombre,
            'direccion': self.direccion,
            'telefono': self.telefono,
            'platos': [p.format() for p in self.platos if p.disponible]
        }


class Plato(db.Model):
    __tablename__ = 'restaurante_plato'

    id = db.Column(db.BigInteger, primary_key=True)
    restaurante_id = db.Column(db.BigInteger, db.ForeignKey('restaurante_restaurante.id'), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=True)
    precio = db.Column(db.Numeric(10, 2), nullable=False)
    disponible = db.Column(db.Boolean, default=True, nullable=False)

    def __repr__(self):
        return f'<Plato id={self.id} nombre={self.nombre} precio={self.precio}>'

    def format(self):
        return {
            'id': self.id,
            'restaurante_id': self.restaurante_id,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'precio': float(self.precio) if self.precio is not None else 0.0,
            'disponible': self.disponible
        }


class Pedido(db.Model):
    __tablename__ = 'restaurante_pedido'

    id = db.Column(db.BigInteger, primary_key=True)
    # Identificado por el 'sub' de Auth0 (ej: auth0|65f...)
    cliente = db.Column(db.String(150), nullable=False)
    restaurante_id = db.Column(db.BigInteger, db.ForeignKey('restaurante_restaurante.id'), nullable=False)
    estado = db.Column(db.String(20), default='pendiente', nullable=False)
    fecha = db.Column(db.DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    total = db.Column(db.Numeric(10, 2), default=0.00, nullable=False)

    # Relación 1—N con ItemPedido
    items = db.relationship('ItemPedido', backref='pedido', lazy=True, cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Pedido id={self.id} cliente={self.cliente} estado={self.estado} total={self.total}>'

    def format(self):
        return {
            'id': self.id,
            'cliente': self.cliente,
            'restaurante_id': self.restaurante_id,
            'restaurante_nombre': self.restaurante.nombre if self.restaurante else None,
            'estado': self.estado,
            'fecha': self.fecha.isoformat() if self.fecha else None,
            'total': float(self.total) if self.total is not None else 0.0,
            'items': [i.format() for i in self.items]
        }


class ItemPedido(db.Model):
    __tablename__ = 'restaurante_itempedido'

    id = db.Column(db.BigInteger, primary_key=True)
    pedido_id = db.Column(db.BigInteger, db.ForeignKey('restaurante_pedido.id'), nullable=False)
    plato_id = db.Column(db.BigInteger, db.ForeignKey('restaurante_plato.id'), nullable=False)
    cantidad = db.Column(db.Integer, default=1, nullable=False)
    precio_unitario = db.Column(db.Numeric(10, 2), nullable=False)

    # Relación directa con Plato para consultar detalles (ej: nombre)
    plato = db.relationship('Plato', lazy=True)

    def __repr__(self):
        return f'<ItemPedido id={self.id} plato_id={self.plato_id} cantidad={self.cantidad}>'

    def format(self):
        return {
            'id': self.id,
            'pedido_id': self.pedido_id,
            'plato_id': self.plato_id,
            'plato_nombre': self.plato.nombre if self.plato else None,
            'cantidad': self.cantidad,
            'precio_unitario': float(self.precio_unitario) if self.precio_unitario is not None else 0.0,
            'subtotal': float(self.precio_unitario * self.cantidad) if self.precio_unitario is not None else 0.0
        }
