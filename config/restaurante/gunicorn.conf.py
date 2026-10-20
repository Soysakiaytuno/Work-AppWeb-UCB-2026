import multiprocessing
import os

bind = "0.0.0.0:5000"

# Fórmula recomendada de trabajadores: (2 x núcleos de CPU) + 1
workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"
threads = int(os.environ.get("GUNICORN_THREADS", 1))

timeout = int(os.environ.get("GUNICORN_TIMEOUT", 30))
graceful_timeout = 30
keepalive = 5

# Reciclaje defensivo contra fugas de memoria
max_requests = 1000
max_requests_jitter = 100

# Logs hacia stdout/stderr para captura de Docker
accesslog = "-"
errorlog = "-"

# Confía en las cabeceras de proxy de NGINX en red interna
forwarded_allow_ips = "*"
