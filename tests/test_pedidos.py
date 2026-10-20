import pytest
from app.extensions import db
from app.models import Restaurante, Plato, Pedido, ItemPedido


# ==============================================================================
# R6.1: Sin sesión, crear un pedido no crea nada y redirige al login (o 401)
# ==============================================================================
def test_sin_sesion_crear_pedido_no_crea_nada_y_redirige(client, app):
    with app.app_context():
        restaurante = Restaurante.query.first()
        plato = Plato.query.filter_by(restaurante_id=restaurante.id, disponible=True).first()
        conteo_inicial = Pedido.query.count()

    response = client.post('/pedidos', data={
        'restaurante_id': restaurante.id,
        'plato_id': [plato.id],
        'cantidad': [2]
    })

    # Debe redirigir al login (302) o devolver 401 no autorizado
    assert response.status_code in [302, 401]
    if response.status_code == 302:
        assert '/auth/login' in response.headers.get('Location', '')

    with app.app_context():
        # Comprobar que no se creó ninguna fila en la base de datos
        assert Pedido.query.count() == conteo_inicial


# ==============================================================================
# R6.2: Un cliente que intenta avanzar el estado de un pedido recibe 403
# ==============================================================================
def test_cliente_intentando_avanzar_estado_recibe_403(auth_cliente, app):
    with app.app_context():
        restaurante = Restaurante.query.first()
        pedido = Pedido(
            cliente='auth0|cliente_test_123',
            restaurante_id=restaurante.id,
            estado='pendiente',
            total=100.00
        )
        db.session.add(pedido)
        db.session.commit()
        pedido_id = pedido.id

    # El cliente intenta llamar a la ruta de cocina
    response = auth_cliente.post(f'/cocina/pedidos/{pedido_id}/avanzar')

    # Debe recibir 403 Forbidden
    assert response.status_code == 403

    with app.app_context():
        # El estado no debe haber cambiado
        pedido_actualizado = Pedido.query.get(pedido_id)
        assert pedido_actualizado.estado == 'pendiente'


# ==============================================================================
# R6.3: El total se calcula en el servidor (precio inventado se ignora)
# ==============================================================================
def test_total_calculado_en_servidor_ignora_precio_inventado(auth_cliente, app):
    with app.app_context():
        restaurante = Restaurante.query.first()
        plato = Plato.query.filter_by(restaurante_id=restaurante.id, disponible=True).first()
        precio_real = float(plato.precio)

    # El formulario envía maliciosamente un precio y un total falsos de $1.00
    response = auth_cliente.post('/pedidos', data={
        'restaurante_id': restaurante.id,
        'plato_id': [plato.id],
        'cantidad': [3],
        'precio_unitario': [1.00],  # Precio inventado
        'total': 1.00              # Total inventado
    }, follow_redirects=False)

    # Post/Redirect/Get
    assert response.status_code == 302

    with app.app_context():
        # Obtener el último pedido creado por este cliente
        pedido = Pedido.query.filter_by(cliente='auth0|cliente_test_123').order_by(Pedido.id.desc()).first()
        assert pedido is not None
        # El servidor calculó: 3 * precio_real
        total_esperado = round(3 * precio_real, 2)
        assert round(float(pedido.total), 2) == total_esperado
        
        # Verificar que el ítem congeló el precio real del plato y no el inventado
        item = pedido.items[0]
        assert round(float(item.precio_unitario), 2) == round(precio_real, 2)


# ==============================================================================
# R6.4: Plato no disponible rechaza pedido y no deja filas huérfanas
# ==============================================================================
def test_plato_no_disponible_rechaza_pedido_sin_filas_huerfanas(auth_cliente, app):
    with app.app_context():
        restaurante = Restaurante.query.first()
        plato_agotado = Plato.query.filter_by(restaurante_id=restaurante.id, disponible=False).first()
        assert plato_agotado is not None

        conteo_pedidos_ini = Pedido.query.count()
        conteo_items_ini = ItemPedido.query.count()

    response = auth_cliente.post('/pedidos', data={
        'restaurante_id': restaurante.id,
        'plato_id': [plato_agotado.id],
        'cantidad': [2]
    })

    # La petición debe ser rechazada (400)
    assert response.status_code == 400

    with app.app_context():
        # Atomicidad: no debe existir ninguna fila nueva en Pedido ni ItemPedido
        assert Pedido.query.count() == conteo_pedidos_ini
        assert ItemPedido.query.count() == conteo_items_ini


# ==============================================================================
# R6.5: Cliente que abre el pedido de otro cliente recibe 404 (no 403)
# ==============================================================================
def test_cliente_abre_pedido_ajeno_recibe_404(auth_cliente, app):
    with app.app_context():
        restaurante = Restaurante.query.first()
        # Pedido creado por OTRO cliente
        pedido_ajeno = Pedido(
            cliente='auth0|otro_usuario_distinto',
            restaurante_id=restaurante.id,
            estado='pendiente',
            total=80.00
        )
        db.session.add(pedido_ajeno)
        db.session.commit()
        pedido_ajeno_id = pedido_ajeno.id

    # El cliente logueado (auth0|cliente_test_123) intenta ver el pedido de otro
    response = auth_cliente.get(f'/pedidos/{pedido_ajeno_id}')

    # R2.6: Debe recibir 404 estricto (no 403, para no confirmar que existe)
    assert response.status_code == 404


# ==============================================================================
# R6.6: La cocina no puede pasar un pedido de listo a pendiente
# ==============================================================================
def test_cocina_no_puede_pasar_pedido_de_listo_a_pendiente(auth_cocina, app):
    with app.app_context():
        restaurante = Restaurante.query.first()
        pedido = Pedido(
            cliente='auth0|cliente_cualquiera',
            restaurante_id=restaurante.id,
            estado='listo',
            total=120.00
        )
        db.session.add(pedido)
        db.session.commit()
        pedido_id = pedido.id

    # Avanzar desde 'listo' solo puede ir a 'entregado', nunca a 'pendiente'
    # Intentamos avanzar el pedido
    response = auth_cocina.post(f'/cocina/pedidos/{pedido_id}/avanzar', follow_redirects=True)
    assert response.status_code == 200

    with app.app_context():
        pedido_actualizado = Pedido.query.get(pedido_id)
        # Avanzó a 'entregado'
        assert pedido_actualizado.estado == 'entregado'
        assert pedido_actualizado.estado != 'pendiente'

    # Intentar avanzar un pedido que ya está 'entregado' debe ser rechazado
    response_invalida = auth_cocina.post(f'/cocina/pedidos/{pedido_id}/avanzar')
    assert response_invalida.status_code == 400

    with app.app_context():
        # Sigue entregado, jamás volvió a 'pendiente'
        assert Pedido.query.get(pedido_id).estado == 'entregado'
