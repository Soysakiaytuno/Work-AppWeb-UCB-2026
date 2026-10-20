from urllib.parse import urlencode
from authlib.integrations.base_client.errors import OAuthError
from flask import Blueprint, current_app, flash, redirect, request, session, url_for
from .oauth import auth0

auth_bp = Blueprint("auth", __name__, url_prefix="/auth")


def safe_next(target):
    """Evita ataques de Open Redirect verificando que la URL sea relativa al sitio."""
    if target and target.startswith("/") and not target.startswith("//") and "\\" not in target:
        return target
    return url_for("views.pagina_inicio")


@auth_bp.route("/login")
def login():
    """Redirige al navegador a la página de inicio de sesión de Auth0."""
    session["next"] = safe_next(request.args.get("next"))
    redirect_uri = url_for("auth.callback", _external=True)
    audience = current_app.config.get("AUTH0_AUDIENCE")
    
    return auth0().authorize_redirect(
        redirect_uri=redirect_uri,
        audience=audience,
    )


@auth_bp.route("/callback")
def callback():
    """Auth0 devuelve el código de un solo uso aquí; Authlib lo canjea por tokens."""
    try:
        token = auth0().authorize_access_token()
    except OAuthError as err:
        current_app.logger.error(f"Fallo en callback de Auth0: {err.description or err.error}")
        flash("No se pudo completar el inicio de sesión. Por favor, verifica la autorización de la app en Auth0.", "error")
        return redirect(url_for("views.pagina_inicio"))

    next_url = session.pop("next", None) or url_for("views.pagina_inicio")
    profile = token.get("userinfo") or {}
    
    # Inicia una nueva sesión limpia
    session.clear()
    session["access_token"] = token["access_token"]
    session["user"] = {
        "name": profile.get("name") or profile.get("nickname") or profile.get("email"),
        "email": profile.get("email"),
        "sub": profile.get("sub"),
    }
    flash("Has iniciado sesión correctamente.", "success")
    return redirect(next_url)


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    """Limpia la sesión de Flask y cierra la sesión en el servidor de Auth0."""
    session.clear()
    domain = current_app.config.get("AUTH0_DOMAIN")
    client_id = current_app.config.get("AUTH0_CLIENT_ID")
    return_to = url_for("views.pagina_inicio", _external=True)
    
    params = {
        "returnTo": return_to,
        "client_id": client_id,
    }
    flash("Has cerrado sesión.", "info")
    return redirect(f"https://{domain}/v2/logout?{urlencode(params)}")
