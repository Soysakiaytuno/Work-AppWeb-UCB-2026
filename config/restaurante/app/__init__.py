from flask import Flask, render_template, request, jsonify, redirect, url_for
from werkzeug.middleware.proxy_fix import ProxyFix
from .config import Config
from .extensions import db
from .auth import init_auth0, AuthError, current_user


def create_app(config_class=Config):
    """
    Application Factory:
    Crea, configura y ensambla la instancia de la aplicación Flask.
    """
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Si estamos detrás de NGINX en producción, confiamos en cabeceras X-Forwarded-*
    # R5.3: Flask usa ProxyFix para que la URL de callback de Auth0 salga con https://
    if app.config.get("BEHIND_PROXY"):
        app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)

    # Conectar base de datos SQLAlchemy (sin migraciones en Flask: Django es el dueño)
    db.init_app(app)

    # Inicializar cliente Authlib para Auth0
    init_auth0(app)

    # Inyectar el usuario actual y sus permisos en todas las plantillas Jinja (R2.7)
    @app.context_processor
    def inject_context():
        return {
            'user': current_user()
        }

    # Registrar los Blueprints
    from .routes import views_bp
    from .api import api_bp
    from .auth import auth_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(auth_bp)

    # ==============================================================================
    # MANEJADORES DE ERRORES (R2.5)
    # ==============================================================================

    @app.errorhandler(AuthError)
    def handle_auth_error(ex):
        """
        401: Si no hay sesión, redirige al login de Auth0.
        403: Si no tiene el permiso requerido, muestra página 403 con mensaje claro.
        """
        # Si la petición es JSON (ej. API o test con Accept: application/json)
        if request.path.startswith('/api') or request.headers.get('Accept') == 'application/json':
            return jsonify({
                'success': False,
                'error': ex.status_code,
                'code': ex.error.get('code', 'auth_error'),
                'message': ex.error.get('description', 'Error de autenticación')
            }), ex.status_code

        if ex.status_code == 401:
            # Redirige al login de Auth0 guardando la URL a la que intentaba ir
            return redirect(url_for('auth.login', next=request.path))

        return render_template(
            'auth/forbidden.html',
            code=ex.status_code,
            error_code=ex.error.get('code', 'forbidden'),
            message=ex.error.get('description', 'No tienes permisos para realizar esta acción.')
        ), ex.status_code

    @app.errorhandler(404)
    def no_encontrado(error):
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'error': 404, 'mensaje': 'Recurso no encontrado'}), 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(400)
    def solicitud_invalida(error):
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'error': 400, 'mensaje': 'Solicitud inválida'}), 400
        return render_template('errors/400.html'), 400

    @app.errorhandler(500)
    def error_servidor(error):
        if request.path.startswith('/api'):
            return jsonify({'success': False, 'error': 500, 'mensaje': 'Error interno del servidor'}), 500
        return render_template('errors/500.html'), 500

    return app
