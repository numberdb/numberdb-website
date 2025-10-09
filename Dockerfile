# syntax=docker/dockerfile:1
FROM sagemath/sagemath:latest

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    DJANGO_SETTINGS_MODULE=numberdb.settings

USER root
# System deps minimal; sagemath image already includes python + build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget ca-certificates \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python deps as 'sage' user for correct environment
COPY requirements.txt ./
RUN chown sage:sage requirements.txt
USER sage
RUN sage -pip install --no-cache-dir -r requirements.txt

USER root
# Copy project sources and ensure scripts are executable
COPY . .
RUN chmod +x docker/entrypoint.web.sh
RUN chown -R sage:sage /app

# Run container as root; entrypoint downgrades to 'sage' for app commands
USER root

EXPOSE 8000

# Default command (overridden in compose)
CMD ["gunicorn", "numberdb.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
