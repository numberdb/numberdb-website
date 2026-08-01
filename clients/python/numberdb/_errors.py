"""One exception hierarchy, so callers can catch the package rather than a list.

Kept in its own module because both the transport and the decoder raise, and
neither should have to import the other to share a base class.
"""

__all__ = ['NumberDBError', 'TransportError', 'RateLimited', 'Unauthorized',
           'UnsupportedNumber']


class NumberDBError(Exception):
    """Base for everything this package raises.

    ``except numberdb.NumberDBError`` catches all of it. Every other exception
    here inherits from this, so adding a new failure mode later cannot silently
    escape a caller's handler.
    """


class TransportError(NumberDBError):
    """The server could not be reached, or answered with something unusable."""


class RateLimited(TransportError):
    """Too many requests.

    ``retry_after`` is in seconds when the server said, otherwise None. An API
    key raises the limit -- see https://numberdb.org/help#section-api.
    """

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class Unauthorized(TransportError):
    """The API key was rejected."""


class UnsupportedNumber(NumberDBError):
    """A number this version of the package has no rule for.

    Usually means the server is newer than the package, and upgrading is the
    fix. Raised rather than guessed at: a wrong guess about a number is worse
    than an honest refusal.

    Reaching this does not spoil a whole search. Results are decoded on demand,
    so an unknown kind costs you that one value and nothing else -- the rest of
    the results, and that result's own ``exact_text``, remain usable.
    """
