# 🍽️ La Carta 2.0 — Plataforma Multi-Restaurante y Gestión de Pedidos

Plataforma web distribuida para pedidos en línea, atención de cocina y administración centralizada, construida con **Flask**, **Django Backoffice**, **PostgreSQL 16**, autenticación RBAC mediante **Auth0**, orquestación en **Docker Compose** y reverse proxy **NGINX** con HTTPS.

Trabajo Práctico Integrador — **ISW-233 Aplicaciones Web I**  
Universidad Católica Boliviana "San Pablo" — Sede Santa Cruz

---

## 🌐 1. URLs del Proyecto

* **Web Pública y Portal de Pedidos (Flask):** [https://carta.mijael.mooo.com](https://carta.mijael.mooo.com)  
  *(En desarrollo local: `http://carta.localhost` o `http://localhost`)*
* **Portal de Cocina (Cola de preparación):** [https://carta.mijael.mooo.com/cocina](https://carta.mijael.mooo.com/cocina)
* **Backoffice Administrativo (Django Admin):** [https://admin.mijael.mooo.com](https://admin.mijael.mooo.com)  
  *(En desarrollo local: `http://admin.localhost`)*

---

## 🏗️ 2. Arquitectura del Sistema

```
                       [ Cliente / Cocina / Admin ]
                                    │
                                    │ HTTPS (Puerto 443) / HTTP (80 redirige a 443)
                                    ▼
       ┌──────────────────────────────────────────────────────────────┐
       │                   NGINX (Reverse Proxy)                      │
       │                   Contenedor: restaurante_nginx              │
       │                   Puertos públicos host: 80, 443             │
       └──────────────┬───────────────────────────────┬───────────────┘
                      │                               │
         Host: carta.<dominio>           Host: admin.<dominio>
         Proxy HTTP a :5000              Proxy HTTP a :8000
         (Cabeceras X-Forwarded-*)       (Cabeceras X-Forwarded-*)
                      │                               │
                      ▼                               ▼
       ┌──────────────────────────────┐┌──────────────────────────────┐
       │     Flask App + Gunicorn     ││    Django Admin + Gunicorn   │
       │  Contenedor: restaurante_flask││ Contenedor: restaurante_django│
       │  (Sin puertos expuestos)     ││ (Sin puertos expuestos)      │
       │  - Catálogo público          ││ - TabularInline de ítems     │
       │  - Transacción atómica       ││ - readonly_fields            │
       │  - ProxyFix (HTTPS callback) ││ - SECURE_PROXY_SSL_HEADER    │
       └──────────────┬───────────────┘└──────────────┬───────────────┘
                      │                               │
                      │         Red Interna           │
                      │      (Docker Bridge)          │
                      │                               │
                      ▼                               ▼
       ┌──────────────────────────────────────────────────────────────┐
       │                 PostgreSQL 16 Database                       │
       │                 Contenedor: restaurante_db                   │
       │                 (100% interna, sin ports expuestos)          │
       │                 - Esquema único gestionado por Django        │
       │                 - CheckConstraints de integridad física      │
       │                 - Volumen persistente: postgres_data         │
       └──────────────────────────────▲───────────────────────────────┘
                                      │
                         Ejecuta migraciones al boot
                                      │
                       ┌──────────────┴──────────────┐
                       │     Servicio migrate        │
                       │ Contenedor: restaurante_migrate│
                       │ (One-shot, condition:       │
                       │  service_completed_successfully)
                       │ - python manage.py migrate  │
                       │ - python manage.py initadmin│
                       │ - collectstatic a volumen   │
                       └─────────────────────────────┘
```

### Volúmenes Compartidos
* `postgres_data`: Almacenamiento persistente de PostgreSQL 16 (inmune a `docker compose down`).
* `django_static`: Archivos estáticos recopilados por `collectstatic` en `migrate` y servidos directamente por Nginx desde disco (`/var/www/django_static/`).
* `certbot_conf` y `certbot_www`: Certificados SSL generados por Let's Encrypt y desafíos ACME.

---

## 🚀 3. Guía de Despliegue Paso a Paso (Desde Cero)

### Prerrequisitos
* Servidor Linux (Ubuntu 22.04 LTS en AWS EC2 recomendado).
* Docker Engine 24+ y Docker Compose v2 instalados.
* Puertos `80` (HTTP), `443` (HTTPS) y `22` (SSH) habilitados en el Security Group de AWS.

### Paso 1: Clonar el repositorio
```bash
git clone https://github.com/Soysakiaytuno/Work-AppWeb-UCB-2026.git
cd Work-AppWeb-UCB-2026
```

### Paso 2: Configurar las Variables de Entorno
Copia la plantilla y edita con tus credenciales reales:
```bash
cp .env.example .env
nano .env
```
Completa las variables de Auth0, contraseñas de PostgreSQL y dominios.

### Paso 3: Configurar los Subdominios en FreeDNS / DNS
Crea dos registros tipo **A** apuntando a la IP pública de tu instancia EC2:
* `carta.<tu-dominio>`  ──> `IP_PUBLICA_EC2`
* `admin.<tu-dominio>`  ──> `IP_PUBLICA_EC2`

### Paso 4: Levantar la Arquitectura con Docker Compose
```bash
docker compose up -d --build
```
El servicio `migrate` creará las tablas, creará el superusuario y compilará los estáticos. Luego arrancarán Flask, Django y NGINX automáticamente.

### Paso 5: Emitir Certificados SSL con Certbot
Ejecuta Certbot en contenedor usando el desafío webroot ya configurado en NGINX:
```bash
docker compose run --rm certbot certonly --webroot -w /var/www/certbot \
  -d carta.<tu-dominio> -d admin.<tu-dominio> \
  --email tu-correo@ejemplo.com --agree-tos --no-eff-email
```

### Paso 6: Activar HTTPS y Recargar NGINX
Copia o enlaza la configuración de producción con SSL y recarga:
```bash
cp nginx/nginx.prod.conf nginx/nginx.conf
# Ajusta el nombre de tu dominio en nginx/nginx.conf si es necesario
docker compose exec nginx nginx -s reload
```

### Paso 7: Ejecutar las Pruebas Automatizadas
Verifica la suite de 6 pruebas obligatorias:
```bash
docker exec -w /app restaurante_flask pytest -q
```

---

## 🧠 4. Decisiones de Diseño Justificadas

### 1. Mapeo de modelos Flask y Django como único dueño del esquema
* **Decisión:** Django gestiona el ciclo de vida completo del esquema mediante `migrations` y `models.Model` con `CheckConstraint`. Flask mapea sus modelos con SQLAlchemy utilizando `__tablename__ = 'restaurante_pedido'`, etc.
* **Justificación:** Tener dos frameworks ejecutando migraciones sobre la misma base de datos provocaría inconsistencias de esquema y bloqueos de tablas (*race conditions*). Django actúa como la única fuente de verdad (*Single Source of Truth*), mientras Flask consume las tablas garantizando que `migrate` termine antes de que Flask inicie (`condition: service_completed_successfully`).

### 2. Por qué el pedido de otro cliente responde 404 y no 403
* **Decisión:** Cuando un cliente autenticado intenta consultar `/pedidos/<id>` de un pedido que pertenece a otro usuario, el servidor responde con **404 Not Found**.
* **Justificación:** Un código 403 Forbidden confirmaría la existencia de ese pedido, permitiendo ataques de enumeración de recursos (*ID Harvesting / Insecure Direct Object References - IDOR*). El código 404 oculta completamente la existencia del recurso ante ojos no autorizados.

### 3. Ubicación exacta de las reglas de negocio y máquina de estados
* **Validación de restaurante único y platos disponibles:** En `config/restaurante/app/routes.py`, función `crear_pedido()`, líneas 110-155.
* **Cálculo del total en servidor y congelación de precio:** En `routes.py`, `crear_pedido()`, donde `item.precio_unitario = plato.precio` y `total = sum(cant * precio)`.
* **Transacción atómica con rollback:** En `routes.py`, bloque `try ... except ... db.session.rollback()`.
* **Máquina de estados estricta:** En `routes.py`, función `cambiar_estado_pedido()`, donde se valida que solo la cocina pueda realizar `pendiente -> en_preparacion -> listo -> entregado` y el cliente únicamente `pendiente -> cancelado`.

### 4. Gestión de Secretos y Control de Acceso
* **Decisión:** Los secretos residen exclusivamente en el archivo `.env` del servidor, ignorado en `.gitignore` e inyectado mediante variables de entorno a los contenedores en `docker-compose.yml`.
* **Justificación:** Previene fugas accidentales en el historial de Git (evitando la penalización de -6 pts). Solo el usuario con acceso SSH al servidor host o el runtime de Docker en memoria pueden leer las credenciales.

---

## 🔍 5. Autocrítica y Trabajo Futuro

1. **Notificaciones en Tiempo Real:** Actualmente la cocina debe recargar la página para ver pedidos nuevos. Una mejora ideal sería incorporar WebSockets (Flask-SocketIO o SSE) para actualizar la cola en vivo.
2. **Concurrencia en Cocina:** Si dos cocineros hacen clic en "Avanzar pedido" exactamente al mismo milisegundo, la base de datos podría procesar ambos. Se podría implementar un bloqueo optimista o `SELECT FOR UPDATE` en PostgreSQL para mitigar condiciones de carrera concurrentes.
3. **Manejo de Stock:** No existe control de inventario de platos por restaurante; se asume disponibilidad binaria (`disponible = True/False`).
* **Usuarios de Prueba:**
  * Cliente: `cliente@test.com` / `ClientedelaCarta123!`
  * Cocina: `cocina@test.com` / `CocinadelaCarta123!`
  * Admin: `admin@test.com` / `AdmindelaCarta123!`
  * Superusuario Django: `admin` / `admin123`