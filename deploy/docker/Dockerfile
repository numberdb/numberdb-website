# syntax=docker/dockerfile:1

# Pinned by digest, not by tag.
#
# This was `sagemath/sagemath:latest`, and on 2026-07-30 that tag moved from
# Sage 10.8 to 10.9. The cached base disappeared, the build failed at apt-get,
# and a routine rebuild would otherwise have swapped the Sage version silently
# -- during an outage, that is the last thing you want to discover.
#
# The tag is kept alongside the digest for readability; the digest is what
# actually resolves, so the tag moving cannot affect us.
#
# To upgrade deliberately:
#   1. docker pull sagemath/sagemath:<new-version>
#   2. docker inspect --format '{{index .RepoDigests 0}}' sagemath/sagemath:<new-version>
#   3. update both the tag and the digest below
#   4. rebuild, then run the test suite before deploying
#
# Sage 10.9, released 2026-05-04 (image published 2026-05-15).
FROM sagemath/sagemath:10.9@sha256:e068670ae5863b54b2550e72437ec637b0283acb0dc712c8584c124dbf44e667

ENV PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    POETRY_VIRTUALENVS_CREATE=false \
    DJANGO_SETTINGS_MODULE=numberdb.settings.prod

USER root
# System deps minimal; sagemath image already includes python + build tools
RUN apt-get update && apt-get install -y --no-install-recommends \
    git wget ca-certificates gosu \
    && rm -rf /var/lib/apt/lists/*
RUN git config --system --add safe.directory /numberdb-data

WORKDIR /app

# Install Python deps as 'sage' user for correct environment
COPY requirements.txt ./
RUN chown sage:sage requirements.txt
USER sage
RUN sage -pip install --no-cache-dir -r requirements.txt

USER root
# Copy project sources and ensure scripts are executable
COPY . .
RUN mkdir -p /app/docker \
    && cp deploy/docker/entrypoint.web.sh /app/docker/entrypoint.web.sh \
    && chmod +x /app/docker/entrypoint.web.sh
RUN chown -R sage:sage /app

# Socket directory for the sandboxed evaluator. Created here (rather than left
# to Docker) so the named volume inherits sage ownership on first mount -- the
# evaluator runs unprivileged and must be able to create the socket.
RUN mkdir -p /run/eval && chown sage:sage /run/eval

# Run container as root; entrypoint downgrades to 'sage' for app commands
USER root

EXPOSE 8000

# Default command (overridden in compose)
CMD ["gunicorn", "numberdb.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
