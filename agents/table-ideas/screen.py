"""Screens a proposal before a person reads it.

Prose in a prompt cannot catch these three, because a proposal that fails any
of them reads exactly like one that does not:

  * a family that does not exist, or is not called that by anyone
  * one the corpus already holds under a different name
  * one somebody already asked for

    from screen import source_names_it, already_here, already_asked, representable

Everything here reaches the outside through ordinary HTTP and the numberdb
package. Nothing writes.
"""

import json
import os
import re
import urllib.error
import urllib.parse
import urllib.request

TIMEOUT = 25


#: Words too common to identify anything. A family is recognised by the rest.
GENERIC = {'polynomial', 'polynomials', 'numbers', 'number', 'sequence',
           'sequences', 'function', 'functions', 'values', 'value', 'of',
           'the', 'and', 'in', 'for', 'a', 'constant', 'constants',
           'transcendent', 'transcendental', 'zeros', 'zeta', 'series',
           'coefficients', 'small', 'interesting', 'some'}


def _distinguishing(name):
    """The words in a name that could identify it.

    Hyphens are split, because the search splits them too: asking for
    "K-function" asks for "k" or "function", which is every table with the
    word "function" in its title.
    """
    return [w for w in re.findall(r"[a-z][a-z']+", name.lower().replace('-', ' '))
            if w not in GENERIC and len(w) > 2]


def use_socks_proxy_if_set():
    """Route Python through ALL_PROXY when it names a SOCKS proxy.

    curl honours ALL_PROXY; `urllib` and `http.client`, which the client and
    this module use, do not. On a network that reaches numberdb.org only
    through the proxy that difference is invisible and expensive: curl answers
    200, Python times out, and the corpus looks empty rather than unreachable.

    Idempotent, and a no-op when ALL_PROXY is unset or is not SOCKS.
    """
    global _PROXY_READY
    if _PROXY_READY:
        return
    url = os.environ.get('ALL_PROXY', '')
    if not url.startswith('socks'):
        _PROXY_READY = True
        return
    try:
        import socket
        import socks                                  # PySocks
    except ImportError:
        _PROXY_READY = True
        return
    parsed = urllib.parse.urlparse(url)
    socks.set_default_proxy(socks.SOCKS5, parsed.hostname, parsed.port or 1080,
                            rdns=url.startswith('socks5h'))
    socket.socket = socks.socksocket
    #urllib would otherwise try to speak HTTP to a SOCKS port.
    for name in ('ALL_PROXY', 'all_proxy', 'HTTP_PROXY', 'http_proxy',
                 'HTTPS_PROXY', 'https_proxy'):
        os.environ.pop(name, None)
    _PROXY_READY = True


#: Whether `use_socks_proxy_if_set` has already run.
_PROXY_READY = False


def source_names_it(name, url):
    """Does the cited source exist, and does it actually name this family?

    The check against inventing one. A proposal for the "Zhang-Liu
    polynomials" citing a Wikipedia article that says nothing of them fails
    here, and reads perfectly well otherwise.

    Returns a complaint, or None if the source names it.
    """
    use_socks_proxy_if_set()
    try:
        request = urllib.request.Request(
            url, headers={'User-Agent': 'numberdb-proposal-screen'})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            if answer.status != 200:
                return 'source answered %s: %s' % (answer.status, url)
            body = answer.read().decode('utf8', 'replace')
    except urllib.error.HTTPError as trouble:
        return 'source answered %s: %s' % (trouble.code, url)
    except Exception as trouble:                     # noqa: BLE001
        return 'source could not be read (%s): %s' % (
            type(trouble).__name__, url)

    text = re.sub(r'<[^>]+>', ' ', body).lower()
    text = ' '.join(text.split())

    #The distinguishing words, not the generic ones: "Bessel polynomials"
    #should be looked for as "bessel", since a page may write "polynomials of
    #Bessel type" or hyphenate.
    words = _distinguishing(name)
    if not words:
        return None
    missing = [w for w in words if w not in text]
    if missing:
        return ('the source does not mention %s -- either the name is not what '
                'this family is called, or the wrong page was cited: %s'
                % (', '.join(missing), url))
    return None


def already_here(name, client=None):
    """Tables the corpus already holds that look like this one.

    Search is weak on its own -- a family can be here under another name -- so
    this searches the words of the name separately and returns everything it
    finds for a person to glance at, rather than answering yes or no.
    """
    import numberdb

    found = {}
    #Distinguishing words only, and not the full name: the search ORs the words
    #of whatever it is given, so asking for "Polygamma function" returns every
    #table with "function" in its title. The first version of this reported
    #that the Bessel polynomials matched "transcendent" -- noise a reader has
    #to wade through to find the one real collision.
    terms = _distinguishing(name)
    if not terms:
        #Every word is generic, so there is nothing to search on that would
        #not match half the corpus. Say so; a person can look by hand.
        return ['(no distinguishing word in %r -- search the corpus by hand)'
                % name]
    use_socks_proxy_if_set()
    for term in terms:
        try:
            results = numberdb.search_text(term, client=client)
        except Exception as trouble:                 # noqa: BLE001
            #Never silently. This returned [] for every name once, because
            #Python ignores the SOCKS proxy that curl honours and the corpus
            #was simply unreachable -- and [] reads exactly like "nothing
            #similar is here", which is the opposite of what was known. A
            #failed question and an empty answer must not look the same.
            return ['(could not ask the corpus: %s: %s)'
                    % (type(trouble).__name__, trouble)]
        for table in getattr(results, 'tables', []):
            found[table.title] = term
    return sorted('%s (matched %r)' % (title, term)
                  for title, term in found.items())


def already_asked(name, repository='numberdb/numberdb-data'):
    """Issues, open or closed, that already ask for this.

    Closed ones matter as much: a closed issue means the table exists, and
    proposing it again wastes the next person's day.
    """
    use_socks_proxy_if_set()
    words = [w for w in re.findall(r"[A-Za-z][A-Za-z'-]+", name)
             if len(w) > 4]
    if not words:
        return []
    query = urllib.parse.quote(' '.join(words[:3]))
    url = ('https://api.github.com/search/issues?q=repo:%s+in:title+%s'
           % (repository, query))
    try:
        request = urllib.request.Request(
            url, headers={'User-Agent': 'numberdb-proposal-screen',
                          'Accept': 'application/vnd.github+json'})
        with urllib.request.urlopen(request, timeout=TIMEOUT) as answer:
            payload = json.load(answer)
    except Exception as trouble:                     # noqa: BLE001
        return ['could not ask GitHub (%s)' % type(trouble).__name__]
    return ['#%d [%s] %s' % (item['number'], item['state'], item['title'])
            for item in payload.get('items', [])[:6]]


#: What a table can hold. Anything else is not a table here, however
#: interesting -- say so in the proposal rather than proposing it.
TYPES = ('Z', 'Q', 'R', 'C', 'Qp', 'Z[]', 'Q[]', '*R')
MOST_VARIABLES = 6


def representable(kind, parameters_are_finite, variables=1):
    """Can this be a table at all?

    Three ways it cannot: the value is not one of the types the database
    holds; the parameter runs over something with no canonical enumeration --
    numberdb-data#121 asks for Lagrange polynomials over general point sets,
    and there is nothing to look a value up by; or the polynomials have more
    variables than the renaming-invariant search key can handle.
    """
    complaints = []
    if kind not in TYPES:
        complaints.append('type %r is not one of %s'
                          % (kind, ', '.join(TYPES)))
    if not parameters_are_finite:
        complaints.append('the parameter has no canonical enumeration, so '
                          'there is nothing to look a value up by')
    if variables > MOST_VARIABLES:
        complaints.append('%d variables: more than %d is refused, because the '
                          'key that matches polynomials differing only in '
                          'variable names is found by trying permutations'
                          % (variables, MOST_VARIABLES))
    return complaints
