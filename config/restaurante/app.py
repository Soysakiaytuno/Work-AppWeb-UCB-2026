import os
import uuid
from flask import Flask, jsonify, abort, request
from flask import Flask, jsonify, abort, request, render_template
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import UUID
from flask_migrate import Migrate

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://app:123qwe@localhost:5432/restaurant_database'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
migrar = Migrate(app, db)

# --- Modelos SQLAlchemy ---

class Usuario(db.Model):
    __tablename__ = 'usuario'
    __table_args__ = {'schema': 'content'}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
    edad = db.Column(db.Integer, nullable=False)
    def __init__(self, nombre, email, telefono):
        self.nombre = nombre
        self.email = email
        self.telefono = telefono

    def __repr__(self):
        return f'<Usuario id={self.id} nombre={self.nombre}>'

    def format(self):
        """Convierte el objeto Python en un diccionario serializable a JSON."""
        return {
            'id': str(self.id) if self.id else None,
            'nombre': self.nombre,
            'email': self.email,
            'telefono': self.telefono
        }


class Mesa(db.Model):
    __tablename__ = 'mesa'
    __table_args__ = {'schema': 'content'}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    numero = db.Column(db.Integer, nullable=False, unique=True)
    capacidad = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Mesa numero={self.numero} capacidad={self.capacidad}>'

    def format(self):
        return {
            'id': str(self.id) if self.id else None,
            'numero': self.numero,
            'capacidad': self.capacidad
        }


class Producto(db.Model):
    __tablename__ = 'producto'
    __table_args__ = {'schema': 'content'}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    categoria_id = db.Column(UUID(as_uuid=True), nullable=False)
    nombre = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text)
    ingredientes = db.Column(db.Text)
    precio = db.Column(db.Numeric(10, 2), nullable=False)

    def __repr__(self):
        return f'<Producto nombre={self.nombre} precio={self.precio}>'

    def format(self):
        return {
            'id': str(self.id) if self.id else None,
            'categoria_id': str(self.categoria_id) if self.categoria_id else None,
            'nombre': self.nombre,
            'descripcion': self.descripcion,
            'ingredientes': self.ingredientes,
            'precio': float(self.precio) if self.precio is not None else 0.0
        }


class Recibo(db.Model):
    __tablename__ = 'recibo'
    __table_args__ = {'schema': 'content'}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    cliente_id = db.Column(UUID(as_uuid=True), nullable=False)
    mesero_id = db.Column(UUID(as_uuid=True), nullable=True)
    mesa_id = db.Column(UUID(as_uuid=True), nullable=True)
    tipo_pedido = db.Column(db.String(50), default='Local')
    total = db.Column(db.Numeric(10, 2), nullable=False, default=0.00)
    metodo_pago = db.Column(db.String(50))
    creation_date = db.Column(db.Date, nullable=False)

    def __repr__(self):
        return f'<Recibo id={self.id} total={self.total}>'

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

