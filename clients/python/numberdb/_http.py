"""Talking to numberdb.org.

Anonymous requests are rate limited. An API key raises the limit, and is sent
as a bearer token:

    export NUMBERDB_API_KEY=...          # or numberdb.api_key = '...'

The key is read from the environment by default so it need not be written into
a worksheet -- a notebook that gets shared should not carry its author's key.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

__all__ = ['NumberDBError', 'RateLimited', 'Unauthorized', 'request']

DEFAULT_BASE_URL = 'https://numberdb.org/'
TIMEOUT_SECONDS = 30


class NumberDBError(Exception):
    """The server could not be reached, or refused the request."""


class RateLimited(NumberDBError):
    """Too many requests.

    ``retry_after`` is seconds, when the server said. An API key raises the
    limit; see https://numberdb.org/help#section-api.
    """

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class Unauthorized(NumberDBError):
    """The API key was rejected."""


def base_url():
    """Overridable, so the package can be pointed at a development server."""
    return os.environ.get('NUMBERDB_URL', DEFAULT_BASE_URL)


def api_key():
    from . import api_key as configured
    return configured or os.environ.get('NUMBERDB_API_KEY') or None


def request(path, parameters, urlopen=urllib.request.urlopen):
    """GET ``path`` with ``parameters``, returning parsed JSON.

    ``urlopen`` is injectable so the package can be tested without a network
    and without a live server.
    """
    url = urllib.parse.urljoin(base_url(), path)
    query = urllib.parse.urlencode(
        {k: v for k, v in parameters.items() if v is not None})
    headers = {'Accept': 'application/json',
               'User-Agent': _user_agent()}
    key = api_key()
    if key:
        headers['Authorization'] = 'Bearer %s' % (key,)

    http_request = urllib.request.Request('%s?%s' % (url, query),
                                          headers=headers)
    try:
        with urlopen(http_request, timeout=TIMEOUT_SECONDS) as response:
            body = response.read()
    except urllib.error.HTTPError as error:
        raise _from_status(error)
    except urllib.error.URLError as error:
        raise NumberDBError('could not reach %s: %s' % (url, error.reason))

    try:
        return json.loads(body.decode('utf8'))
    except (UnicodeDecodeError, ValueError):
        raise NumberDBError('%s did not return JSON' % (url,))


def _from_status(error):
    if error.code == 429:
        retry_after = error.headers.get('Retry-After')
        try:
            retry_after = int(retry_after)
        except (TypeError, ValueError):
            retry_after = None
        detail = ('too many requests'
                  if retry_after is None
                  else 'too many requests; retry in %ds' % (retry_after,))
        if not api_key():
            detail += ('. Anonymous use is limited -- an API key raises the '
                       'limit: https://numberdb.org/help#section-api')
        return RateLimited(detail, retry_after)
    if error.code in (401, 403):
        return Unauthorized('the server rejected the API key (HTTP %d)'
                            % (error.code,))
    return NumberDBError('HTTP %d from %s' % (error.code, error.url))


def _user_agent():
    from . import __version__
    return 'numberdb-python/%s' % (__version__,)
