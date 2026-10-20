from django.http import JsonResponse
from .models import Restaurante, Plato, Pedido


def salud(request):
    """GET /api/salud → Comprobación de salud y estado de la base de datos."""
    return JsonResponse({
        'status': 'ok',
        'restaurantes': Restaurante.objects.count(),
        'platos': Plato.objects.count(),
        'pedidos': Pedido.objects.count(),
        'framework': 'django',
    })
