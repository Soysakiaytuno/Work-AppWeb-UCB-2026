from flask import Blueprint, jsonify
from sqlalchemy import text
from .extensions import db
from .models import Restaurante, Plato, Pedido

api_bp = Blueprint('api', __name__, url_prefix='/api')


@api_bp.route('/salud', methods=['GET'])
@api_bp.route('/health', methods=['GET'])
def salud():
    """Endpoint de comprobación de salud para Docker, NGINX y monitoreo."""
    try:
        db.session.execute(text("SELECT 1"))
        return jsonify({
            'status': 'ok',
            'database': 'connected',
            'restaurantes': Restaurante.query.count(),
            'platos': Plato.query.count(),
            'pedidos': Pedido.query.count(),
        }), 200
    except Exception as e:
        return jsonify({
            'status': 'error',
            'database': 'disconnected',
            'detail': str(e)
        }), 500
