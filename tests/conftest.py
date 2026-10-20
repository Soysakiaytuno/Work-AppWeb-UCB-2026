import os
import sys
import datetime
import jwt
import pytest

# Asegurar que el paquete de la app Flask esté en el PYTHONPATH
RESTAURANTE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'config', 'restaurante'))
if RESTAURANTE_DIR not in sys.path:
    sys.path.insert(0, RESTAURANTE_DIR)

from app import create_app
from app.extensions import db
from app.models import Restaurante, Plato, Pedido, ItemPedido


class TestConfig:
    TESTING = True
    SECRET_KEY = 'test-secret-key-for-pytest-execution'
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql+psycopg2://app:123qwe@localhost:5432/restaurant_database'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = False


@pytest.fixture(scope='session')
def app():
    """Instancia la aplicación Flask en modo prueba."""
    app = create_app(TestConfig)
    
    with app.app_context():
        # Asegurar que existan datos base de prueba para los tests
        r = Restaurante.query.filter_by(nombre='Test Bistro').first()
        if not r:
            r = Restaurante(nombre='Test Bistro', direccion='Calle Prueba 123', telefono='77788899')
            db.session.add(r)
            db.session.commit()

        p1 = Plato.query.filter_by(nombre='Hamburguesa Clasica', restaurante_id=r.id).first()
        if not p1:
            p1 = Plato(restaurante_id=r.id, nombre='Hamburguesa Clasica', precio=50.00, disponible=True)
            db.session.add(p1)

        p2 = Plato.query.filter_by(nombre='Papas Rusticas', restaurante_id=r.id).first()
        if not p2:
            p2 = Plato(restaurante_id=r.id, nombre='Papas Rusticas', precio=20.00, disponible=True)
            db.session.add(p2)

        p_agotado = Plato.query.filter_by(nombre='Postre Agotado', restaurante_id=r.id).first()
        if not p_agotado:
            p_agotado = Plato(restaurante_id=r.id, nombre='Postre Agotado', precio=30.00, disponible=False)
            db.session.add(p_agotado)

        db.session.commit()

    yield app


@pytest.fixture
def client(app):
    """Cliente de prueba HTTP de Flask."""
    return app.test_client()


def generar_token_prueba(secret_key, sub, permissions):
    """Genera un token JWT de prueba firmado con HS256 para simular Auth0 sin red."""
    payload = {
        'sub': sub,
        'permissions': permissions,
        'iat': datetime.datetime.now(datetime.timezone.utc),
        'exp': datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=2),
    }
    return jwt.encode(payload, secret_key, algorithm='HS256')


@pytest.fixture
def auth_cliente(app, client):
    """Simula una sesión autenticada con rol Cliente."""
    token = generar_token_prueba(
        app.config['SECRET_KEY'],
        sub='auth0|cliente_test_123',
        permissions=['create:pedidos', 'read:mis-pedidos']
    )
    with client.session_transaction() as sess:
        sess['access_token'] = token
        sess['user'] = {
            'name': 'Cliente Test',
            'email': 'cliente@test.com',
            'sub': 'auth0|cliente_test_123'
        }
    return client


@pytest.fixture
def auth_cocina(app, client):
    """Simula una sesión autenticada con rol Cocina."""
    token = generar_token_prueba(
        app.config['SECRET_KEY'],
        sub='auth0|cocinero_test_456',
        permissions=['read:pedidos', 'update:pedidos']
    )
    with client.session_transaction() as sess:
        sess['access_token'] = token
        sess['user'] = {
            'name': 'Chef Test',
            'email': 'cocina@test.com',
            'sub': 'auth0|cocinero_test_456'
        }
    return client
