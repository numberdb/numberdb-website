"""One exception hierarchy, so callers can catch the package rather than a list.

Kept in its own module because both the transport and the decoder raise, and
neither should have to import the other to share a base class.
"""

__all__ = ['NumberDBError', 'TransportError', 'RateLimitError', 'UnauthorizedError',
           'ConflictError', 'DisagreementError', 'TooBigError',
           'UnsupportedNumberError']


class NumberDBError(Exception):
    """Base for everything this package raises.

    ``except numberdb.NumberDBError`` catches all of it. Every other exception
    here inherits from this, so adding a new failure mode later cannot silently
    escape a caller's handler.
    """


class TransportError(NumberDBError):
    """The server could not be reached, or answered with something unusable."""


class RateLimitError(TransportError):
    """Too many requests.

    ``retry_after`` is in seconds when the server said, otherwise None. An API
    key raises the limit -- see https://numberdb.org/help#section-api.
    """

    def __init__(self, message, retry_after=None):
        super().__init__(message)
        self.retry_after = retry_after


class UnauthorizedError(TransportError):
    """The API key was rejected."""


class UnsupportedNumberError(NumberDBError):
    """A number this version of the package has no rule for.

    Usually means the server is newer than the package, and upgrading is the
    fix. Raised rather than guessed at: a wrong guess about a number is worse
    than an honest refusal.

    Reaching this does not spoil a whole search. Results are decoded on demand,
    so an unknown kind costs you that one value and nothing else -- the rest of
    the results, and that result's own ``exact_text``, remain usable.
    """


class ConflictError(NumberDBError):
    """Somebody changed the table while you were writing it.

    Carries the conflicting entries when the server names them, so a script can
    report which values two people disagreed about rather than only that they
    did.
    """

    def __init__(self, message, conflicts=None, head=None):
        super().__init__(message)
        self.conflicts = list(conflicts or [])
        self.head = head


class TooBigError(NumberDBError):
    """The table is over a size limit and nothing was written.

    A program is refused where a person would be warned and allowed to
    continue: a warning shown to nobody is not a limit. State the reason in a
    "Size exception" line under Data properties if the size is deliberate.
    """


class DisagreementError(NumberDBError):
    """A computed value cannot stand beside the one already stored.

    Raised as soon as it is found, so a run whose first entry already
    contradicts the table stops having spent one entry rather than a day.
    Nothing further is sent; anything a long run had already sent is one
    revision, and revertible in a click.

    ``verdict`` is why -- values that cannot both be true, or a value that
    would replace stored digits with fewer. The message names the argument
    that means "yes, I meant it", so it need not be known in advance.
    """

    def __init__(self, message, identity='', stored='', produced='',
                 verdict=''):
        super().__init__(message)
        self.identity = identity
        self.stored = stored
        self.produced = produced
        self.verdict = verdict
