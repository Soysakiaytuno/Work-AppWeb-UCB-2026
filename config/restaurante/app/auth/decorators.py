from functools import wraps
from flask import session
from .errors import AuthError
from .tokens import get_token_from_session, verify_decode_jwt


def check_permissions(permission, payload):
    """
    Verifica que el payload contenga la lista de permisos (RBAC)
    y que el permiso exigido por la ruta esté presente.
    """
    if "permissions" not in payload:
        raise AuthError({
            "code": "invalid_claims",
            "description": "El token no contiene permisos RBAC."
        }, 400)

    if permission and permission not in payload.get("permissions", []):
        raise AuthError({
            "code": "forbidden",
            "description": f"Acceso denegado: falta el permiso '{permission}'."
        }, 403)

    return True


def requires_auth(permission=""):
    """
    Decorador para proteger rutas con Auth0 (flujo de plantillas Flask).
    1. Obtiene el token de la sesión (cookie firmada).
    2. Valida la firma RS256 contra el JWKS de Auth0.
    3. Valida el permiso requerido en el array 'permissions'.
    """
    def requires_auth_decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            token = get_token_from_session()
            payload = verify_decode_jwt(token)
            check_permissions(permission, payload)
            return f(payload, *args, **kwargs)
        return wrapper
    return requires_auth_decorator


def current_user():
    """
    Helper para inyectar en las plantillas Jinja:
    Devuelve los datos del usuario y sus permisos, o None si no hay sesión.
    """
    token = session.get("access_token")
    if not token:
        return None
    try:
        payload = verify_decode_jwt(token)
        user_info = session.get("user", {})
        return {
            "name": user_info.get("name", "Usuario"),
            "email": user_info.get("email", ""),
            "sub": payload.get("sub"),
            "permissions": payload.get("permissions", []),
            "has_permission": lambda perm: perm in payload.get("permissions", []),
        }
    except Exception:
        return None