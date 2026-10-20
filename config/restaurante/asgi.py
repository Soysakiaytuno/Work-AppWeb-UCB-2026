from asgiref.wsgi import WsgiToAsgi
from app import create_app

# 1. Creamos la aplicación Flask estándar (WSGI)
wsgi_app = create_app()

# 2. La adaptamos a interfaz ASGI para que Uvicorn pueda servirla
asgi_app = WsgiToAsgi(wsgi_app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("asgi:asgi_app", host="0.0.0.0", port=5000, reload=True)
