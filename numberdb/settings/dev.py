"""Development settings."""

from .base import *  # noqa

# Prefer HTTP for local dev unless overridden
if 'ACCOUNT_DEFAULT_HTTP_PROTOCOL' not in globals():
    ACCOUNT_DEFAULT_HTTP_PROTOCOL = 'http'

# Default to DEBUG True if not set in env
try:
    DEBUG
except NameError:
    DEBUG = True

