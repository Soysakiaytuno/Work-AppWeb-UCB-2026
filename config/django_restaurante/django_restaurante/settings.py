import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = 'django-insecure-restaurante-web-ucb-2026-key'

# R5.4: DEBUG desactivado por defecto en producción
DEBUG = os.environ.get('DJANGO_DEBUG', 'False').lower() in ('1', 'true', 'yes')

# R5.4: ALLOWED_HOSTS configurados para los subdominios y localhost
allowed_env = os.environ.get('DJANGO_ALLOWED_HOSTS', '')
if allowed_env:
    ALLOWED_HOSTS = [h.strip() for h in allowed_env.split(',') if h.strip()]
else:
    ALLOWED_HOSTS = ['localhost', '127.0.0.1', 'admin.localhost', 'web_django', '*']

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'restaurante',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'django_restaurante.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'restaurante' / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'django_restaurante.wsgi.application'

# Configuración de Base de Datos PostgreSQL con esquema content
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.environ.get('POSTGRES_DB', 'restaurant_database'),
        'USER': os.environ.get('POSTGRES_USER', 'app'),
        'PASSWORD': os.environ.get('POSTGRES_PASSWORD', '123qwe'),
        'HOST': os.environ.get('POSTGRES_HOST', 'localhost'),
        'PORT': os.environ.get('POSTGRES_PORT', '5432'),
    }
}

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'America/La_Paz'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
# R5.5: Carpeta de destino donde collectstatic recolecta los estáticos para que NGINX los sirva desde disco
STATIC_ROOT = BASE_DIR / 'staticfiles'

rest_static = BASE_DIR.parent / 'restaurante' / 'static'
STATICFILES_DIRS = [rest_static] if rest_static.exists() else []

# R5.4 y 4.C: Informa a Django que confíe en la cabecera X-Forwarded-Proto enviada por NGINX para detectar HTTPS
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# R5.4 y 4.C: Orígenes confiables para CSRF detrás de proxy
csrf_origins_env = os.environ.get('DJANGO_CSRF_ORIGINS', '')
CSRF_TRUSTED_ORIGINS = [
    'http://localhost',
    'http://127.0.0.1',
    'http://localhost:80',
    'http://127.0.0.1:80',
    'http://admin.localhost',
    'http://admin.localhost:80',
    'https://admin.localhost',
    'http://admin.mijael.mooo.com',
    'https://admin.mijael.mooo.com',
]
if csrf_origins_env:
    for origin in csrf_origins_env.split(','):
        if origin.strip():
            CSRF_TRUSTED_ORIGINS.append(origin.strip())
