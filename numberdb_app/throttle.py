"""Rate limiting for the API.

The API is the cheapest way to make the server work hard: ``/api/search``
evaluates an expression in the sandbox and then queries. Without a limit, one
script can occupy the evaluator indefinitely, and the site runs on a 1 GB
machine that has no headroom to absorb it.

Anonymous callers get a small allowance, keyed callers a larger one. The point
is not to charge for access -- it is that a caller who identifies themselves
can be told when something is wrong and, if necessary, have their key revoked,
whereas an anonymous flood can only be absorbed or dropped.

Only ``/api/*`` is limited. The site's own pages, including advanced search,
are rendered server-side and never call the API, so ordinary browsing is
unaffected.

The counter is a fixed window in Django's cache. That is deliberately simple
and has two consequences worth knowing: a caller can spend the whole allowance
at the end of one window and again at the start of the next, and with the
default local-memory cache the counts live in the worker process, so they reset
on deploy and would not be shared if a second worker were ever added. Both are
acceptable for keeping one script from monopolising the machine; neither would
be acceptable for billing.
"""

import functools
import math
import time

from django.conf import settings
from django.core.cache import cache
from django.http import JsonResponse

__all__ = ['rate_limited', 'requester_of', 'charge', 'batch_cost']


def batch_cost(size):
    """What a batch of ``size`` numbers is worth, in units.

    One for the request and half for each number: a batch of a hundred costs
    fifty-one rather than a hundred, so batching is worth doing, but it is not
    free either -- the server still parses and queries each one.
    """
    return int(math.ceil(1 + 0.5 * max(size, 0)))

#: Requests per window for a caller who has not identified themselves.
ANONYMOUS_LIMIT = 60

#: Requests per window for a caller with a valid API key, or a logged-in
#: session.
IDENTIFIED_LIMIT = 1000

#: Seconds. One hour, so Retry-After is a meaningful thing to say.
WINDOW_SECONDS = 3600


def _limits():
    return (getattr(settings, 'NUMBERDB_ANONYMOUS_RATE_LIMIT',
                    ANONYMOUS_LIMIT),
            getattr(settings, 'NUMBERDB_IDENTIFIED_RATE_LIMIT',
                    IDENTIFIED_LIMIT),
            getattr(settings, 'NUMBERDB_RATE_LIMIT_WINDOW', WINDOW_SECONDS))


def _bearer_token(request):
    header = request.headers.get('Authorization', '')
    if header.startswith('Bearer '):
        return header[len('Bearer '):].strip()
    #Accepted as well because it is easier to set in a browser console or a
    #curl one-liner, and the token is no more exposed either way.
    return request.headers.get('X-API-Key', '').strip() or None


def _client_ip(request):
    """The caller's address, trusting the proxy only for its own hop.

    nginx sits in front and sets X-Forwarded-For. Only the last entry is
    trustworthy -- anything earlier is whatever the client chose to send, and
    treating that as identity would let a caller reset their own counter by
    inventing an address.
    """
    forwarded = request.META.get('HTTP_X_FORWARDED_FOR', '')
    if forwarded:
        return forwarded.split(',')[-1].strip()
    return request.META.get('REMOTE_ADDR', '') or 'unknown'


def requester_of(request):
    """Who is asking, and what they are allowed.

    Returns ``(scope, limit, api_key)``. ``scope`` is what the counter is kept
    against, so two users never share an allowance and one user's key is not
    pooled with their session.
    """
    anonymous_limit, identified_limit, _ = _limits()

    token = _bearer_token(request)
    if token:
        from .models import ApiKey
        key = ApiKey.authenticate(token)
        if key is not None:
            return 'key:%d' % (key.pk,), identified_limit, key
        #A token that is present but wrong is refused rather than quietly
        #demoted to the anonymous allowance, so a stale key is visible to its
        #owner instead of looking like a slow day.
        return None, None, False

    user = getattr(request, 'user', None)
    if user is not None and user.is_authenticated:
        return 'user:%d' % (user.pk,), identified_limit, None

    return 'ip:%s' % (_client_ip(request),), anonymous_limit, None


def _consume(scope, limit, window, cost=1):
    """Count this request. Returns (allowed, retry_after).

    ``cost`` is what the request is worth. A batch counts for more than one, so
    that batching saves handshakes and server work without turning the limit
    into a formality.
    """
    now = int(time.time())
    window_start = now - (now % window)
    cache_key = 'numberdb-throttle:%s:%d' % (scope, window_start)

    #add() only sets it if absent, which starts the window; incr() then counts
    #within it. Doing it the other way round would lose the expiry.
    cache.add(cache_key, 0, window)
    try:
        used = cache.incr(cache_key, cost)
    except ValueError:
        #The entry expired between add and incr.
        cache.set(cache_key, cost, window)
        used = cost

    if used > limit:
        return False, window_start + window - now
    return True, None


def charge(request, extra):
    """Bill a caller for work the decorator could not have foreseen.

    A batch is worth more than a single lookup, and how much more is only
    known once it has been parsed. The base unit was taken on the way in; this
    adds the rest.

    Deliberately does not refuse the request in hand -- it has already been
    done, and refusing after the fact would waste the work rather than save it.
    The charge lands on the window, so the next request is what pays.
    """
    if extra <= 0:
        return
    scope, limit, _ = requester_of(request)
    if scope is None:
        return
    _, _, window = _limits()
    _consume(scope, limit, window, int(extra))


def rate_limited(view):
    """Limit an API view by caller.

    Every request costs one unit up front. A view that turns out to be worth
    more calls ``charge`` once it knows -- a batch cannot be priced before it
    has been read, and the decorator runs first.
    """

    @functools.wraps(view)
    def guarded(request, *args, **kwargs):
        scope, limit, key = requester_of(request)

        #Left on the request so the activity log can say which key was asking
        #without authenticating the token a second time. Set before the
        #refusals below, so a request that is turned away is still attributed.
        request.numberdb_api_key = key if key not in (None, False) else None

        if key is False:
            return JsonResponse(
                {'error': 'Invalid API key.',
                 'help': '%s#section-api' % (settings.SITE_HELP_URL
                                             if hasattr(settings, 'SITE_HELP_URL')
                                             else '/help',)},
                status=403)

        _, _, window = _limits()
        allowed, retry_after = _consume(scope, limit, window)
        if not allowed:
            detail = ('Rate limit exceeded (%d requests per %d minutes).'
                      % (limit, window // 60))
            if scope.startswith('ip:'):
                detail += (' An API key raises this limit; see /help#section-api.')
            response = JsonResponse({'error': detail,
                                     'retry_after': retry_after}, status=429)
            response['Retry-After'] = str(retry_after)
            return response

        if key is not None:
            #Recorded so an owner can see a key is in use, and so an abandoned
            #one is identifiable. Written without a full save to keep an extra
            #round trip off every API call.
            from django.utils import timezone
            from .models import ApiKey
            ApiKey.objects.filter(pk=key.pk).update(last_used=timezone.now())

        return view(request, *args, **kwargs)

    return guarded
