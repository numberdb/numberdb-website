# New VM Deployment Guide

This guide covers two phases: private staging without DNS (access via SSH tunnel), and going live with DNS + HTTPS.

## Prerequisites
- Ubuntu LTS VM with SSH access.
- Docker + Compose plugin installed (script does this for you).
- Repo on your laptop with `scripts/provision_vm.sh`.

## A) Private Staging (No DNS)
1) Provision the VM (HTTP only, no public exposure):
   - From your laptop:
     - `scripts/provision_vm.sh --no-wiki --no-oeis user@host`
     - Secrets live in `/.env.prod` on the server (not committed).
2) Restrict Nginx to localhost:
   - On the server (`/opt/numberdb-website`), create `docker-compose.override.yml`:
     - `services:
  nginx:
    ports:
      - "127.0.0.1:8080:80"`
   - Apply: `docker compose up -d nginx`
3) Open an SSH tunnel from your laptop:
   - `ssh -N -L 8080:127.0.0.1:8080 user@host`
   - Browse: `http://localhost:8080`
4) Data builds (optional, can be heavy on small VMs):
   - Core: `docker compose run --rm web sage -python db_builder/build.py`
   - OEIS: `docker compose run --rm web sh -lc './db_builder/update-oeis.sh && sage -python db_builder/build-oeis.py'`
   - Wikipedia: `docker compose exec -T web sh -lc 'nohup sage -python db_builder/build-wikipedia.py > /app/build_wiki.log 2>&1 &'`

## B) Go Live (DNS + HTTPS)
1) Point DNS A/AAAA to the VM and set `.env`:
   - `SERVER_NAME=example.org`
   - `LETSENCRYPT_EMAIL=admin@example.org`
2) Restore public ports (remove local bind in `docker-compose.override.yml` or use `80:80`, `443:443`).
3) Issue TLS and enable HTTPS:
   - `docker compose up -d nginx`
   - `docker compose run --rm certbot certonly --webroot -w /var/www/certbot -d $SERVER_NAME --email $LETSENCRYPT_EMAIL --agree-tos --no-eff-email`
   - `docker compose restart nginx`
4) Auto‑renew runs in `certbot-renew`.

## Useful
- Logs: `docker compose logs -f web`, `docker compose logs -f nginx`
- Admin user: `docker compose exec -T web sh -lc 'DJANGO_SUPERUSER_PASSWORD=... DJANGO_SUPERUSER_USERNAME=admin DJANGO_SUPERUSER_EMAIL=admin@example.org sage -python manage.py createsuperuser --noinput'`
- Low‑RAM defaults are set; adjust `PG_*` and `GUNICORN_WORKERS` in `.env` if needed.

