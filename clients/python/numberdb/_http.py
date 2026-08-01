"""Talking to numberdb.org.

Configuration lives on a ``Client`` rather than in module globals: globals are
not thread-safe, cannot be varied between two servers in one process, and make
tests order-dependent. The module-level functions in ``__init__`` keep the
one-liner case easy by delegating to a default client.

The opener is injectable for the same reason -- it lets the package be tested
without a network or a server, which is why these tests run anywhere.
"""

import json
import os
import urllib.error
import urllib.parse
import urllib.request

from ._errors import NumberDBError, RateLimited, TransportError, Unauthorized

__all__ = ['Client', 'DEFAULT_BASE_URL', 'DEFAULT_TIMEOUT']

DEFAULT_BASE_URL = 'https://numberdb.org/'
DEFAULT_TIMEOUT = 30

#: Sent so the server can tell versions apart in its logs, and so a future
#: change of wire format can be negotiated rather than guessed at.
API_VERSION = '1'


class Client:
    """A configured connection to a NumberDB server.

    ``api_key`` raises the rate limit. It defaults to ``$NUMBERDB_API_KEY``, so
    a key need not be written into a worksheet -- a shared notebook should not
    carry its author's credentials.

    ``base_url`` defaults to ``$NUMBERDB_URL`` and then to numberdb.org, which
    is what lets the package be pointed at a development server.
    """

    def __init__(self, api_key=None, base_url=None, timeout=None, opener=None):
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._opener = opener or urllib.request.urlopen

    @property
    def base_url(self):
        """Always ending in a slash, which is not cosmetic.

        urljoin treats a final segment without a trailing slash as a file to be
        replaced, so a base of 'https://example.org/numberdb' would send
        requests to 'https://example.org/api/search' -- the path prefix
        silently dropped, and quite possibly a different application answering.
        Anyone hosting NumberDB under a sub-path behind a proxy would hit this,
        and would see a 404 rather than anything pointing at the cause.
        """
        configured = self._base_url or os.environ.get('NUMBERDB_URL',
                                                      DEFAULT_BASE_URL)
        return configured if configured.endswith('/') else configured + '/'

    @property
    def api_key(self):
        return self._api_key or os.environ.get('NUMBERDB_API_KEY') or None

    @property
    def timeout(self):
        return self._timeout if self._timeout is not None else DEFAULT_TIMEOUT

    def __repr__(self):
        return 'Client(base_url=%r, api_key=%s)' % (
            self.base_url, 'set' if self.api_key else None)

    def request(self, path, parameters):
        """GET ``path`` with ``parameters``, returning parsed JSON."""
        url = urllib.parse.urljoin(self.base_url, path)
        query = urllib.parse.urlencode(
            {k: v for k, v in parameters.items() if v is not None})
        headers = {'Accept': 'application/json',
                   'User-Agent': _user_agent(),
                   'X-NumberDB-API-Version': API_VERSION}
        key = self.api_key
        if key:
            headers['Authorization'] = 'Bearer %s' % (key,)

        http_request = urllib.request.Request('%s?%s' % (url, query),
                                              headers=headers)
        try:
            with self._opener(http_request, timeout=self.timeout) as response:
                body = response.read()
        except urllib.error.HTTPError as error:
            raise self._from_status(error)
        except urllib.error.URLError as error:
            raise TransportError('could not reach %s: %s'
                                 % (url, error.reason))

        try:
            payload = json.loads(body.decode('utf8'))
        except (UnicodeDecodeError, ValueError):
            raise TransportError('%s did not return JSON' % (url,))
        if not isinstance(payload, dict):
            raise TransportError('%s returned %s, expected an object'
                                 % (url, type(payload).__name__))
        #Both API endpoints report failure this way rather than by status.
        if 'error' in payload:
            raise NumberDBError(str(payload['error']))
        return payload

    def _from_status(self, error):
        if error.code == 429:
            retry_after = error.headers.get('Retry-After')
            try:
                retry_after = int(retry_after)
            except (TypeError, ValueError):
                retry_after = None
            detail = ('too many requests'
                      if retry_after is None
                      else 'too many requests; retry in %ds' % (retry_after,))
            if not self.api_key:
                detail += ('. Anonymous use is limited -- an API key raises '
                           'the limit: https://numberdb.org/help#section-api')
            return RateLimited(detail, retry_after)
        if error.code in (401, 403):
            return Unauthorized('the server rejected the API key (HTTP %d)'
                                % (error.code,))
        return TransportError('HTTP %d from %s' % (error.code, error.url))


def _user_agent():
    from . import __version__
    return 'numberdb-python/%s' % (__version__,)
