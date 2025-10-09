# NumberDB Website

Website and data builder for https://numberdb.org.

Core data is imported from the companion repository numberdb-data (cloned next to this repo).

## Prerequisites
- SageMath installed (`sage` on PATH)
- Python 3; Postgres (default) or SQLite for local dev
- `.env` file at repo root (seeded from `install/env.dev.example`)

## Repository Layout
- `numberdb/` Django project settings, URLs, WSGI/ASGI
- `db/` Main app (models, views, templates, tests)
- `db_builder/` Data import/build scripts (SageMath; OEIS/Wikipedia helpers)
- `services/` Pyro5 evaluation service used by the app
- `templates/`, `static/` source assets; `staticfiles/` is collected output
- `deploy/` Deployment assets (Docker Compose, Nginx snippets)
- `tests/` Additional Sage-based tests; `manage.py` project entry
- `.env` local settings (see `install/env.dev.example`)

## Local Development
- Install deps and set up data/DB:
  - `make install`
- Run the dev server at `http://localhost:8000`:
  - `make run`
- Run tests:
  - `make test`

Notes
- Default DB is Postgres via `DATABASE_URL` in `.env`. For quick local setup you can use SQLite: `DATABASE_URL=sqlite:///db.sqlite3`.
- `.env` defines `PYTHON`, `PIP`, and `MANAGE` (typically `sage -python manage.py`).

### Common Make Targets
- `make fetch_data` — clone/pull `../numberdb-data`
- `make build_db_numbers` — build core data tables
- `make build_db_all` — build extended data tables
- `make migrations` — create/apply schema migrations
- `make static` — collect static assets to `staticfiles/`
- `make update` — housekeeping and updates

## Data: Fetch and Build
- Clone/pull the data repo next to this repo:
  - `make fetch_data` (creates/updates `../numberdb-data`)
- Build core tables:
  - `make build_db_numbers` (core) or `make build_db_all` (extended)

The data builder lives under `db_builder/` and uses SageMath.

## Sage Interface
From a Sage session you can query NumberDB directly:

```
sage: load('https://raw.githubusercontent.com/numberdb/numberdb-website/main/interfaces/numberdb-sage-interface.py')
sage: search('{n: pi^n for n in [1..5]}')
```

Query syntax matches the Advanced Search guide on https://www.numberdb.org/help#section-advanced-search-guide.

## Deployment (Docker Compose)
This setup runs the Django app (with SageMath), Nginx, Postgres, and the Pyro5 services in containers. TLS is provided via Let’s Encrypt using the webroot challenge.

### Services
- `web`: Django + Gunicorn (internal port 8000)
- `nginx`: reverse proxy on `:80` and `:443`, serves `/static` and ACME challenges
- `db`: Postgres
- `pyro-ns`: Pyro5 name server (port 9090)
- `eval`: SafeEval worker (`services/eval.py`)
- `data-fetcher`: one-shot helper to clone/pull `numberdb-data`
- `certbot`/`certbot-renew`: certificate issuance and renewal

### First Run
1) Build and start:
   - `docker compose up -d --build`
2) Fetch data (shared volume):
   - `docker compose run --rm data-fetcher`
3) Apply migrations and create an admin:
   - `docker compose run --rm web sage -python manage.py migrate`
   - `docker compose run --rm web sage -python manage.py createsuperuser`

### TLS: Initial Certificate
- Set in `.env` on the server:
  - `SERVER_NAME=example.org`
  - `LETSENCRYPT_EMAIL=admin@example.org`
- Start HTTP-only stack:
  - `docker compose up -d nginx web db pyro-ns eval`
- Issue certificate (webroot):
  - `docker compose run --rm -e CERTBOT_EMAIL=${LETSENCRYPT_EMAIL} certbot certonly --webroot -w /var/www/certbot -d ${SERVER_NAME} --email ${LETSENCRYPT_EMAIL} --agree-tos --no-eff-email`
- Reload Nginx:
  - `docker compose restart nginx`

### Updating
- `docker compose pull && docker compose up -d --build`
- `docker compose run --rm web sage -python manage.py migrate`
- `docker compose run --rm data-fetcher`

## Staging and Go Live
### Private Staging (no DNS)
- Bind Nginx to localhost with `docker-compose.override.yml` in repo root:

```
services:
  nginx:
    ports:
      - "127.0.0.1:8080:80"
```

- Start Nginx: `docker compose up -d nginx`
- SSH tunnel from your machine: `ssh -N -L 8080:127.0.0.1:8080 user@host`
- Browse: `http://localhost:8080`

### Going Live (DNS + HTTPS)
- Point DNS A/AAAA to the VM and set `SERVER_NAME`, `LETSENCRYPT_EMAIL` in `.env`.
- Expose `80:80` and `443:443` for `nginx` (remove local bind), obtain the certificate as above, then restart Nginx.

### Optional Data Builds (heavy)
- Core build:
  - `docker compose run --rm web sage -python db_builder/build.py`
- OEIS build:
  - `docker compose run --rm web sh -lc './db_builder/update-oeis.sh && sage -python db_builder/build-oeis.py'`
- Wikipedia build (detached):
  - `docker compose exec -T web sh -lc 'nohup sage -python db_builder/build-wikipedia.py > /app/build_wiki.log 2>&1 &'`

## Configuration and Security
- Never commit real secrets. Create `.env` from `install/env.dev.example` and adjust locally; on servers manage secrets out-of-repo.
- Set `ALLOWED_HOSTS`, `DEBUG=False` in production.
- Email backend and social logins (e.g., GitHub) are configured via `.env`.

## Troubleshooting
- Certificate issuance fails: ensure DNS for `SERVER_NAME` points to your server and rerun the Certbot command above, then `docker compose restart nginx`.
- Low‑RAM servers: reduce Postgres and Gunicorn settings via env (e.g., `PG*`, `GUNICORN_WORKERS`).
