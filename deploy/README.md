# Containerized Deployment (Docker Compose)

This setup runs the Django app (with SageMath), Nginx, Postgres, and the Pyro5 services in containers. It replaces Supervisor/system-level scripts.

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
- `nginx`: reverse proxy on `:80`, serves `/static` from the shared `staticfiles` volume
- `db`: Postgres
- `pyro-ns`: Pyro5 name server (port 9090)
- `eval`: SafeEval worker (`services/eval.py`)
- `data-fetcher`: one-shot helper to clone/pull `numberdb-data` into the shared volume

## Configuration
- Database URL is overridden for Compose: `DATABASE_URL=postgres://u_numberdb:$POSTGRES_KEY@db:5432/numberdb`.
- Pyro5 discovery is set via env: `PYRO_NS_HOST=pyro-ns`, `PYRO_NS_PORT=9090`.
- Static files: `web` runs `collectstatic` on startup; files live in the `staticfiles` volume, served by Nginx.

## Updating
- Pull new images / rebuild:
  docker compose pull && docker compose up -d --build
- Apply migrations:
  docker compose run --rm web sage -python manage.py migrate
- Update data:
  docker compose run --rm data-fetcher

## TLS
Terminate TLS at Nginx (container or upstream). For Let’s Encrypt, run a certbot companion or manage certificates externally and mount them into the Nginx container.

