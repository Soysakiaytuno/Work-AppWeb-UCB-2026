import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-cambiar-en-produccion")
    
    _db_url = os.environ.get(
        "DATABASE_URL",
        "postgresql://app:123qwe@localhost:5432/restaurant_database"
    )
    if _db_url and _db_url.startswith("postgresql://"):
        _db_url = _db_url.replace("postgresql://", "postgresql+psycopg2://", 1)
    SQLALCHEMY_DATABASE_URI = _db_url
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Salud del Pool: reconecta si la BD estuvo inactiva
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 300,
    }
    
    # Cookie de sesión segura para Auth0
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "0") == "1"
    
    # Configuración Auth0
    AUTH0_DOMAIN = os.environ.get("AUTH0_DOMAIN", "")
    AUTH0_AUDIENCE = os.environ.get("API_AUDIENCE", os.environ.get("AUTH0_AUDIENCE", ""))
    AUTH0_CLIENT_ID = os.environ.get("AUTH0_CLIENT_ID", "")
    AUTH0_CLIENT_SECRET = os.environ.get("AUTH0_CLIENT_SECRET", "")
    ALGORITHMS = ["RS256"]
    
    # ¿Estamos detrás de NGINX?
    BEHIND_PROXY = os.environ.get("BEHIND_PROXY", "0") == "1"
