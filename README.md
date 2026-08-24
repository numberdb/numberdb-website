# NumberDB Website

Website and data builder for https://numberdb.org.

Core data is imported from the companion repository numberdb-data (cloned next to this repo).

## Prerequisites
- SageMath installed (`sage` on PATH)
- Python 3; Postgres database (required)
- `.env` file at repo root (seeded from `env/.env.dev.example`)

## Repository Layout
- `numberdb/` Django project settings, URLs, WSGI/ASGI
- `numberdb_app/` Main Django app (models, views, templates, tests)
- `data_pipeline/` Data import/build scripts (SageMath; OEIS/Wikipedia helpers)
- `utils/` Number parsing, formatting and the wire format shared by app and builder
- `workers/` sandboxed evaluator used by the app (see docs/design/eval-sandbox.md)
- `templates/`, `static/` source assets; `staticfiles/` is collected output
- `deploy/` Deployment assets (Docker Compose, Nginx snippets)
- `clients/python/` the `numberdb` client package, published to PyPI
- `generators/` per-table programs that recompute a table and publish it
- `scripts/` deployment (`ship.sh`), systemd units, and one-off corrections
- `docs/` Design notes and the backlog
- `tests/` Additional Sage-based tests; `manage.py` project entry
- `.env` local settings (see `env/.env.dev.example`)

## Local Development
- Install deps and set up data/DB:
  - `make install`
- Run the dev server at `http://localhost:8000`:
  - `make run`
- Run tests:
  - `make test`

Notes
- Default DB is Postgres via `DATABASE_URL` in `.env`. SQLite is discouraged even for local development due to missing features and different behavior; prefer a local Postgres instance.
- `.env` defines `PYTHON`, `PIP`, and `MANAGE` (typically `sage -python manage.py`).
- The site serves the agent skill at `/skill`, reading
  `.claude/skills/numberdb-table/SKILL.md`. The image copies the whole
  repository, so this works in production; a development override that mounts
  source directories one by one needs `./.claude:/app/.claude:ro` and
  `./AGENTS.md:/app/AGENTS.md:ro` as well, or the page 404s locally and works
  deployed, and the tests that check those pointers read a stale copy.

### Common Make Targets
- `make fetch_data`: clone/pull `../numberdb-data`
- `make build_db_numbers`: build core data tables
- `make build_db_all`: build extended data tables
- `make migrations`: create/apply schema migrations
- `make static`: collect static assets to `staticfiles/`
- `make update`: housekeeping and updates

## Data: Fetch and Build
- Clone/pull the data repo next to this repo:
  - `make fetch_data` (creates/updates `../numberdb-data`)
- Build core tables:
  - `make build_db_numbers` (core) or `make build_db_all` (extended)

The data builder lives under `data_pipeline/` and uses SageMath.

## Querying NumberDB from Python or Sage

Install the client package:

```
$ pip install numberdb          # or: sage -pip install numberdb
```

```python
>>> import numberdb
>>> numberdb.search_real_ball(3.14159265, 1e-8)[0].table.title
'Pi'
```

In Sage, `import numberdb.sage as numberdb` gives the same calls with Sage
objects coming back. That works with SageMath and with
[passagemath](https://github.com/passagemath/passagemath), the modular pip
distribution -- `pip install passagemath-symbolics numberdb` into a fresh
environment is enough for everything but p-adics. The package lives in
`clients/python/`, is published to [PyPI](https://pypi.org/project/numberdb/),
and its [README](clients/python/README.md) documents every call.

It replaces the old `clients/sage/numberdb-sage-interface.py`, which was
loaded over the network and called `loads()` on server-supplied bytes; that
hands code execution to anyone able to answer the request. Decoding in the
package is a fixed table of seven decoders and nothing else.

### HTTP API

The package is the supported route, but the endpoints are plain HTTP:

- `GET /api/lookup` looks up a number you already have: `?number=<json>`,
  `?numbers=<json list>` (batched, at most 100), `?polynomial=<text>`,
  `?polynomial_hash=<digest>`, or `?text=<term>` for the search bar's grammar.
- `GET /api/search?expression=<sage>` evaluates a Sage expression in the
  sandboxed evaluator and searches the result.
- `GET /api/table?id=T12` and `GET /api/tag?url=<name>` return a table or a tag.

Anonymous callers are rate limited per hour; an API key raises the limit.
Keys are issued from the site, and sent as `Authorization: Bearer <key>` or
`X-API-Key`. See https://numberdb.org/help#section-api.

## Deployment (Docker Compose)
This setup runs the Django app (with SageMath), Nginx, Postgres, and the sandboxed evaluator in containers. TLS is provided via Let’s Encrypt using the webroot challenge.

### Services
- `web`: Django + Gunicorn
  - Ports: internal `8000` (not exposed publicly)
  - Healthcheck: TCP connect to `127.0.0.1:8000` inside the container
- `nginx`: reverse proxy and static serving
  - Ports: `80` (HTTP), `443` (HTTPS)
  - TLS: serves via Let’s Encrypt certs in the `letsencrypt` volume
- `db`: Postgres
  - Ports: internal only (no host mapping by default)
- `evaluator`: sandboxed evaluator for advanced-search expressions
  - Ports: **none** -- runs with `network_mode: none`, no interfaces at all
  - Reached only over a Unix socket on the `eval-sock` volume
  - Each expression runs in a forked child that handles one request and exits
  - See `docs/design/eval-sandbox.md`
- `data-fetcher`: one-shot helper to clone/pull `numberdb-data`
- `certbot`/`certbot-renew`: certificate issuance and renewal

### Settings Split
- Use `numberdb.settings.dev` for local development (default in `manage.py`).
- Use `numberdb.settings.prod` for production (default in Docker environment).

### Data Volumes
- `staticfiles`: collected Django static assets served by Nginx
- `pgdata`: Postgres data directory (persistent)
- `numberdb-data`: checked-out copy of the numberdb-data repo (shared)
- `certbot-www`: ACME webroot for challenges
- `letsencrypt`: issued TLS certificates and renewal state

Backups: snapshot `pgdata` and, if needed, `letsencrypt`. `numberdb-data` is re-fetchable; `staticfiles` is reproducible via collectstatic.

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
  - `docker compose up -d nginx web db evaluator`
- Issue certificate (webroot):
  - `docker compose run --rm -e CERTBOT_EMAIL=${LETSENCRYPT_EMAIL} certbot certonly --webroot -w /var/www/certbot -d ${SERVER_NAME} --email ${LETSENCRYPT_EMAIL} --agree-tos --no-eff-email`
- Reload Nginx:
  - `docker compose restart nginx`

### Updating
- `docker compose pull && docker compose up -d --build`
- `docker compose run --rm web sage -python manage.py migrate`
- `docker compose run --rm data-fetcher`

### Production Overrides
- You can layer production overrides using the provided file at `deploy/compose/docker-compose.prod.yml`:
  - `docker compose -f docker-compose.yml -f deploy/compose/docker-compose.prod.yml up -d --build`
- This enables `restart: unless-stopped` and runs DB migrations automatically on start (`AUTO_MIGRATE=1`).

## Staging and Go Live
### Quick Staging (recommended)
- One command to provision a fresh VM, bind Nginx to localhost, open a tunnel, and build core data:
  - `scripts/deploy.sh quickstage user@host`
- When done, browse: `http://localhost:8080`

### Staging (customizable)
- Stage with options (no background builds, or keep wiki/OEIS off):
  - `scripts/deploy.sh stage [--force-secrets] [--no-build] [--no-wiki] [--no-oeis] user@host [/remote/path] [--open-tunnel]`
- This uses `scripts/provision_vm.sh` under the hood to install Docker, copy the repo, create `.env`/`.env.prod`, start the stack (HTTP), and seed data/admin.
- To open a tunnel later: `ssh -N -L 8080:127.0.0.1:8080 user@host`

### Going Live (DNS + HTTPS)
- Point DNS A/AAAA to your VM.
- Promote the staged setup to HTTPS with a single command:
  - `scripts/deploy.sh live user@host example.org admin@example.org`
- The command sets `SERVER_NAME` and `LETSENCRYPT_EMAIL`, removes local-only port binding, issues a TLS cert via Certbot, and restarts Nginx.

Tip: To avoid passing arguments, set these in `.env` (used by Makefile wrappers):
- `DEPLOY_REMOTE`, `DEPLOY_RPATH`, `DEPLOY_DOMAIN`, `DEPLOY_EMAIL`
Then run `make deploy_quickstage`, `make deploy_stage`, or `make deploy_live` without extra flags. For ad‑hoc options during staging, pass `FLAGS=...` on the command line, e.g. `make deploy_stage FLAGS="--no-build --no-wiki"`.

### Optional Data Builds (heavy)
- Core build:
  - `docker compose run --rm web sage -python data_pipeline/build.py`
- OEIS build:
  - `docker compose run --rm web sh -lc './data_pipeline/update-oeis.sh && sage -python data_pipeline/build-oeis.py'`
- Wikipedia build (detached):
  - `docker compose exec -T web sh -lc 'nohup sage -python data_pipeline/build-wikipedia.py > /app/build_wiki.log 2>&1 &'`

## Configuration and Security
- Never commit real secrets. Create `.env` from `env/.env.dev.example` and adjust locally; on servers manage secrets out-of-repo.
- Set `ALLOWED_HOSTS`, `DEBUG=False` in production.
- Email backend and social logins (e.g., GitHub) are configured via `.env`.

## Troubleshooting
- Certificate issuance fails: ensure DNS for `SERVER_NAME` points to your server and rerun the Certbot command above, then `docker compose restart nginx`.
- Low‑RAM servers: reduce Postgres and Gunicorn settings via env (e.g., `PG*`, `GUNICORN_WORKERS`).

## Scripts
- `deploy/docker/entrypoint.web.sh`: container entrypoint for the app. Optionally runs migrations (`AUTO_MIGRATE=1|true`), collects static, and launches Gunicorn as the `sage` user.
- `deploy/docker/entrypoint.nginx.sh`: container entrypoint for Nginx. Chooses HTTP vs. HTTPS config based on presence of Let’s Encrypt certs for `SERVER_NAME`.
- `scripts/provision_vm.sh`: one-shot VM bootstrap and deploy over HTTP (installs Docker remotely, copies repo, generates `.env`, starts stack, seeds data/admin). Flags: `--force-secrets`, `--no-build`, `--no-wiki`, `--no-oeis`.
- `scripts/deploy.sh`: convenience wrapper for staging and go-live: `stage`, `live`, `status`, `quickstage`. Can bind Nginx to localhost and open an SSH tunnel.
- `scripts/deploy_ssh.sh`: deploy via Docker context over SSH to an existing remote host; attempts initial TLS issuance.

## Licence

Three parts, three licences, for reasons rather than taste:

| | Licence | Why |
|---|---|---|
| This repository (the website) | **GPL-3.0-or-later** | It imports SageMath, which is GPL-3.0-or-later, so the combined work must be too. |
| `clients/python` (the `numberdb` package) | **MIT** | A client library exists to be depended on, and it has no Sage dependency -- Sage is imported only if the user asks for a Sage object. |
| [numberdb-data](https://github.com/numberdb/numberdb-data) (the data) | **CC BY-SA 4.0** | Matches both upstream sources, Wikipedia and the OEIS, and keeps improvements to the database in the commons. |

Contributions to the data are covered by the [Contributor's Licence
Agreement](https://github.com/numberdb/numberdb-data/blob/main/CONTRIBUTING.md).

Sequence names shown from the On-Line Encyclopedia of Integer Sequences are
(c) the OEIS Foundation Inc., licensed CC BY-SA 4.0.
