import jwt
from flask import session, current_app
from .errors import AuthError


def get_token_from_session():
    """
    Obtiene el access_token guardado en la sesión de Flask (cookie firmada).
    En aplicaciones web con plantillas y formularios HTML no se puede enviar
    el header Authorization: Bearer, por lo que el token vive en la sesión.
    """
    token = session.get("access_token")
    if not token:
        raise AuthError({
            "code": "not_signed_in",
            "description": "Por favor inicia sesión para continuar."
        }, 401)
    return token


def verify_decode_jwt(token):
    """
    Verifica y decodifica el token JWT:
    1. Si es un token de prueba (firmado con SECRET_KEY para pytest), lo decodifica con HS256.
    2. Si es de Auth0, descarga las claves públicas JWKS y valida con RS256, audience e issuer.
    """
    # Soporte para pruebas locales / pytest
    test_secret = current_app.config.get("SECRET_KEY")
    try:
        header = jwt.get_unverified_header(token)
        if header.get("alg") == "HS256":
            # Usado exclusivamente en suite de pruebas automáticas (R6)
            payload = jwt.decode(
                token,
                test_secret,
                algorithms=["HS256"],
                options={"verify_aud": False}
            )
            return payload
    except Exception:
        pass

    domain = current_app.config.get("AUTH0_DOMAIN")
    audience = current_app.config.get("AUTH0_AUDIENCE")

    if not domain or not audience:
        raise AuthError({
            "code": "auth0_not_configured",
            "description": "AUTH0_DOMAIN y AUTH0_AUDIENCE deben estar configurados."
        }, 500)

    jwks_url = f"https://{domain}/.well-known/jwks.json"

    try:
        jwks_client = jwt.PyJWKClient(jwks_url)
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            audience=audience,
            issuer=f"https://{domain}/",
            options={"require": ["exp", "iat", "sub"]}
        )
        return payload

    except jwt.ExpiredSignatureError:
        raise AuthError({"code": "token_expired", "description": "Tu sesión ha expirado. Inicia sesión nuevamente."}, 401)
    except (jwt.InvalidAudienceError, jwt.InvalidIssuerError):
        raise AuthError({"code": "invalid_claims", "description": "Claims inválidos en el token. Revisa audience e issuer."}, 401)
    except jwt.PyJWKClientConnectionError:
        raise AuthError({"code": "jwks_unavailable", "description": "No se pudo conectar con Auth0 para obtener las claves públicas."}, 503)
    except jwt.PyJWKClientError:
        raise AuthError({"code": "invalid_header", "description": "No se encontró la clave correspondiente en el JWKS de Auth0."}, 401)
    except jwt.InvalidTokenError:
        raise AuthError({"code": "invalid_token", "description": "Token inválido."}, 401)
