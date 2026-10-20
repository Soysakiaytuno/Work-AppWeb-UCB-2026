from authlib.integrations.flask_client import OAuth
from flask import current_app


def init_auth0(app):
    """
    Registra Auth0 como proveedor OpenID Connect para esta app Flask.
    Authlib consulta server_metadata_url para descubrir las rutas de authorize,
    token y JWKS automáticamente.
    """
    oauth = OAuth(app)
    domain = app.config.get("AUTH0_DOMAIN")
    if domain:
        oauth.register(
            "auth0",
            client_id=app.config.get("AUTH0_CLIENT_ID"),
            client_secret=app.config.get("AUTH0_CLIENT_SECRET"),
            client_kwargs={
                "scope": "openid profile email",
            },
            server_metadata_url=f"https://{domain}/.well-known/openid-configuration",
        )
    return oauth


def auth0():
    """Retorna el cliente registrado de Auth0 en la aplicación actual."""
    return current_app.extensions["authlib.integrations.flask_client"].auth0
