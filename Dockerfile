# syntax=docker/dockerfile:1
FROM sagemath/sagemath:latest

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    DJANGO_SETTINGS_MODULE=numberdb.settings

USER root
# System deps minimal; sagemath image already includes python + build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git \
    && rm -rf /var/lib/apt/lists/*

# Ensure working dir writable by 'sage'
RUN mkdir -p /app && chown -R sage:sage /app

USER sage
WORKDIR /app

COPY requirements.txt ./
RUN sage -pip install --no-cache-dir -r requirements.txt

# Copy project
COPY . .

# Entrypoint script for web service
RUN chmod +x docker/entrypoint.web.sh || true

EXPOSE 8000

# Default command (overridden in compose)
CMD ["gunicorn", "numberdb.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
