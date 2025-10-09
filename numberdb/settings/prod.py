"""Production settings."""

from .base import *  # noqa

# Enforce secure defaults unless explicitly overridden
DEBUG = False if 'DEBUG' not in globals() else DEBUG

# Recommended security headers (can be tuned per deployment)
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True

