# Containerized Deployment (Docker Compose)

This setup runs the Django app (with SageMath), Nginx, Postgres, and the Pyro5 services in containers. It replaces Supervisor/system-level scripts. TLS is provided via Let’s Encrypt (Certbot) using the webroot challenge.

## Prerequisites
- Docker and Docker Compose plugin installed.
- A `.env` file in the repo root for app settings (no secrets committed).

## First Run
- Build and start services:
  docker compose up -d --build
- Initialize the data repository (once, and whenever you want to update):
  docker compose run --rm data-fetcher
- Run database migrations (recommended as a separate step):
  docker compose run --rm web sage -python manage.py migrate
- Create an admin user:
  docker compose run --rm web sage -python manage.py createsuperuser

## Services
- `web`: Django + Gunicorn (port 8000, internal only)
- `nginx`: reverse proxy on `:80` and `:443`, serves `/static` and ACME challenges; uses `/etc/letsencrypt` for certificates
- `db`: Postgres
- `pyro-ns`: Pyro5 name server (port 9090)
- `eval`: SafeEval worker (`services/eval.py`)
- `data-fetcher`: one-shot helper to clone/pull `numberdb-data` into the shared volume
- `certbot`: on-demand certificate issuance (manual run)
- `certbot-renew`: background certificate renewal (12h loop)

## Configuration
- Database URL is overridden for Compose: `DATABASE_URL=postgres://u_numberdb:$POSTGRES_KEY@db:5432/numberdb`.
- Pyro5 discovery is set via env: `PYRO_NS_HOST=pyro-ns`, `PYRO_NS_PORT=9090`.
- Static files: `web` runs `collectstatic` on startup; files live in the `staticfiles` volume, served by Nginx.
- TLS: set `SERVER_NAME=example.org` and `LETSENCRYPT_EMAIL=admin@example.org` in your `.env` (on the server). Nginx will serve HTTP until the first certificate is obtained.

## TLS: Initial Certificate
- Ensure `SERVER_NAME` is set in `.env`.
- Start `nginx` and dependencies (HTTP only):
  docker compose up -d nginx web db pyro-ns eval
- Issue certificate (replace hostnames/email):
  docker compose run --rm -e CERTBOT_EMAIL=${LETSENCRYPT_EMAIL} certbot certonly --webroot -w /var/www/certbot -d ${SERVER_NAME} --email ${LETSENCRYPT_EMAIL} --agree-tos --no-eff-email
- Reload `nginx` to pick up TLS:
  docker compose restart nginx

Certificates renew automatically by `certbot-renew`.

## Updating
- Pull new images / rebuild:
  docker compose pull && docker compose up -d --build
- Apply migrations:
  docker compose run --rm web sage -python manage.py migrate
- Update data:
  docker compose run --rm data-fetcher

## TLS
TLS terminates at the `nginx` container using Let’s Encrypt certificates stored in the `letsencrypt` volume. For custom domains or multiple SANs, run `certbot` with multiple `-d` flags.

## Deploying to a Fresh Ubuntu LTS Server
1) Prepare the server (as a sudo user):
   - Install Docker + Compose plugin:
     sudo apt-get update && sudo apt-get install -y ca-certificates curl gnupg
     sudo install -m 0755 -d /etc/apt/keyrings
     curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
     echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo $VERSION_CODENAME) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
     sudo apt-get update && sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin
     sudo usermod -aG docker $USER && newgrp docker

2) Get the code onto the server:
   - Clone the repo and checkout the deployment branch:
     git clone <your-fork-url>.git numberdb-website && cd numberdb-website
     git checkout docker-deploy

3) Create the environment file on the server (`.env` in repo root):
   - Required keys (example):
     SECRET_KEY=change_me
     POSTGRES_KEY=strong_db_password
     DEBUG=False
     ALLOWED_HOSTS=.numberdb.org,example.org
     EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
     SERVER_NAME=example.org
     LETSENCRYPT_EMAIL=admin@example.org

4) First bring-up:
   - Build images and start core services:
     docker compose up -d --build db pyro-ns eval web nginx
   - Initialize data repo:
     docker compose run --rm data-fetcher
   - Run database migrations and create admin:
     docker compose run --rm web sage -python manage.py migrate
     docker compose run --rm web sage -python manage.py createsuperuser
   - Issue TLS certificate:
     docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d ${SERVER_NAME} --email ${LETSENCRYPT_EMAIL} --agree-tos --no-eff-email
     docker compose restart nginx

5) Ongoing maintenance:
   - Update app:
     git pull && docker compose pull && docker compose up -d --build
   - Apply migrations:
     docker compose run --rm web sage -python manage.py migrate
   - Update data:
     docker compose run --rm data-fetcher
