import os
import uuid
from flask import Flask, jsonify, abort, request
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import Uuid
from sqlalchemy.dialects.postgresql import UUID

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get(
    'DATABASE_URL',
    'postgresql://app:123qwe@localhost:5432/restaurant_database'
)
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class Usuario(db.Model):
    __tablename__ = 'usuario'
    __table_args__ = {'schema': 'content'}

    id = db.Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    nombre = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    telefono = db.Column(db.String(20))

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


@app.route('/personas', methods=['GET'])
def listar_personas():
    """GET /personas  →  todas las personas.
       Acepta ?nombre=... para filtrar."""
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

    if persona is None:
        abort(404)

    return jsonify({'success': True, 'persona': persona.format()})


@app.route('/', methods=['GET'])
def salud():
    """GET /  →  comprobación rápida de que la conexión funciona."""
    total = Usuario.query.count()
    return jsonify({'status': 'ok', 'personas_registradas': total})


@app.errorhandler(404)
def no_encontrado(error):
    return jsonify({'success': False, 'error': 404,
                    'mensaje': 'recurso no encontrado'}), 404


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(host='0.0.0.0', port=5000, debug=True)
