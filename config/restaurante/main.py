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


# --- Modelos SQLAlchemy ---

class Usuario(db.Model):
    __tablename__ = 'usuario'
    __table_args__ = {'schema': 'content'}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telefono = db.Column(db.String(20))
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


# --- Rutas de Vistas HTML (Layers) ---

@app.route('/', methods=['GET'])
@app.route('/usuarios', methods=['GET'])
def vista_usuarios():
    """GET / o /usuarios  →  vista HTML de usuarios."""
    usuarios = Usuario.query.order_by(Usuario.nombre).all()
    return render_template('usuarios/usuarios.html', listaUsuarios=usuarios)

@app.route('/usuario', methods=['GET', 'POST', 'PATCH', 'DELETE'])
def vista_usuario():
    """GET / o /usuario  →  vista HTML de un usuario."""
    if request.method == 'GET':
        try:
            id_buscado = request.args.get('usuario_id')
            if id_buscado:
                usuario = Usuario.query.get(id_buscado)
            else:
                usuario = None
        except:
            abort(404)
    elif request.method == 'POST':
        if request.form.get('methodvalue') == 'PATCH':
            try:
                usuario = Usuario.query.get(request.form.get('usuario_id'))
                usuario.nombre = request.form.get('usuario_nombre')
                usuario.email = request.form.get('usuario_email')
                usuario.telefono = request.form.get('usuario_telefono')
                db.session.commit()
            except:
                abort(404)
        elif request.form.get('methodvalue') == 'DELETE':
            try:
                usuario = Usuario.query.get(request.form.get('usuario_id'))
                db.session.delete(usuario)
                db.session.commit()
                usuario = None
            except:
                abort(404)
        else:
            try:
                usuario = Usuario(nombre=request.form.get('usuario_nombre_add'), email=request.form.get('usuario_email_add'), telefono=request.form.get('usuario_telefono_add'))
                db.session.add(usuario)
                db.session.commit()
            except:
                abort(404)
    return render_template('usuarios/usuario.html', user=usuario)


@app.route('/mesas', methods=['GET'])
def vista_mesas():
    """GET /mesas  →  vista HTML de mesas."""
    mesas = Mesa.query.order_by(Mesa.numero).all()
    return render_template('mesas/mesas.html', listaMesas=mesas)


@app.route('/productos', methods=['GET'])
def vista_productos():
    """GET /productos  →  vista HTML de productos."""
    productos = Producto.query.order_by(Producto.nombre).all()
    return render_template('productos/productos.html', listaProductos=productos)


@app.route('/recibos', methods=['GET'])
def vista_recibos():
    """GET /recibos  →  vista HTML de recibos (los 50 más recientes)."""
    recibos = Recibo.query.order_by(Recibo.creation_date.desc()).limit(50).all()
    return render_template('recibos/recibos.html', listaRecibos=recibos)


# --- Endpoints API JSON ---

@app.route('/personas', methods=['GET'])
def listar_personas():
    """GET /personas  →  todas las personas.
       Acepta ?nombre=... para filtrar."""
    """GET /personas  →  todas las personas en JSON."""
    consulta = Usuario.query

    nombre = request.args.get('nombre')
    if nombre:
        consulta = consulta.filter(Usuario.nombre.ilike(f'%{nombre}%'))

    personas = consulta.order_by(Usuario.nombre).all()

    return jsonify({
        'success': True,
        'total': len(personas),
        'personas': [p.format() for p in personas]
    })


@app.route('/personas/<person_id>', methods=['GET'])
def obtener_persona(person_id):
    """GET /personas/3  →  una sola persona, o 404."""
    persona = Usuario.query.get(person_id)
    """GET /personas/<person_id>  →  una sola persona por UUID en JSON."""
    try:
        persona = Usuario.query.filter_by(id=person_id).first()
    except Exception:
        abort(404)

    if persona is None:
        abort(404)

    return jsonify({'success': True, 'persona': persona.format()})


@app.route('/salud', methods=['GET'])
def salud():
    """GET /salud  →  comprobación rápida de que la conexión funciona."""
    total = Usuario.query.count()
    return jsonify({'status': 'ok', 'personas_registradas': total, 'docker': True})


@app.errorhandler(404)
def no_encontrado(error):
    return jsonify({'success': False, 'error': 404,
                    'mensaje': 'recurso no encontrado'}), 404


@app.errorhandler(500)
def error_servidor(error):
    return jsonify({'success': False, 'error': 500,
                    'mensaje': 'error interno del servidor'}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
