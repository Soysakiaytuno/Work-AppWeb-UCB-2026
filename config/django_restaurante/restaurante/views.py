from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse, Http404
from .models import Usuario, Mesa, Producto, Recibo

# --- Vistas HTML ---

def vista_usuarios(request):
    """GET / o /usuarios → vista HTML de usuarios en Django."""
    usuarios = Usuario.objects.order_by('nombre')
    return render(request, 'usuarios/usuarios.html', {'listaUsuarios': usuarios})


def vista_mesas(request):
    """GET /mesas → vista HTML de mesas en Django."""
    mesas = Mesa.objects.order_by('numero')
    return render(request, 'mesas/mesas.html', {'listaMesas': mesas})


def vista_productos(request):
    """GET /productos → vista HTML de productos en Django."""
    productos = Producto.objects.order_by('nombre')
    return render(request, 'productos/productos.html', {'listaProductos': productos})


def vista_recibos(request):
    """GET /recibos → vista HTML de recibos (50 más recientes) en Django."""
    recibos = Recibo.objects.order_by('-creation_date')[:50]
    return render(request, 'recibos/recibos.html', {'listaRecibos': recibos})


# --- Endpoints API JSON ---

def listar_personas(request):
    """GET /personas → listado de personas en JSON con soporte de filtro ?nombre=..."""
    consulta = Usuario.objects.all()
    nombre = request.GET.get('nombre')
    if nombre:
        consulta = consulta.filter(nombre__icontains=nombre)

    personas = consulta.order_by('nombre')
    return JsonResponse({
        'success': True,
        'total': personas.count(),
        'personas': [p.format() for p in personas]
    })


def obtener_persona(request, person_id):
    """GET /personas/<person_id> → una sola persona en JSON."""
    try:
        persona = Usuario.objects.get(id=person_id)
        return JsonResponse({'success': True, 'persona': persona.format()})
    except (Usuario.DoesNotExist, Exception):
        return JsonResponse({'success': False, 'error': 404, 'mensaje': 'recurso no encontrado'}, status=404)


def salud(request):
    """GET /salud → comprobación rápida de conexión a la base de datos."""
    total = Usuario.objects.count()
    return JsonResponse({
        'status': 'ok',
        'personas_registradas': total,
        'framework': 'django',
        'live_reload': 'success'
    })
