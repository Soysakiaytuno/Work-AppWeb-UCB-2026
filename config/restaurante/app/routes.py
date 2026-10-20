from flask import Blueprint, render_template, request, redirect, url_for, abort, flash
from .extensions import db
from .models import Restaurante, Plato, Pedido, ItemPedido
from .auth import requires_auth

views_bp = Blueprint('views', __name__)

# Transiciones de estado permitidas para el rol cocina
TRANSICIONES_COCINA = {
    'pendiente': 'en_preparacion',
    'en_preparacion': 'listo',
    'listo': 'entregado',
}


# ==============================================================================
# 1. CARTA PÚBLICA (Sin login - R2.3)
# ==============================================================================

@views_bp.route('/', methods=['GET'])
def pagina_inicio():
    """Catálogo público de restaurantes y sus platos disponibles."""
    restaurantes = Restaurante.query.order_by(Restaurante.nombre).all()
    return render_template('carta/index.html', restaurantes=restaurantes)


@views_bp.route('/restaurantes/<int:restaurante_id>', methods=['GET'])
def detalle_restaurante(restaurante_id):
    """Detalle de un restaurante y formulario para armar un pedido."""
    restaurante = Restaurante.query.get(restaurante_id)
    if not restaurante:
        abort(404)
    platos = Plato.query.filter_by(restaurante_id=restaurante_id, disponible=True).order_by(Plato.nombre).all()
    return render_template('carta/restaurante.html', restaurante=restaurante, platos=platos)


# ==============================================================================
# 2. CLIENTE: CREACIÓN Y GESTIÓN DE PEDIDOS (R1 y R2)
# ==============================================================================

@views_bp.route('/pedidos', methods=['POST'])
@requires_auth('create:pedidos')
def crear_pedido(payload):
    """
    R1.5 Pedido Atómico y R1.4 Total en Servidor:
    Crea un pedido con uno o más ítems congelando el precio del plato.
    Valida atomicidad: todo en una sola transacción con rollback si algo falla.
    """
    cliente_sub = payload.get('sub')
    if not cliente_sub:
        abort(400)

    try:
        restaurante_id = int(request.form.get('restaurante_id', 0))
    except (ValueError, TypeError):
        abort(400)

    restaurante = Restaurante.query.get(restaurante_id)
    if not restaurante:
        abort(404)

    # El formulario envía listas paralelas: plato_id[] y cantidad[]
    plato_ids = request.form.getlist('plato_id')
    cantidades = request.form.getlist('cantidad')

    if not plato_ids or not cantidades or len(plato_ids) != len(cantidades):
        flash("Debes seleccionar al menos un plato válido.", "error")
        return redirect(url_for('views.detalle_restaurante', restaurante_id=restaurante_id))

    total_calculado = 0.0
    items_a_crear = []

    try:
        for p_id_str, cant_str in zip(plato_ids, cantidades):
            try:
                p_id = int(p_id_str)
                cant = int(cant_str)
            except (ValueError, TypeError):
                db.session.rollback()
                abort(400)

            # Si la cantidad enviada es 0, se ignora (el cliente no pidió este plato)
            if cant == 0:
                continue

            # R1.5: Validar cantidad entera entre 1 y 20
            if cant < 1 or cant > 20:
                db.session.rollback()
                flash("La cantidad por plato debe estar entre 1 y 20.", "error")
                return redirect(url_for('views.detalle_restaurante', restaurante_id=restaurante_id)), 400

            # R1.5: Validar que el plato exista, pertenezca al mismo restaurante y esté disponible
            plato = Plato.query.get(p_id)
            if not plato:
                db.session.rollback()
                abort(404)

            if plato.restaurante_id != restaurante_id or not plato.disponible:
                db.session.rollback()
                flash(f"El plato '{plato.nombre}' no está disponible o pertenece a otro restaurante.", "error")
                return redirect(url_for('views.detalle_restaurante', restaurante_id=restaurante_id)), 400

            # R1.3: Precio congelado: se copia del plato al momento de pedir
            precio_congelado = plato.precio
            subtotal = float(precio_congelado) * cant
            total_calculado += subtotal

            items_a_crear.append({
                'plato_id': plato.id,
                'cantidad': cant,
                'precio_unitario': precio_congelado
            })

        # Al menos un ítem debe haber sido seleccionado
        if not items_a_crear:
            flash("No seleccionaste ningún plato para el pedido.", "error")
            return redirect(url_for('views.detalle_restaurante', restaurante_id=restaurante_id))

        # Crear el pedido principal
        nuevo_pedido = Pedido(
            cliente=cliente_sub,
            restaurante_id=restaurante_id,
            estado='pendiente',
            total=total_calculado
        )
        db.session.add(nuevo_pedido)
        db.session.flush()  # Obtener el ID del pedido para las claves foráneas

        # Crear los ítems del pedido
        for item_data in items_a_crear:
            item = ItemPedido(
                pedido_id=nuevo_pedido.id,
                plato_id=item_data['plato_id'],
                cantidad=item_data['cantidad'],
                precio_unitario=item_data['precio_unitario']
            )
            db.session.add(item)

        # R1.5: Confirmación de la transacción atómica
        db.session.commit()
        flash(f"¡Pedido #{nuevo_pedido.id} creado con éxito!", "success")
        
        # Post/Redirect/Get
        return redirect(url_for('views.ver_pedido', pedido_id=nuevo_pedido.id))

    except Exception:
        db.session.rollback()
        abort(400)


@views_bp.route('/mis-pedidos', methods=['GET'])
@requires_auth('read:mis-pedidos')
def mis_pedidos(payload):
    """Muestra exclusivamente los pedidos del cliente autenticado."""
    cliente_sub = payload['sub']
    pedidos = Pedido.query.filter_by(cliente=cliente_sub).order_by(Pedido.fecha.desc()).all()
    return render_template('pedidos/mis_pedidos.html', pedidos=pedidos)


@views_bp.route('/pedidos/<int:pedido_id>', methods=['GET'])
@requires_auth('read:mis-pedidos')
def ver_pedido(payload, pedido_id):
    """
    R2.6: Nadie ve pedidos ajenos.
    Si el pedido no existe o pertenece a otro cliente, responde 404 (no 403).
    """
    pedido = Pedido.query.get(pedido_id)
    cliente_sub = payload['sub']

    # Si no existe o es de otro cliente: 404 estricto
    if not pedido or pedido.cliente != cliente_sub:
        abort(404)

    return render_template('pedidos/detalle.html', pedido=pedido)


@views_bp.route('/pedidos/<int:pedido_id>/cancelar', methods=['POST'])
@requires_auth('read:mis-pedidos')
def cancelar_pedido(payload, pedido_id):
    """
    Cancela un pedido si el cliente es el dueño y sigue en estado 'pendiente'.
    """
    pedido = Pedido.query.get(pedido_id)
    cliente_sub = payload['sub']

    # R2.6: Seguridad contra enumeración de IDs
    if not pedido or pedido.cliente != cliente_sub:
        abort(404)

    # Transición cliente: solo desde 'pendiente' a 'cancelado'
    if pedido.estado != 'pendiente':
        flash("No se puede cancelar un pedido que ya está en preparación o finalizado.", "error")
        return redirect(url_for('views.ver_pedido', pedido_id=pedido.id)), 400

    pedido.estado = 'cancelado'
    db.session.commit()
    flash(f"El pedido #{pedido.id} ha sido cancelado.", "info")
    return redirect(url_for('views.ver_pedido', pedido_id=pedido.id))


# ==============================================================================
# 3. COCINA: COLA Y TRANSICIONES DE ESTADO (R1 y R2)
# ==============================================================================

@views_bp.route('/cocina', methods=['GET'])
@requires_auth('read:pedidos')
def vista_cocina(payload):
    """Muestra la cola de pedidos activos para preparar."""
    pedidos_activos = Pedido.query.filter(
        Pedido.estado.in_(['pendiente', 'en_preparacion', 'listo'])
    ).order_by(Pedido.fecha.asc()).all()
    return render_template('cocina/cola.html', pedidos=pedidos_activos)


@views_bp.route('/cocina/pedidos/<int:pedido_id>/avanzar', methods=['POST'])
@requires_auth('update:pedidos')
def avanzar_pedido_cocina(payload, pedido_id):
    """
    Avanza el estado del pedido según la máquina de estados estricta:
    pendiente → en_preparacion → listo → entregado.
    """
    pedido = Pedido.query.get(pedido_id)
    if not pedido:
        abort(404)

    siguiente_estado = TRANSICIONES_COCINA.get(pedido.estado)
    if not siguiente_estado:
        flash(f"No se puede avanzar el pedido #{pedido.id} desde el estado '{pedido.estado}'.", "error")
        return redirect(url_for('views.vista_cocina')), 400

    pedido.estado = siguiente_estado
    db.session.commit()
    flash(f"Pedido #{pedido.id} avanzado a '{siguiente_estado}'.", "success")
    return redirect(url_for('views.vista_cocina'))
