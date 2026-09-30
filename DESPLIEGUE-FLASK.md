# Despliegue de una aplicación Flask a producción

Guía completa para llevar la aplicación Flask de este repositorio desde un
entorno local hasta un servidor remoto en producción, con dominio propio y
certificado HTTPS.

La guía cubre **Flask + Gunicorn + PostgreSQL**, desde el servidor recién
creado hasta la aplicación publicada con dominio y certificado.

**Cada tema se presenta dos veces:**

1. **Sin Docker**, instalando todo directamente en el servidor. Es la ruta
   que enseña qué hace cada pieza.
2. **Con Docker**, donde todo va en contenedores. Es la ruta que se usa en
   proyectos reales porque es reproducible.

---

## Contenido

1. [Panorama general](#1-panorama-general)
2. [El servidor remoto en AWS](#2-el-servidor-remoto-en-aws)
3. [Preparar el servidor sin Docker](#3-preparar-el-servidor-sin-docker)
4. [Gunicorn: el servidor WSGI](#4-gunicorn-el-servidor-wsgi)
5. [systemd: mantener la aplicación viva](#5-systemd-mantener-la-aplicación-viva)
6. [Nombre de dominio](#6-nombre-de-dominio)
7. [Web servers: por qué necesitamos NGINX](#7-web-servers-por-qué-necesitamos-nginx)
8. [NGINX sin Docker](#8-nginx-sin-docker)
9. [HTTPS con Certbot sin Docker](#9-https-con-certbot-sin-docker)
10. [CORS](#10-cors)
11. [Frontend y backend en el mismo dominio](#11-frontend-y-backend-en-el-mismo-dominio)
12. [Ahora con Docker: NGINX en contenedor](#12-ahora-con-docker-nginx-en-contenedor)
13. [HTTPS con Docker](#13-https-con-docker)
14. [Actualizar el código en producción](#14-actualizar-el-código-en-producción)
15. [Comparación: con Docker vs sin Docker](#15-comparación-con-docker-vs-sin-docker)
16. [Checklist final](#16-checklist-final)

---

## 1. Panorama general

### El problema que resolvemos

En local ejecutamos la aplicación así:

```bash
flask run --debug
```

Eso arranca el **servidor de desarrollo de Flask**, que es de un solo hilo,
no tiene límites de petición, y su propia documentación dice explícitamente
que no se use en producción. Además solo escucha en `localhost`, nadie más
puede entrar, no tiene dominio ni cifrado.

En producción necesitamos cuatro piezas:

| Pieza | Qué resuelve |
|---|---|
| Un **servidor remoto** | Que la app esté encendida 24/7 con IP pública |
| Un **servidor WSGI** (Gunicorn) | Ejecutar Python con varios procesos en paralelo |
| Un **servidor HTTP** (NGINX) | Puerto 80/443, archivos estáticos, TLS, proxy inverso |
| Un **gestor de procesos** | Que la app reviva si se cae o si el servidor reinicia |

### Arquitectura final

```
                    Internet
                       │
                       ▼
        ┌──────────────────────────────┐
        │  NGINX  :80 / :443           │  ← TLS, estáticos, proxy inverso
        └──────────────┬───────────────┘
                       │  proxy_pass
                       ▼
        ┌──────────────────────────────┐
        │  Gunicorn  :8000             │  ← servidor WSGI, N workers
        │    ├─ worker 1 → Flask       │
        │    ├─ worker 2 → Flask       │
        │    └─ worker 3 → Flask       │
        └──────────────┬───────────────┘
                       │
                       ▼
        ┌──────────────────────────────┐
        │  PostgreSQL  :5432           │  ← solo accesible internamente
        └──────────────────────────────┘
```

### Por qué Flask necesita un servidor aparte

Flask **no es un servidor**. Es una aplicación que habla el protocolo
**WSGI**, y necesita un servidor WSGI separado que la ejecute. Ese servidor
es Gunicorn.

Esa separación es deliberada: gracias a ella podrías cambiar Gunicorn por
uWSGI o Waitress sin tocar una sola línea de tu código Flask.

| Pieza | Qué es | Puerto |
|---|---|---|
| Flask | La aplicación, habla WSGI | — |
| Gunicorn | El servidor WSGI que la ejecuta | 8000 |
| NGINX | El servidor HTTP público | 80 y 443 |
| PostgreSQL | La base de datos | 5432, solo interno |

---

## 2. El servidor remoto en AWS

### Crear la instancia EC2

En AWS Academy Learner Lab, entra al laboratorio y abre la consola de AWS.
Busca el servicio **EC2** y haz clic en **Launch instance**.

Configuración:

- **Sistema operativo:** Ubuntu (recomendado 22.04 LTS o superior)
- **Tipo de instancia:** `t2.micro` o `t3.micro` (capa gratuita)
- **Key pair:** crea una nueva y **guarda el archivo `.pem`**. Es la llave
  con la que entrarás por SSH. Si la pierdes, pierdes el acceso.

### Abrir los puertos

En **Network settings**, habilita el tráfico entrante:

| Puerto | Protocolo | Para qué |
|---|---|---|
| 22 | SSH | Conectarte al servidor |
| 80 | HTTP | Tráfico web sin cifrar |
| 443 | HTTPS | Tráfico web cifrado |

Para abrir puertos adicionales después, ve a **Network & Security >
Security Groups**, selecciona el grupo de tu instancia y edita las
**inbound rules**. Por ejemplo, para exponer temporalmente el puerto 8000:

- Type: Custom TCP
- Port range: `8000`
- Source: `0.0.0.0/0` (cualquier IP)

> **Importante:** el puerto 8000 solo se abre para probar antes de instalar
> NGINX. Una vez que NGINX esté funcionando, **ciérralo**. Gunicorn no debe
> ser accesible desde internet directamente.

### Conectarse por SSH

En macOS y Linux, la llave debe tener permisos restringidos o SSH la rechaza:

```bash
chmod 400 ~/.ssh/mi-llave.pem
```

Luego conéctate:

```bash
ssh -i ~/.ssh/mi-llave.pem ubuntu@<ip-publica>
```

El usuario en Ubuntu de AWS es `ubuntu`. En otras distribuciones puede ser
`ec2-user` o `admin`.

---

## 3. Preparar el servidor sin Docker

Todos los comandos de esta sección se ejecutan **dentro del servidor**, por
SSH.

### Actualizar el sistema

```bash
sudo apt update && sudo apt upgrade -y
```

### Instalar Python y herramientas

Ubuntu trae Python 3, pero necesitamos el módulo de entornos virtuales y las
cabeceras de compilación para `psycopg2`:

```bash
sudo apt install -y python3 python3-pip python3-venv python3-dev build-essential libpq-dev git
```

Verifica la versión:

```bash
python3 --version
```

> **Regla importante:** la versión mayor de Python en el servidor debe
> coincidir con la de tu máquina local. Si desarrollaste en 3.12 y el
> servidor tiene 3.10, puedes encontrarte con incompatibilidades de sintaxis
> o de dependencias.

### Instalar PostgreSQL

```bash
sudo apt install -y postgresql postgresql-contrib
```

El servicio arranca automáticamente. Verifícalo:

```bash
sudo systemctl status postgresql
```

PostgreSQL ya queda habilitado para iniciar en cada arranque del servidor.

### Crear la base de datos y el usuario

> **Importante:** la base de datos que tienes en tu máquina local **no se
> copia** al servidor. Son dos instalaciones de PostgreSQL completamente
> separadas. En el servidor vas a crear una base **vacía**, y las
> migraciones se encargarán de crear las tablas.

Entra a la consola de PostgreSQL con el usuario `postgres` que crea la
instalación:

```bash
sudo -u postgres psql
```

Dentro de la consola (el prompt será `postgres=#`):

```sql
CREATE USER todo WITH PASSWORD 'una-password-fuerte-aqui';
CREATE DATABASE todoapp OWNER todo;
GRANT ALL PRIVILEGES ON DATABASE todoapp TO todo;
\q
```

`\q` sale de la consola.

Usa **el mismo nombre de base y de usuario** que en tu `.env` local, pero
con una **contraseña distinta y fuerte**. La contraseña de desarrollo no
debe viajar a producción.

Comprueba que la base existe y está vacía:

```bash
sudo -u postgres psql -d todoapp -c "\dt"
```

Debe responder `Did not find any relations`, porque todavía no hay tablas.
Eso es lo esperado: las creará `flask db upgrade` más adelante.

> **Seguridad:** por defecto PostgreSQL solo escucha en `localhost`, que es
> exactamente lo que queremos. **No** lo cambies a `listen_addresses = '*'`
> a menos que sepas lo que haces: expondría tu base de datos a internet.

### ¿Y si necesitas llevar datos de tu máquina al servidor?

Normalmente **no hace falta**: producción empieza vacía y los usuarios
generan sus propios datos. Pero si necesitas llevar datos de ejemplo, se
hace con un volcado:

```bash
# En tu máquina local: exportar
pg_dump -U todo todoapp > datos.sql

# Copiar al servidor
scp -i ~/.ssh/mi-llave.pem datos.sql ubuntu@<ip>:/home/ubuntu/

# En el servidor: importar
sudo -u postgres psql -d todoapp -f /home/ubuntu/datos.sql
```

Hazlo **después** de aplicar las migraciones, para que las tablas ya
existan.

### Clonar el proyecto

```bash
cd /home/ubuntu
git clone https://github.com/tu-usuario/todoapp.git
cd todoapp
```

Si el repositorio es privado, necesitarás añadir una llave SSH del servidor
a tu cuenta de GitHub, o usar un token de acceso personal.

### Crear el entorno virtual

Un entorno virtual aísla las dependencias del proyecto de las del sistema:

```bash
python3 -m venv venv
source venv/bin/activate
```

Cuando el entorno está activo, el prompt muestra `(venv)` al inicio.

Instala las dependencias:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### Configurar las variables de entorno

Crea el archivo `.env` en la raíz del proyecto:

```bash
nano .env
```

Con este contenido:

```bash
SECRET_KEY=pega-aqui-una-clave-aleatoria-larga
DATABASE_URL=postgresql://todo:una-password-fuerte-aqui@localhost:5432/todoapp
FLASK_APP=wsgi.py
FLASK_DEBUG=0
```

Genera la clave secreta con:

```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

Guarda con `Ctrl+O`, `Enter`, y sal con `Ctrl+X`.

Protege el archivo para que solo tu usuario pueda leerlo:

```bash
chmod 600 .env
```

> **Nunca subas `.env` a Git.** Debe estar en `.gitignore`. Una contraseña
> commiteada queda en el historial para siempre.

### Aplicar las migraciones

```bash
export FLASK_APP=wsgi.py
flask db upgrade
```

Esto crea la tabla `todos` en PostgreSQL. Verifícalo:

```bash
sudo -u postgres psql -d todoapp -c "\dt"
```

---

## 4. Gunicorn: el servidor WSGI

### Qué es WSGI y por qué lo necesitamos

**WSGI** (Web Server Gateway Interface) es el estándar que define cómo se
comunican un servidor web y una aplicación Python. Es el equivalente en
Python de lo que CGI y FastCGI fueron para las primeras aplicaciones web.

Flask implementa el lado de la **aplicación**. Gunicorn implementa el lado
del **servidor**. Gunicorn arranca varios procesos *worker*, y cada uno
ejecuta una copia de tu aplicación Flask.

Esa separación es lo que permite que cualquier servidor WSGI ejecute
cualquier framework WSGI: podrías cambiar Gunicorn por uWSGI o Waitress sin
tocar el código de Flask.

### Probar Gunicorn

Con el entorno virtual activo:

```bash
gunicorn --bind 0.0.0.0:8000 wsgi:app
```

`wsgi:app` significa: en el archivo `wsgi.py`, usa el objeto llamado `app`.

Abre en el navegador `http://<ip-publica>:8000` (recuerda que el puerto 8000
debe estar abierto en el Security Group para esta prueba).

Detén el proceso con `Ctrl+C`.

### El archivo de configuración

Este repositorio ya incluye `gunicorn.conf.py`:

```python
import multiprocessing
import os

bind = "0.0.0.0:8000"

workers = int(os.environ.get("GUNICORN_WORKERS", multiprocessing.cpu_count() * 2 + 1))
worker_class = "sync"

timeout = int(os.environ.get("GUNICORN_TIMEOUT", 30))
graceful_timeout = 30
keepalive = 5

max_requests = 1000
max_requests_jitter = 100

accesslog = "-"
errorlog = "-"
loglevel = os.environ.get("GUNICORN_LOG_LEVEL", "info")

forwarded_allow_ips = "*"
```

Los parámetros que importan:

**`workers`.** La fórmula `(2 × núcleos) + 1` es el punto de partida
recomendado. Cada worker es un **proceso independiente** con su propia
memoria y sus propias conexiones a la base de datos. Más workers no es
automáticamente mejor: consumen RAM y conexiones.

**`max_requests`.** Recicla cada worker después de unas 1000 peticiones. Es
una defensa pragmática contra fugas de memoria lentas: en vez de perseguir
una fuga durante días, el worker se reemplaza antes de que importe. El
`jitter` evita que todos se reinicien a la vez.

**`timeout`.** Mata un worker que lleve más de 30 segundos en una petición.
Protege contra peticiones colgadas.

**`forwarded_allow_ips`.** Le dice a Gunicorn que confíe en las cabeceras
`X-Forwarded-*`. Solo es seguro porque Gunicorn estará detrás de NGINX y no
accesible directamente.

Para producción, cambia el `bind` a `127.0.0.1:8000`, de modo que Gunicorn
**solo** acepte conexiones desde la propia máquina (o sea, desde NGINX).

---

## 5. systemd: mantener la aplicación viva

### El problema

Si ejecutas `gunicorn` en la terminal y cierras la sesión SSH, el proceso
muere y tu aplicación deja de responder. Además, si el proceso falla o el
servidor se reinicia, nadie lo vuelve a levantar.

La solución estándar es **systemd**, el gestor de servicios que ya viene
con Ubuntu. No hay que instalar nada.

### Crear el servicio

```bash
sudo nano /etc/systemd/system/todoapp.service
```

Contenido:

```ini
[Unit]
Description=Todo App Flask con Gunicorn
After=network.target postgresql.service
Requires=postgresql.service

[Service]
Type=notify
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/todoapp
EnvironmentFile=/home/ubuntu/todoapp/.env
ExecStart=/home/ubuntu/todoapp/venv/bin/gunicorn --config gunicorn.conf.py wsgi:app
ExecReload=/bin/kill -s HUP $MAINPID
Restart=always
RestartSec=5
KillMode=mixed
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

Qué significa cada parte:

- **`After` y `Requires`**: arranca después de que PostgreSQL esté listo.
- **`EnvironmentFile`**: carga el `.env`, así que Gunicorn ve `SECRET_KEY` y
  `DATABASE_URL` sin que estén en el archivo de servicio.
- **`ExecStart`**: usa el Gunicorn **del entorno virtual**, con ruta
  absoluta. systemd no sabe nada de entornos virtuales.
- **`Restart=always`**: si el proceso muere por cualquier motivo, systemd lo
  vuelve a levantar automáticamente.
- **`RestartSec=5`**: espera 5 segundos entre reintentos, para no entrar en
  un bucle de reinicios.

### Activar y arrancar

```bash
sudo systemctl daemon-reload
sudo systemctl enable todoapp
sudo systemctl start todoapp
```

`enable` hace que la aplicación arranque sola cuando el servidor se
reinicia.

### Comandos que usarás a diario

| Acción | Comando |
|---|---|
| Arrancar | `sudo systemctl start todoapp` |
| Reiniciar tras un cambio | `sudo systemctl restart todoapp` |
| Detener | `sudo systemctl stop todoapp` |
| Ver si está corriendo | `sudo systemctl status todoapp` |
| Ver los logs en vivo | `sudo journalctl -u todoapp -f` |
| Activar el arranque automático | `sudo systemctl enable todoapp` |

Verifica que está corriendo:

```bash
sudo systemctl status todoapp
```

Deberías ver `active (running)` en verde.

Para ver los logs en vivo:

```bash
sudo journalctl -u todoapp -f
```

---

## 6. Nombre de dominio

### Por qué

Ahora solo podemos entrar por IP, algo como `http://54.23.11.90:8000`. Nadie
memoriza eso, y además un certificado SSL **se emite para un nombre de
dominio**, no para una IP. Sin dominio no hay HTTPS.

### Registrar un subdominio gratis con FreeDNS

Los dominios normalmente se pagan. Para la clase usaremos
[FreeDNS](https://freedns.afraid.org/), que regala subdominios.

1. Crea una cuenta en **Sign up Free**.
2. Ve a la [página de Subdomains](https://freedns.afraid.org/subdomain/).
3. Añade un subdominio:
   - **Type:** `A`
   - **Subdomain:** el nombre que elijas, por ejemplo `todoapp-jose`
   - **Domain:** elige uno de la lista disponible
   - **Destination:** la **IP pública de tu servidor EC2**

> **Consejo:** evita los dominios más populares de la lista. Let's Encrypt
> tiene un límite de certificados por dominio base, y si eliges uno muy
> usado puede que ya se haya alcanzado ese límite y no puedas emitir tu
> certificado.

### Registra también la versión con `www`

Repite el proceso con el prefijo `www.`:

```
todoapp-jose.example.com        ← sin www
www.todoapp-jose.example.com    ← con www
```

Así la aplicación responde escriban lo que escriban los usuarios.

### Un subdominio para la API

Si el frontend y el backend van separados, conviene un tercer registro:

```
todoapp-jose.example.com        → frontend
api.todoapp-jose.example.com    → API backend
```

Los tres apuntan a la **misma IP**. NGINX decidirá qué servir según el
`Host` de cada petición.

### Verificar la propagación

El DNS tarda. Espera entre 10 y 15 minutos y comprueba:

```bash
ping todoapp-jose.example.com
dig +short todoapp-jose.example.com
```

Debe devolver la IP de tu servidor. Si no, espera un poco más.

Mientras NGINX no esté configurado, todavía tendrás que indicar el puerto:

```
http://todoapp-jose.example.com:8000
```

---

## 7. Web servers: por qué necesitamos NGINX

### Los tres tipos de servidor

**Servidores HTTP.** Son la capa intermedia entre el usuario y la aplicación.
Optimizan las peticiones, alivian la carga, enrutan según reglas y escalan a
todos los núcleos. Los más conocidos: **Apache** y **NGINX**.

**Servidores de aplicaciones.** Ejecutan las instancias de la aplicación y
las comunican con el servidor HTTP. En Python: **Gunicorn**, **uWSGI**.

**Servidores integrados.** El servidor de desarrollo de Flask o de Django.
Cómodos para depurar, lentos e inseguros para producción.

### El problema C10K

En los 2000 surgió el problema de atender **10.000 conexiones simultáneas**.
El hardware aguantaba, pero los servidores web eran el cuello de botella.

**Apache** maneja cada conexión en un proceso o hilo separado del sistema
operativo. Cada proceso consume memoria y cada hilo carga el procesador. En
los 90 no importaba: las webs pesaban menos de 1 MB y había 16 millones de
usuarios en internet. Hoy hay miles de millones.

En 2004, **Igor Sysoev** presentó **NGINX**, basado en un modelo de
**eventos** (*event loop*) en lugar de procesos. NGINX maneja miles de
conexiones sin desperdiciar recursos. Hoy el reto se llama C10M: diez
millones de conexiones.

### Las dos funciones de NGINX que usaremos

**1. Proxy inverso.** Recibe la petición, decide a dónde ir dentro de la red
privada a buscar el contenido, y devuelve la respuesta. Para el usuario
parece que todo lo atendió NGINX.

> Un proxy **normal** (directo) redirige peticiones del cliente hacia
> cualquier recurso de internet. Un proxy **inverso** está del lado del
> servidor: el cliente no sabe que detrás hay otra máquina.

**2. Servidor de archivos estáticos.** El HTML cambia en cada petición, pero
las imágenes, el CSS y el JS casi nunca cambian. Dejar que NGINX los sirva
directamente desde disco descarga completamente a la aplicación. Una
petición que Gunicorn nunca ve es una petición que no cuesta nada.

### El problema de los clientes lentos

Hay una razón menos obvia y muy importante. Los workers `sync` de Gunicorn
atienden **una petición a la vez**. Un cliente con mala conexión móvil que
envía el cuerpo de una petición lentamente ocupa un worker entero mientras
tanto. Con 3 workers, unos pocos clientes lentos bloquean toda la
aplicación.

NGINX lee la petición completa en un buffer y solo entonces se la pasa a
Gunicorn, de golpe. Así los workers solo están ocupados haciendo trabajo
real.

---

## 8. NGINX sin Docker

### El problema de los puertos

Por defecto, las peticiones web van al puerto **80**. Nuestra aplicación
corre en el **8000**. Podríamos cambiar Gunicorn al puerto 80, pero:

```bash
# NO hagas esto
sudo gunicorn --bind 0.0.0.0:80 wsgi:app
```

Los puertos por debajo de **1024** son privilegiados: solo `root` puede
usarlos. Ejecutar la aplicación como `root` significa que, si alguien logra
ejecutar código en tu app, tendría control total de la máquina. Como usuario
normal, el sistema operativo lo limitaría.

La solución correcta: **NGINX escucha en el 80 y reenvía al 8000.**

### Instalar NGINX

```bash
sudo apt update
sudo apt install -y nginx
```

### Configurar el firewall UFW

Ubuntu trae el firewall **UFW**. Es una capa de seguridad que decide qué
tráfico pasa y cuál se bloquea.

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
sudo ufw enable
```

- `'Nginx Full'` abre los puertos **80** y **443**.
- `OpenSSH` abre el **22**, para no quedarte fuera del servidor al activar
  el firewall.

> **Advertencia:** si activas UFW sin permitir OpenSSH primero, perderás la
> conexión SSH y no podrás volver a entrar.

Arranca NGINX y habilítalo en el arranque:

```bash
sudo systemctl enable --now nginx
```

El flag `--now` hace `start` y `enable` en un solo comando.

Abre `http://<ip-publica>` en el navegador. Verás la página de bienvenida de
NGINX. Eso confirma que está escuchando en el puerto 80.

### El archivo de configuración

```bash
sudo nano /etc/nginx/sites-available/default
```

Borra todo el contenido (con `Ctrl+K` línea por línea) y escribe:

```nginx
server {
    listen 80;

    server_name todoapp-jose.example.com www.todoapp-jose.example.com;

    server_tokens off;
    client_max_body_size 10M;

    access_log /var/log/nginx/todoapp.access.log;
    error_log  /var/log/nginx/todoapp.error.log warn;

    # NGINX sirve los archivos estáticos directamente, sin tocar Python
    location /static/ {
        alias /home/ubuntu/todoapp/app/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://127.0.0.1:8000;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_redirect off;

        proxy_connect_timeout 30s;
        proxy_send_timeout    30s;
        proxy_read_timeout    30s;
    }
}
```

Guarda con `Ctrl+O`, `Enter`, `Ctrl+X`.

### Qué hace cada directiva

**`server_name`** con ambos nombres, con y sin `www`, separados por espacio.
NGINX usa este valor para decidir qué bloque `server` atiende cada petición.

**`location /static/`** intercepta las rutas de archivos estáticos antes de
llegar al proxy. `alias` apunta a la carpeta real en disco. `expires 30d`
dice al navegador que puede cachearlos 30 días.

**`proxy_pass http://127.0.0.1:8000`** reenvía todo lo demás a Gunicorn.
Usamos `127.0.0.1` y no `localhost` para evitar ambigüedad con IPv6.

**Las cabeceras `proxy_set_header`** son importantes. Sin ellas, todas las
peticiones parecerían venir de la propia máquina, y tus logs, límites por IP
y cualquier lógica basada en IP verían un solo cliente:

- `X-Real-IP`: la IP real del visitante.
- `X-Forwarded-For`: la cadena completa de proxies.
- `X-Forwarded-Proto`: si el usuario entró por `http` o `https`. Es lo que
  permite a Flask saber que la petición original era segura aunque NGINX se
  la pase por HTTP interno.

**`server_tokens off`** oculta la versión de NGINX en las cabeceras y
páginas de error. Endurecimiento gratuito.

**`client_max_body_size 10M`** limita el tamaño de las subidas. El valor por
defecto es 1 MB y produce errores 413 confusos.

### Nombres de dominio largos

Si tu dominio es largo, NGINX puede fallar con
`could not build server_names_hash`. Abre:

```bash
sudo nano /etc/nginx/nginx.conf
```

Y dentro del bloque `http { }` añade:

```nginx
server_names_hash_bucket_size 128;
```

### Comprobar y recargar

**Siempre** valida la sintaxis antes de recargar:

```bash
sudo nginx -t
```

Si todo está bien:

```
nginx: the configuration file /etc/nginx/nginx.conf syntax is ok
nginx: configuration file /etc/nginx/nginx.conf test is successful
```

Ahora recarga:

```bash
sudo systemctl reload nginx
```

`reload` aplica la configuración **sin cortar las conexiones activas**, a
diferencia de `restart`.

### Probar

Ahora, sin puerto:

```
http://todoapp-jose.example.com
```

### Cierra el puerto 8000

Ya no hace falta exponer Gunicorn. En el Security Group de AWS, **elimina la
regla del puerto 8000**. Y en `gunicorn.conf.py`, cambia el bind:

```python
bind = "127.0.0.1:8000"
```

Reinicia:

```bash
sudo systemctl restart todoapp
```

Ahora Gunicorn solo acepta conexiones de la propia máquina.

---

## 9. HTTPS con Certbot sin Docker

### Qué es SSL/TLS

**SSL** (Secure Sockets Layer, hoy técnicamente TLS) cifra los datos entre
cliente y servidor. Aunque alguien intercepte el tráfico, solo verá datos
cifrados.

Los certificados los emiten las **autoridades certificadoras (CA)**, que son
organizaciones terceras que validan la identidad del sitio. El certificado se
emite para un **nombre de dominio concreto**, y la CA verifica que quien lo
pide realmente controla ese dominio.

**Let's Encrypt** es una CA gratuita. La usaremos con la herramienta
**Certbot**.

### Instalar Certbot

En Ubuntu 20.04 o superior, `snap` ya viene instalado:

```bash
sudo snap install --classic certbot
sudo ln -s /snap/bin/certbot /usr/bin/certbot
```

### Emitir el certificado

```bash
sudo certbot --nginx
```

Certbot lee los `server_name` de tu configuración de NGINX, emite los
certificados y **modifica el archivo de NGINX automáticamente** para usarlos.

Te hará estas preguntas:

1. **Tu correo electrónico.** Recibirás avisos de renovación.
2. **Aceptar los términos de servicio.** Escribe `a` y Enter.
3. **Compartir el correo con la EFF.** `y` o `n`, a tu criterio.
4. **Para qué dominios activar HTTPS.** Presiona Enter para incluir todos
   los del `server_name`.
5. **Redirigir HTTP a HTTPS.** Elige la opción **2 (Redirect)**.

> El curso original sugiere la opción 1 (no redirigir). Para producción real
> **recomiendo la 2**: fuerza a todos los visitantes a HTTPS. Si alguien
> entra por `http://`, NGINX lo manda a `https://` automáticamente.

Reinicia NGINX:

```bash
sudo systemctl restart nginx
```

### Cómo queda la configuración

Certbot reescribe el archivo. Quedará algo así:

```nginx
server {
    server_name todoapp-jose.example.com www.todoapp-jose.example.com;

    location /static/ {
        alias /home/ubuntu/todoapp/app/static/;
        expires 30d;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl; # administrado por Certbot
    ssl_certificate /etc/letsencrypt/live/todoapp-jose.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/todoapp-jose.example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

server {
    if ($host = www.todoapp-jose.example.com) {
        return 301 https://$host$request_uri;
    }
    if ($host = todoapp-jose.example.com) {
        return 301 https://$host$request_uri;
    }

    listen 80;
    server_name todoapp-jose.example.com www.todoapp-jose.example.com;
    return 404;
}
```

El segundo bloque es el que redirige HTTP a HTTPS con código **301**
(movido permanentemente).

### Renovación automática

Los certificados de Let's Encrypt **duran 90 días**. Certbot instala un
temporizador que los renueva automáticamente. Compruébalo:

```bash
sudo systemctl status snap.certbot.renew.timer
```

Y prueba la renovación en seco, sin emitir nada:

```bash
sudo certbot renew --dry-run
```

### Cookies seguras en Flask

Con HTTPS activo, dile a Flask que marque las cookies como seguras. En
`app/config.py`:

```python
class ProductionConfig(Config):
    SESSION_COOKIE_SECURE = True      # solo enviar cookies por HTTPS
    SESSION_COOKIE_HTTPONLY = True    # JavaScript no puede leerlas
    SESSION_COOKIE_SAMESITE = "Lax"   # protección básica contra CSRF
    PREFERRED_URL_SCHEME = "https"
```

Y para que `url_for(..., _external=True)` genere URLs `https://`
correctamente detrás del proxy, añade en `app/__init__.py`:

```python
from werkzeug.middleware.proxy_fix import ProxyFix

def create_app(config_class=Config):
    app = Flask(__name__)
    ...
    # Confía en las cabeceras X-Forwarded-* que envía NGINX
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1)
    return app
```

> `ProxyFix` **solo** debe usarse cuando la app está realmente detrás de un
> proxy de confianza. Si la expusieras directamente, un cliente podría
> falsificar su propia IP en esas cabeceras.

---

## 10. CORS

### El problema

Por seguridad, el navegador **bloquea por defecto** las peticiones entre
orígenes distintos. Un **origen** es la combinación de protocolo, dominio y
puerto.

Sin esa restricción, un atacante podría crear una página que, al abrirla,
enviara peticiones al servidor de tu banco **usando tus cookies de sesión**.
Bastaría un clic en un enlace malicioso.

Pero esa restricción estorba en casos legítimos. Si tu frontend está en
`todoapp-jose.example.com` y tu API en `api.todoapp-jose.example.com`, el
navegador los considera orígenes distintos y bloquea las peticiones.

### Qué es CORS

**CORS** (Cross-Origin Resource Sharing) es el mecanismo por el que el
servidor declara desde qué orígenes acepta peticiones. Navegador y servidor
intercambian cabeceras especiales para negociarlo.

### Peticiones simples

Se usan para `GET`, `POST` y `HEAD` con cabeceras consideradas seguras:
`Accept`, `Accept-Language`, `Content-Language`, `Content-Type` y `Origin`.
Para `Content-Type` solo son seguros los valores
`application/x-www-form-urlencoded`, `multipart/form-data` y `text/plain`.

El navegador envía:

```http
GET /todos HTTP/1.1
Origin: https://todoapp-jose.example.com
Host: api.todoapp-jose.example.com
```

Y el servidor responde:

```http
HTTP/1.1 200 OK
Access-Control-Allow-Origin: https://todoapp-jose.example.com
Content-Type: application/json
```

El navegador permite la respuesta solo si `Access-Control-Allow-Origin`
incluye el origen desde el que se hizo la petición.

### Peticiones preflight

Para `PUT`, `PATCH`, `DELETE`, o cuando hay cabeceras "no seguras" como
`Authorization` o `Content-Type: application/json`, el navegador envía
**primero** una petición `OPTIONS` de sondeo:

```http
OPTIONS /todos/1 HTTP/1.1
Origin: https://todoapp-jose.example.com
Access-Control-Request-Method: PUT
Access-Control-Request-Headers: Content-Type, Authorization
```

El servidor responde qué permite:

```http
HTTP/1.1 204 No Content
Access-Control-Allow-Origin: https://todoapp-jose.example.com
Access-Control-Allow-Methods: GET, POST, PUT, PATCH, DELETE
Access-Control-Allow-Headers: Content-Type, Authorization
```

Solo si el sondeo pasa, el navegador envía la petición real.

Fíjate en la simetría: el navegador pregunta con `Request`, el servidor
responde con `Allow`.

### CORS en Flask

En Flask se usa la extensión **Flask-CORS**, que se encarga de las
cabeceras y de responder a los preflight automáticamente.

Añade a `requirements.txt`:

```
Flask-Cors==6.0.1
```

Instala:

```bash
pip install -r requirements.txt
```

Configura en `app/__init__.py`:

```python
from flask_cors import CORS

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Orígenes permitidos, leídos del entorno
    origenes = app.config["CORS_ORIGINS"]

    CORS(
        app,
        resources={r"/api/*": {"origins": origenes}},
        methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
        allow_headers=["Content-Type", "Authorization"],
        supports_credentials=True,
        max_age=600,
    )
    ...
```

Y en `app/config.py`:

```python
class Config:
    CORS_ORIGINS = [
        o.strip()
        for o in os.environ.get("CORS_ORIGINS", "http://localhost:5001").split(",")
        if o.strip()
    ]
```

En el `.env` de producción:

```bash
CORS_ORIGINS=https://todoapp-jose.example.com,https://www.todoapp-jose.example.com
```

### Buenas prácticas de CORS

**Nunca uses `*` en producción si manejas credenciales.** El valor
`Access-Control-Allow-Origin: *` permite peticiones desde cualquier sitio
web del mundo. Es aceptable en una API pública de solo lectura, nunca en una
API con sesiones o tokens.

De hecho, el navegador **prohíbe** combinar `*` con
`supports_credentials=True`.

**Limita el alcance.** En el ejemplo, CORS solo aplica a `/api/*`. Las rutas
HTML no lo necesitan porque el navegador las visita directamente.

**Lista los orígenes explícitamente**, incluyendo el protocolo. `https://` y
`http://` del mismo dominio son orígenes distintos.

**`max_age`** dice al navegador cuántos segundos puede cachear la respuesta
del preflight, ahorrando peticiones `OPTIONS` repetidas.

### CORS no es autenticación

Es un error común pensar que CORS protege la API. **No lo hace.** CORS es una
restricción que aplica el **navegador**, no el servidor. Un atacante con
`curl` o Postman ignora CORS por completo.

CORS protege a **tus usuarios** de que otra web use sus credenciales. Para
proteger tus **datos** necesitas autenticación y autorización.

---

## 11. Frontend y backend en el mismo dominio

Si tu proyecto separa frontend y backend, la configuración final tiene tres
bloques `server`.

> **Nota:** si tu aplicación Flask sirve sus propias plantillas Jinja, como
> hace la todo app de este repositorio, **no necesitas esta sección**. Ya
> tienes frontend y backend en el mismo dominio, y NGINX solo necesita el
> bloque `server` de la sección 8.

Esta sección aplica cuando el frontend es un conjunto de archivos estáticos
independientes (HTML, CSS y JavaScript) y Flask actúa solo como API JSON.

### Subir los archivos del frontend

Copia la carpeta con los archivos estáticos al servidor:

```bash
# Desde tu máquina local, en la carpeta del frontend
scp -r -i ~/.ssh/mi-llave.pem ./* ubuntu@todoapp-jose.example.com:/home/ubuntu/frontend
```

Las opciones de `scp`:

- `-r`: copia carpetas recursivamente.
- `-i`: indica explícitamente qué llave SSH usar.

Si tu frontend tiene un paso de construcción, ejecútalo **localmente** y
copia solo el resultado. El servidor no necesita el código fuente.

### Configuración de NGINX con dos bloques

```nginx
# Bloque 1: la API (backend Flask)
server {
    server_name api.todoapp-jose.example.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/todoapp-jose.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/todoapp-jose.example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

# Bloque 2: el frontend (archivos estáticos)
server {
    server_name todoapp-jose.example.com www.todoapp-jose.example.com;

    root /home/ubuntu/frontend;

    location / {
        try_files $uri $uri/ /index.html =404;
    }

    listen 443 ssl;
    ssl_certificate /etc/letsencrypt/live/todoapp-jose.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/todoapp-jose.example.com/privkey.pem;
    include /etc/letsencrypt/options-ssl-nginx.conf;
    ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;
}

# Bloque 3: redirección HTTP → HTTPS (lo genera Certbot)
server {
    if ($host = www.todoapp-jose.example.com) {
        return 301 https://$host$request_uri;
    }
    if ($host = todoapp-jose.example.com) {
        return 301 https://$host$request_uri;
    }
    listen 80;
    server_name todoapp-jose.example.com www.todoapp-jose.example.com;
    return 404;
}
```

### La directiva clave: `try_files`

```nginx
try_files $uri $uri/ /index.html =404;
```

Significa: busca el archivo exacto; si no existe, busca la carpeta; si
tampoco, **devuelve `/index.html`**; y si ni eso existe, error 404.

Esto es lo que hace funcionar una **Single Page Application**. Si el usuario
entra directamente a `/signup`, ese archivo no existe en disco. Sin
`try_files`, NGINX devolvería 404. Con ella, sirve `index.html`, carga el
JavaScript, y el router del frontend se encarga de mostrar la vista
correcta.

---

## 12. Ahora con Docker: NGINX en contenedor

Hasta aquí instalamos todo a mano. Ahora veamos la misma arquitectura con
Docker, que es lo que se usa en proyectos reales.

### Por qué Docker

| Problema sin Docker | Cómo lo resuelve Docker |
|---|---|
| "En mi máquina funciona" | La imagen es idéntica en todas partes |
| Instalar Python, Postgres, NGINX a mano | `docker compose up` y listo |
| Versiones distintas entre dev y prod | La misma imagen en ambos |
| Volver atrás tras un despliegue malo | Vuelves a la imagen anterior |
| Un proyecto necesita Python 3.10 y otro 3.12 | Cada contenedor tiene el suyo |

### Preparar el servidor para Docker

Ahora el servidor necesita **mucho menos**. No instalas Python, ni
PostgreSQL, ni NGINX. Solo Docker:

```bash
sudo apt update
sudo apt install -y ca-certificates curl gnupg git

# Repositorio oficial de Docker
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt update
sudo apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Permite usar Docker sin `sudo`:

```bash
sudo usermod -aG docker $USER
```

**Cierra la sesión SSH y vuelve a entrar** para que el cambio surta efecto.

Verifica:

```bash
docker --version
docker compose version
```

### El archivo de NGINX

En este repositorio, `nginx/nginx.conf`:

```nginx
upstream flask_app {
    # "web" es el nombre del servicio en docker-compose.
    # Docker provee DNS interno: no hace falta ninguna IP.
    server web:5000;
}

server {
    listen 80;
    server_name _;
    server_tokens off;

    client_max_body_size 10M;

    location /static/ {
        alias /app/app/static/;
        expires 30d;
        access_log off;
        add_header Cache-Control "public";
    }

    location / {
        proxy_pass http://flask_app;

        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;

        proxy_redirect off;

        proxy_connect_timeout 30s;
        proxy_send_timeout    30s;
        proxy_read_timeout    30s;
    }
}
```

**La diferencia clave con la versión sin Docker:** allí escribíamos
`proxy_pass http://127.0.0.1:8000`. Aquí escribimos `server web:5000`, donde
`web` es el **nombre del servicio** en `docker-compose.yml`. Docker resuelve
ese nombre a la IP del contenedor automáticamente. Si el contenedor se
reinicia con otra IP, sigue funcionando.

### El docker-compose de producción

```yaml
services:
  db:
    image: postgres:16-alpine
    restart: always
    environment:
      POSTGRES_USER: ${POSTGRES_USER:?POSTGRES_USER es obligatorio}
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD:?POSTGRES_PASSWORD es obligatorio}
      POSTGRES_DB: ${POSTGRES_DB:?POSTGRES_DB es obligatorio}
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U ${POSTGRES_USER} -d ${POSTGRES_DB}"]
      interval: 10s
      timeout: 5s
      retries: 5
    networks:
      - backend

  web:
    build: .
    restart: always
    depends_on:
      db:
        condition: service_healthy
    environment:
      SECRET_KEY: ${SECRET_KEY:?SECRET_KEY es obligatorio}
      DATABASE_URL: postgresql://${POSTGRES_USER}:${POSTGRES_PASSWORD}@db:5432/${POSTGRES_DB}
      GUNICORN_WORKERS: ${GUNICORN_WORKERS:-3}
    # Sin "ports": solo accesible a través de NGINX
    volumes:
      - static_files:/app/app/static
    command: ["gunicorn", "--config", "gunicorn.conf.py", "wsgi:app"]
    networks:
      - backend
      - frontend

  nginx:
    image: nginx:1.27-alpine
    restart: always
    depends_on:
      - web
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_files:/app/app/static:ro
    networks:
      - frontend

volumes:
  postgres_data_prod:
  static_files:

networks:
  frontend:
  backend:
    internal: true    # ← sin salida a internet
```

### Las decisiones de seguridad

**Solo NGINX publica puertos.** Los servicios `web` y `db` no tienen
sección `ports`. Son inalcanzables desde fuera de Docker. En la versión sin
Docker teníamos que acordarnos de cerrar el puerto 8000 en el Security
Group; aquí nunca se abre.

**`internal: true` en la red backend.** Los contenedores conectados solo a
esa red **no tienen conectividad externa en absoluto**. La base de datos es
accesible por la aplicación y por nadie más. El servicio `web` está en las
dos redes, que es lo que permite a NGINX alcanzarlo mientras la base de
datos sigue aislada.

**Secretos obligatorios.** La sintaxis `${VARIABLE:?mensaje}` hace que
Compose **se niegue a arrancar** si falta la variable. Es la diferencia entre
un fallo ruidoso al inicio y un agujero de seguridad silencioso donde
producción corre con `dev-secret-change-me`.

**Sin bind mount del código.** En desarrollo montamos `.:/app` para ver los
cambios al instante. En producción **no**: la imagen es el artefacto que
probaste y es lo que despliegas.

### El truco del volumen de estáticos

Hay un detalle que confunde a mucha gente. El volumen `static_files` se monta
en `/app/app/static` **en ambos contenedores**, para que NGINX pueda leer los
archivos.

Pero un volumen montado **tapa** lo que la imagen tenía en esa ruta. Sin
precauciones, NGINX serviría una carpeta vacía.

La solución está en el `Dockerfile`:

```dockerfile
# Copia intacta de los estáticos, fuera de la ruta que el volumen tapará
RUN cp -r /app/app/static /opt/static-dist
```

Y en `entrypoint.sh`:

```sh
if [ -d /opt/static-dist ]; then
  echo "Sincronizando archivos estáticos para NGINX..."
  cp -r /opt/static-dist/. /app/app/static/
fi
```

Cada vez que el contenedor arranca, restaura los estáticos desde la copia de
la imagen. **Esa línea del Dockerfile parece borrable y no lo es.**

### El entrypoint: esperar, migrar, servir

```sh
#!/bin/sh
set -e

echo "Esperando a PostgreSQL..."
until pg_isready -h "${POSTGRES_HOST:-db}" -p 5432 -U "${POSTGRES_USER:-todo}" -q; do
  sleep 1
done

if [ -d /opt/static-dist ]; then
  cp -r /opt/static-dist/. /app/app/static/
fi

if [ -d migrations ]; then
  echo "Aplicando migraciones..."
  flask db upgrade
fi

exec "$@"
```

Tres detalles importantes:

**`set -e`** aborta al primer comando que falle. Sin esto, una migración
fallida se registraría en el log y el servidor arrancaría igual, sirviendo
tráfico contra un esquema que no coincide con el código.

**`exec "$@"`** reemplaza el proceso del shell por Gunicorn, así Gunicorn
pasa a ser **PID 1** y recibe `SIGTERM` directamente de Docker. Sin `exec`,
el shell sigue siendo PID 1, las señales nunca llegan a Gunicorn, y cada
apagado tarda los 10 segundos completos hasta que Docker lo mata a la fuerza.

**Las migraciones se aplican solas** en cada arranque. No hay que acordarse
de ejecutarlas manualmente al desplegar.

### La base de datos con Docker: no la creas tú

Aquí está la diferencia más grande con la ruta sin Docker. Antes tuviste que
instalar PostgreSQL, entrar a `psql` y escribir `CREATE USER` y
`CREATE DATABASE` a mano. **Con Docker nada de eso hace falta.**

La imagen oficial de PostgreSQL crea la base y el usuario sola, leyendo tres
variables de entorno la primera vez que arranca:

```yaml
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: ${POSTGRES_USER}        # crea este usuario
      POSTGRES_PASSWORD: ${POSTGRES_PASSWORD} # con esta contraseña
      POSTGRES_DB: ${POSTGRES_DB}            # y esta base, vacía
    volumes:
      - postgres_data_prod:/var/lib/postgresql/data
```

Comparado con la ruta manual:

| Paso | Sin Docker | Con Docker |
|---|---|---|
| Instalar PostgreSQL | `apt install postgresql` | incluido en la imagen |
| Crear el usuario | `CREATE USER ...` en psql | `POSTGRES_USER` |
| Crear la base | `CREATE DATABASE ...` en psql | `POSTGRES_DB` |
| Crear las tablas | `flask db upgrade` a mano | el entrypoint, automático |

> **Detalle importante:** esas tres variables solo tienen efecto **la primera
> vez**, cuando el volumen `postgres_data_prod` está vacío. Si después
> cambias `POSTGRES_PASSWORD` en el `.env.prod` y reinicias, la contraseña
> **no cambia**, porque la base ya existe dentro del volumen. Para empezar de
> cero tienes que borrar el volumen con `down -v`, lo que destruye todos los
> datos.

Las **tablas** siguen siendo responsabilidad de las migraciones, igual que
antes. La diferencia es que `entrypoint.sh` ejecuta `flask db upgrade` en
cada arranque, así que no tienes que acordarte de hacerlo.

### Desplegar

```bash
# En el servidor
git clone https://github.com/tu-usuario/todoapp.git
cd todoapp

cp .env.prod.example .env.prod
nano .env.prod    # pon la contraseña y la SECRET_KEY reales

docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Verifica:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml ps
docker compose --env-file .env.prod -f docker-compose.prod.yml logs -f web
curl -I http://localhost/
```

En los logs del servicio `web` deberías ver la secuencia completa del
entrypoint:

```
Waiting for PostgreSQL at db:5432...
PostgreSQL is ready.
Applying database migrations...
INFO [alembic.runtime.migration] Running upgrade -> 18ad00069a11, create todos table
[INFO] Starting gunicorn 23.0.0
```

Comprueba que las tablas se crearon dentro del contenedor:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec db \
  psql -U todo -d todoapp -c "\dt"
```

---

## 13. HTTPS con Docker

Con Docker, Certbot no puede modificar la configuración de NGINX
automáticamente como hacía antes. Hay tres enfoques.

### Opción A: Certbot en contenedor con webroot (recomendada)

Let's Encrypt valida que controlas el dominio pidiendo un archivo en
`/.well-known/acme-challenge/`. La idea es que NGINX sirva esa carpeta desde
un volumen compartido con Certbot.

**1. Añade el servicio Certbot** a `docker-compose.prod.yml`:

```yaml
  certbot:
    image: certbot/certbot:latest
    volumes:
      - certbot_conf:/etc/letsencrypt
      - certbot_www:/var/www/certbot
    # Renueva cada 12 horas
    entrypoint: >
      /bin/sh -c "trap exit TERM;
      while :; do certbot renew --webroot -w /var/www/certbot --quiet;
      sleep 12h & wait $${!}; done;"

volumes:
  certbot_conf:
  certbot_www:
```

Y monta esos volúmenes también en NGINX:

```yaml
  nginx:
    volumes:
      - ./nginx/nginx.conf:/etc/nginx/conf.d/default.conf:ro
      - static_files:/app/app/static:ro
      - certbot_conf:/etc/letsencrypt:ro
      - certbot_www:/var/www/certbot:ro
```

**2. Configuración inicial de NGINX**, solo HTTP, para poder validar:

```nginx
server {
    listen 80;
    server_name todoapp-jose.example.com www.todoapp-jose.example.com;

    # Let's Encrypt deja aquí el archivo de validación
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host $host;
    }
}
```

Levanta el stack:

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml up -d
```

**3. Emite el certificado** (una sola vez):

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml run --rm certbot \
  certbot certonly --webroot -w /var/www/certbot \
  -d todoapp-jose.example.com \
  -d www.todoapp-jose.example.com \
  --email tu-correo@ejemplo.com \
  --agree-tos --no-eff-email
```

> **Consejo:** añade `--dry-run` la primera vez para probar sin gastar
> cuota. Let's Encrypt limita a **5 certificados por dominio por semana**, y
> es fácil agotarlo probando.

**4. Actualiza NGINX** para usar el certificado:

```nginx
# Redirección HTTP → HTTPS
server {
    listen 80;
    server_name todoapp-jose.example.com www.todoapp-jose.example.com;

    # El desafío ACME debe seguir siendo accesible por HTTP
    location /.well-known/acme-challenge/ {
        root /var/www/certbot;
    }

    location / {
        return 301 https://$host$request_uri;
    }
}

# Servidor HTTPS
server {
    listen 443 ssl;
    http2 on;
    server_name todoapp-jose.example.com www.todoapp-jose.example.com;

    ssl_certificate     /etc/letsencrypt/live/todoapp-jose.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/todoapp-jose.example.com/privkey.pem;

    ssl_protocols       TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers off;
    ssl_session_cache   shared:SSL:10m;
    ssl_session_timeout 1d;

    # HSTS: el navegador recordará usar solo HTTPS
    add_header Strict-Transport-Security "max-age=31536000" always;

    server_tokens off;
    client_max_body_size 10M;

    location /static/ {
        alias /app/app/static/;
        expires 30d;
        access_log off;
    }

    location / {
        proxy_pass http://flask_app;
        proxy_set_header Host              $host;
        proxy_set_header X-Real-IP         $remote_addr;
        proxy_set_header X-Forwarded-For   $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

**5. Recarga NGINX:**

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec nginx nginx -s reload
```

El servicio `certbot` renovará solo cada 12 horas. Para que NGINX recoja el
certificado renovado, recarga periódicamente, por ejemplo añadiendo al
comando de NGINX:

```yaml
  nginx:
    command: >
      /bin/sh -c "while :; do sleep 6h & wait $${!}; nginx -s reload; done & 
      nginx -g 'daemon off;'"
```

### Opción B: NGINX con Let's Encrypt automático

Existen imágenes que automatizan todo el proceso. La más usada combina
`nginx-proxy` con `acme-companion`:

```yaml
services:
  nginx-proxy:
    image: nginxproxy/nginx-proxy:latest
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - /var/run/docker.sock:/tmp/docker.sock:ro
      - certs:/etc/nginx/certs
      - vhost:/etc/nginx/vhost.d
      - html:/usr/share/nginx/html

  acme-companion:
    image: nginxproxy/acme-companion:latest
    volumes_from:
      - nginx-proxy
    volumes:
      - /var/run/docker.sock:/var/run/docker.sock:ro
      - acme:/etc/acme.sh
    environment:
      DEFAULT_EMAIL: tu-correo@ejemplo.com

  web:
    build: .
    environment:
      VIRTUAL_HOST: todoapp-jose.example.com
      LETSENCRYPT_HOST: todoapp-jose.example.com
      VIRTUAL_PORT: 5000

volumes:
  certs:
  vhost:
  html:
  acme:
```

Solo con declarar `VIRTUAL_HOST` y `LETSENCRYPT_HOST`, el proxy detecta el
contenedor, emite el certificado y configura NGINX automáticamente.

> **Advertencia importante:** esto monta el socket de Docker
> (`/var/run/docker.sock`) dentro de un contenedor. Quien controle ese socket
> **controla el demonio de Docker completo**, lo que equivale a ser root en
> el host. Es cómodo, pero conviene entender el riesgo.

### Opción C: Caddy en lugar de NGINX

**Caddy** es un servidor web que obtiene y renueva certificados de Let's
Encrypt **automáticamente**, sin configuración adicional.

`Caddyfile`:

```
todoapp-jose.example.com, www.todoapp-jose.example.com {
    handle_path /static/* {
        root * /app/app/static
        file_server
    }

    reverse_proxy web:5000
}
```

Y en Compose:

```yaml
  caddy:
    image: caddy:2-alpine
    restart: always
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile:ro
      - static_files:/app/app/static:ro
      - caddy_data:/data
      - caddy_config:/config
    networks:
      - frontend

volumes:
  caddy_data:
  caddy_config:
```

Eso es **todo**. Caddy detecta los dominios del `Caddyfile`, pide los
certificados al arrancar, los renueva solo, y configura HTTPS con
redirección desde HTTP. Son diez líneas contra las cincuenta de la opción A.

### Cuál elegir

| Opción | Ventaja | Desventaja |
|---|---|---|
| **A: Certbot webroot** | Control total, NGINX estándar | Configuración manual larga |
| **B: acme-companion** | Automático, muy poco código | Expone el socket de Docker |
| **C: Caddy** | El más simple con diferencia | Cambias NGINX por otro servidor |

Para aprender, la **A**. Para un proyecto pequeño, la **C**.

---

## 14. Actualizar el código en producción

### Sin Docker

```bash
cd /home/ubuntu/todoapp
git pull

source venv/bin/activate
pip install -r requirements.txt     # si cambiaron las dependencias
flask db upgrade                    # si hay migraciones nuevas

sudo systemctl restart todoapp
```

### Con Docker

```bash
cd /home/ubuntu/todoapp
git pull

docker compose --env-file .env.prod -f docker-compose.prod.yml up -d --build
```

Un solo comando. Reconstruye la imagen, aplica las migraciones en el
entrypoint, y reemplaza los contenedores.

> **Recuerda:** en producción no hay bind mount del código. Si haces
> `git pull` y no reconstruyes la imagen, **no verás ningún cambio**. Eso es
> intencional, no un fallo.

### Copia de seguridad de la base de datos

**Sin Docker:**

```bash
pg_dump -U todo todoapp > respaldo-$(date +%F).sql
```

**Con Docker:**

```bash
docker compose --env-file .env.prod -f docker-compose.prod.yml exec -T db \
  pg_dump -U todo todoapp > respaldo-$(date +%F).sql
```

Haz esto **antes** de cualquier migración que borre o transforme datos. Y
prueba la restauración al menos una vez: una copia sin probar no es una
copia.

---

## 15. Comparación: con Docker vs sin Docker

| Aspecto | Sin Docker | Con Docker |
|---|---|---|
| **Instalación en el servidor** | Python, venv, PostgreSQL, NGINX, Certbot | Solo Docker |
| **Crear la base y el usuario** | A mano en `psql` | Variables de entorno |
| **Gestor de procesos** | systemd (`.service`) | `restart: always` en Compose |
| **Reenvío de NGINX** | `proxy_pass http://127.0.0.1:8000` | `proxy_pass http://web:5000` |
| **Aislar la base de datos** | Confiar en `listen_addresses` y el firewall | `internal: true` en la red |
| **Migraciones** | Manual: `flask db upgrade` | Automático en el entrypoint |
| **Certificados** | `sudo certbot --nginx`, muy simple | Requiere volúmenes compartidos |
| **Actualizar** | `git pull` + `pip install` + `restart` | `git pull` + `up -d --build` |
| **Volver atrás** | Difícil | Usar la imagen anterior |
| **Reproducibilidad** | "En mi máquina funcionaba" | Idéntico en todas partes |
| **Curva de aprendizaje** | Ves cada pieza por separado | Hay que entender Docker primero |

### La conclusión honesta

**Sin Docker es mejor para aprender.** Instalas cada pieza, ves qué hace,
y cuando algo falla entiendes por qué. Además, Certbot con NGINX nativo es
notablemente más simple.

**Con Docker es mejor para trabajar.** El despliegue es un comando, el
entorno es idéntico en todas partes, y volver atrás es trivial.

Lo ideal es hacer el camino largo una vez, entender cada pieza, y después
usar Docker sabiendo qué está automatizando por ti.

---

## 16. Checklist final

### Servidor
- [ ] Instancia EC2 creada con Ubuntu
- [ ] Puertos 22, 80 y 443 abiertos en el Security Group
- [ ] Puerto de la aplicación (8000) **cerrado** tras instalar NGINX
- [ ] Llave SSH guardada con permisos `400`
- [ ] Firewall UFW activo con OpenSSH permitido

### Aplicación
- [ ] Código clonado en el servidor
- [ ] Dependencias instaladas
- [ ] `.env` creado con permisos `600` y **fuera de Git**
- [ ] `SECRET_KEY` aleatoria y única, no la de desarrollo
- [ ] Base de datos **vacía** creada en el servidor (sin Docker) o
      declarada con `POSTGRES_DB` (con Docker)
- [ ] Contraseña de producción distinta a la de desarrollo
- [ ] Migraciones aplicadas: crean las tablas (`flask db upgrade`)
- [ ] `FLASK_DEBUG=0` en producción

### Servidor WSGI
- [ ] Gunicorn escuchando solo en `127.0.0.1`
- [ ] Servicio systemd creado y habilitado (o `restart: always`)
- [ ] Arranca automáticamente tras reiniciar el servidor

### NGINX
- [ ] Instalado y habilitado
- [ ] `server_name` con los dominios reales, con y sin `www`
- [ ] Archivos estáticos servidos por NGINX
- [ ] Cabeceras `X-Forwarded-*` configuradas
- [ ] `sudo nginx -t` sin errores

### Dominio y HTTPS
- [ ] Subdominio apuntando a la IP del servidor
- [ ] Versión con `www` también registrada
- [ ] Certificado emitido con Certbot
- [ ] Redirección de HTTP a HTTPS activa
- [ ] Renovación automática verificada (`certbot renew --dry-run`)
- [ ] Cookies marcadas como `Secure` y `HttpOnly`

### Seguridad
- [ ] Base de datos **no** accesible desde internet
- [ ] CORS con lista explícita de orígenes, sin `*`
- [ ] Protección CSRF si hay formularios con sesión
- [ ] `server_tokens off` en NGINX
- [ ] Copia de seguridad de la base de datos programada

---

## Recursos

- [Documentación de Flask sobre despliegue](https://flask.palletsprojects.com/en/stable/deploying/)
- [Documentación de Gunicorn](https://docs.gunicorn.org/)
- [Documentación de NGINX](https://nginx.org/en/docs/)
- [Certbot](https://certbot.eff.org/)
- [Let's Encrypt: límites de emisión](https://letsencrypt.org/docs/rate-limits/)
- [Flask-CORS](https://flask-cors.readthedocs.io/)
- [Curso original app-web-i](https://isw-lia.gitbook.io/app-web-i)
