# Repository Guidelines

## Project Structure & Module Organization
- `numberdb/` Django project settings, URLs, and WSGI/ASGI.
- `db/` Main app (models, views, templates, tests).
- `db_builder/` Data import/build scripts (uses SageMath; OEIS/data helpers).
- `services/` Pyro5 evaluation service used by the app.
- `templates/`, `static/` source assets; `staticfiles/` is the collected output.
- `deploy/` Docker Compose, Nginx templates, and related server configs.
- `tests/` Additional Sage-based tests; `manage.py` project entry.
- `.env` local settings (seeded from `env/.env.dev.example`).

## Build, Test, and Development Commands
- Prerequisites: SageMath installed (`sage` on PATH). Default DB is Postgres via `DATABASE_URL` in `.env`. SQLite is discouraged even for local development.
- `make install` — install deps, set up Postgres, run migrations, clone `../numberdb-data`, build core tables.
- `make run` — start the dev server at http://localhost:8000.
- `make test` — run Django tests.
- `make fetch_data` — clone/pull `../numberdb-data`.
- `make build_db_numbers` | `make build_db_all` — build data tables.
- `make migrations` | `make static` | `make update` — schema changes, collect static, housekeeping.
  Note: `.env` defines `PYTHON`, `PIP`, and `MANAGE` (typically `sage -python manage.py`).

## Coding Style & Naming Conventions
- Python 3, PEP 8, 4‑space indentation.
- `snake_case` for functions/variables/modules; `CamelCase` for classes.
- Keep views thin; move logic to helpers in `db/`. Name URL patterns `app:view` and prefer reverse lookups.

## Testing Guidelines
- Framework: Django `TestCase` (see `db/tests.py`) and Sage-based tests under `tests/`.
- Name tests `test_*.py`; class names end with `Test`.
- Ensure `../numberdb-data` exists (`make fetch_data`) before DB‑dependent tests.

## Commit & Pull Request Guidelines
- Commit style follows short, imperative messages (e.g., "add", "fix", "refactor"). Example: `fix: handle empty tags`.
- PRs should include: clear description, linked issues, test instructions, and screenshots for UI changes. Avoid committing secrets.

## Agent Commit Policy
- Commit regularly in small, logical chunks.
- Group related changes together (e.g., docs vs. config), avoid mixing unrelated changes.
- Use clear, conventional commit messages (e.g., `docs:`, `chore:`, `feat:`, `fix:`).
- After major edits (docs consolidation, config refactors), commit before proceeding to the next area.
- Never commit real secrets; `.env` remains untracked and generated from templates.

## Security & Configuration Tips
- Never commit real secrets. Create `.env` from `env/.env.dev.example` and adjust locally.
- Prefer Postgres locally and in production; avoid SQLite.
- Deployment config lives in `deploy/`. `make deploy` is server‑side and modifies system packages; do not run on a dev machine.
