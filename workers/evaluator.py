"""Sandboxed evaluator for advanced-search expressions.

Replaces ``workers/eval.py`` (SafeEval over Pyro5). See
``docs/design/eval-sandbox.md``.

Shape of the thing:

* One long-lived parent imports Sage once, then serves a Unix domain socket.
* Each request is evaluated in a **forked child** that handles exactly one
  expression and exits (``workers/sandbox.py``). Nothing carries between
  requests.
* The parent owns the socket and every deadline. The child never touches it.
* Wire format is JSON in both directions (``workers/protocol.py``). No pickle.

The container this runs in has ``network_mode: none``, so the socket is the
only channel in or out. Even full code execution inside a child cannot reach
Postgres, the Docker API, the internet, or Tailscale peers.

Run::

    sage -python workers/evaluator.py [socket-path]
"""

import os
import socket
import stat
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.protocol import (  # noqa: E402
    ProtocolError,
    recv_frame,
    send_frame,
)
from workers.sandbox import run_isolated  # noqa: E402
from workers.expression_validator import (  # noqa: E402
    ExpressionRejected,
    validate_expression,
)

DEFAULT_SOCKET_PATH = '/run/eval/evaluator.sock'

#: Wall-clock budget for one evaluation, enforced by the parent.
EVALUATION_TIMEOUT_SECONDS = 5.0

#: Budget for reading a request off the socket. Separate from evaluation.
REQUEST_TIMEOUT_SECONDS = 10.0

DEFAULT_MAX_NUMBERS = 1000


def build_namespace():
    """The allow-listed evaluation environment.

    This mapping is the single source of truth: the validator derives permitted
    names from its keys, so the two cannot drift apart. Adding a function here
    makes it usable; removing it makes it unusable. Nothing else is reachable,
    and ``__builtins__`` is emptied at evaluation time.
    """
    from sage.all import (
        pi, e, I, infinity, golden_ratio, euler_gamma, catalan,
        sqrt, exp, log, sin, cos, tan, arcsin, arccos, arctan,
        sinh, cosh, tanh, floor, ceil, abs_symbolic,
        factorial, binomial, gcd, lcm, bernoulli, zeta, gamma,
        prime_pi, next_prime, previous_prime, is_prime, divisors, sigma,
        euler_phi, moebius, continued_fraction, N, numerical_approx,
        Integer, RealNumber, ellipsis_range, ellipsis_iter,
    )
    from sage.rings.all import (
        ZZ, QQ, RR, CC, RIF, CIF, RBF, CBF, Qp,
        RealField, RealIntervalField, RealBallField,
        ComplexField, ComplexIntervalField, ComplexBallField,
        PolynomialRing,
    )

    namespace = {
        # constants
        'pi': pi, 'e': e, 'I': I, 'i': I, 'infinity': infinity, 'oo': infinity,
        'golden_ratio': golden_ratio, 'euler_gamma': euler_gamma,
        'catalan': catalan,
        # elementary functions
        'sqrt': sqrt, 'exp': exp, 'log': log,
        'sin': sin, 'cos': cos, 'tan': tan,
        'arcsin': arcsin, 'arccos': arccos, 'arctan': arctan,
        'sinh': sinh, 'cosh': cosh, 'tanh': tanh,
        'floor': floor, 'ceil': ceil,
        # number theory / combinatorics
        'factorial': factorial, 'binomial': binomial,
        'gcd': gcd, 'lcm': lcm, 'bernoulli': bernoulli,
        'zeta': zeta, 'gamma': gamma,
        'prime_pi': prime_pi, 'next_prime': next_prime,
        'previous_prime': previous_prime, 'is_prime': is_prime,
        'divisors': divisors, 'sigma': sigma, 'euler_phi': euler_phi,
        'moebius': moebius, 'continued_fraction': continued_fraction,
        'N': N, 'numerical_approx': numerical_approx,
        # rings and fields
        'ZZ': ZZ, 'QQ': QQ, 'RR': RR, 'CC': CC,
        'RIF': RIF, 'CIF': CIF, 'RBF': RBF, 'CBF': CBF, 'Qp': Qp,
        'RealField': RealField, 'RealIntervalField': RealIntervalField,
        'RealBallField': RealBallField, 'ComplexField': ComplexField,
        'ComplexIntervalField': ComplexIntervalField,
        'ComplexBallField': ComplexBallField, 'PolynomialRing': PolynomialRing,
        # safe builtins, provided explicitly since __builtins__ is emptied
        'abs': abs, 'len': len, 'min': min, 'max': max, 'sum': sum,
        'range': range, 'sorted': sorted, 'list': list, 'tuple': tuple,
        'set': set, 'dict': dict, 'int': int, 'bool': bool,
        # emitted by Sage's preparser
        'Integer': Integer, 'RealNumber': RealNumber,
        'ellipsis_range': ellipsis_range, 'ellipsis_iter': ellipsis_iter,
        'Ellipsis': Ellipsis,
    }
    namespace.pop('abs_symbolic', None)
    return namespace


def _flatten(value, parent_key='', separator=', ', depth=0):
    """Walk a nested result into ``(parameter_label, number)`` pairs.

    Mirrors the old ``SafeEval._parse_numbers``: a dict contributes its keys to
    the parameter label, so ``{n: 2^n for n in [1..10]}`` yields labels ``n``
    rather than a bare list of values. Returns ``(pairs, unconvertible_labels)``.
    """
    from utils.number_json import encode_number, UnsupportedNumber
    from sage.rings.all import RIF, CIF

    if depth > 20:
        return [], [parent_key or '?']

    if isinstance(value, dict):
        pairs, failed = [], []
        prefix = (parent_key + separator) if parent_key else ''
        for key, item in value.items():
            sub_pairs, sub_failed = _flatten(
                item, parent_key=prefix + str(key),
                separator=separator, depth=depth + 1)
            pairs += sub_pairs
            failed += sub_failed
        return pairs, failed

    if isinstance(value, (list, tuple, set, range)) or hasattr(value, '__next__'):
        pairs, failed = [], []
        for item in value:
            sub_pairs, sub_failed = _flatten(
                item, parent_key=parent_key,
                separator=separator, depth=depth + 1)
            pairs += sub_pairs
            failed += sub_failed
        return pairs, failed

    # A leaf. p-adics and polynomials are carried as themselves; everything
    # else is coerced to a real, then complex, interval.
    try:
        return [(parent_key, encode_number(value))], []
    except (UnsupportedNumber, AttributeError, TypeError, ValueError):
        pass

    for ring in (RIF, CIF):
        try:
            return [(parent_key, encode_number(ring(value)))], []
        except (UnsupportedNumber, AttributeError, TypeError, ValueError):
            continue

    return [], [parent_key]


def _pluralize(word, count):
    return word if count == 1 else word + 's'


def evaluate_search_program(source, max_numbers=DEFAULT_MAX_NUMBERS):
    """Validate, evaluate and encode one expression. Runs inside a forked child."""
    from sage.repl.preparse import preparse

    messages = []
    namespace = build_namespace()

    try:
        source_python = preparse(source)
    except Exception as error:  # noqa: BLE001
        return {'numbers': None, 'messages': [{
            'tags': 'alert-danger',
            'text': 'Parsing error: %s' % (error,)}]}

    try:
        validate_expression(source_python, namespace)
    except ExpressionRejected as error:
        return {'numbers': None, 'messages': [{
            'tags': 'alert-danger', 'text': str(error)}]}

    try:
        # __builtins__ emptied: names come only from the allow-listed namespace.
        evaluated = eval(source_python, {'__builtins__': {}}, dict(namespace))
    except Exception as error:  # noqa: BLE001
        return {'numbers': None, 'messages': [{
            'tags': 'alert-danger',
            'text': 'Error: %s' % (error,)}]}

    pairs, failed = _flatten(evaluated)

    if len(pairs) > max_numbers:
        pairs = pairs[:max_numbers]
        messages.append({
            'tags': 'alert-warning',
            'text': 'We only check the first %s given numbers.' % (max_numbers,)})

    if failed:
        if len(failed) <= 100 and all(label != '' for label in failed):
            text = ('%s %s with the following parameters could not be converted '
                    'into real intervals: %s.'
                    % (len(failed), _pluralize('number', len(failed)),
                       '; '.join(failed)))
        else:
            text = ('%s %s could not be converted into real intervals.'
                    % (len(failed), _pluralize('number', len(failed))))
        messages.append({'tags': 'alert-danger', 'text': text})

    return {'numbers': [{'param': label, 'number': record}
                        for label, record in pairs],
            'messages': messages}


def handle_request(request):
    """Dispatch one decoded request. Returns the reply payload."""
    if not isinstance(request, dict):
        return {'ok': False, 'error': 'bad_request', 'messages': []}

    if request.get('op') == 'ping':
        return {'ok': True, 'pong': request.get('echo')}

    if request.get('op') != 'search_program':
        return {'ok': False, 'error': 'unknown_op', 'messages': []}

    source = request.get('source')
    if not isinstance(source, str):
        return {'ok': False, 'error': 'bad_request', 'messages': []}

    try:
        max_numbers = int(request.get('max_numbers', DEFAULT_MAX_NUMBERS))
    except (TypeError, ValueError):
        max_numbers = DEFAULT_MAX_NUMBERS
    max_numbers = max(1, min(max_numbers, DEFAULT_MAX_NUMBERS))

    outcome = run_isolated(
        lambda: evaluate_search_program(source, max_numbers),
        timeout=EVALUATION_TIMEOUT_SECONDS,
    )

    if outcome.ok:
        value = outcome.value or {}
        return {'ok': True,
                'numbers': value.get('numbers'),
                'messages': value.get('messages', [])}

    if outcome.error == 'timeout':
        text = 'Timed out (%.0f seconds).' % (EVALUATION_TIMEOUT_SECONDS,)
    elif outcome.error == 'output_too_large':
        text = 'That expression produced too much output.'
    else:
        text = 'The expression could not be evaluated.'
    # outcome.detail deliberately stays out of the user-visible message; it can
    # carry internals. It is logged instead.
    if outcome.detail:
        print('evaluator: %s: %s' % (outcome.error, outcome.detail),
              file=sys.stderr, flush=True)
    return {'ok': False, 'error': outcome.error, 'numbers': None,
            'messages': [{'tags': 'alert-danger', 'text': text}]}


def serve(socket_path=DEFAULT_SOCKET_PATH):
    """Listen on ``socket_path`` and serve requests until interrupted."""
    directory = os.path.dirname(socket_path)
    if directory:
        os.makedirs(directory, exist_ok=True)
    if os.path.exists(socket_path):
        os.unlink(socket_path)

    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(socket_path)
    # The socket is the only channel into this container; the sharing volume is
    # already restricted to web + evaluator, so allow both to use it.
    os.chmod(socket_path, stat.S_IRUSR | stat.S_IWUSR |
             stat.S_IRGRP | stat.S_IWGRP | stat.S_IROTH | stat.S_IWOTH)
    server.listen(16)

    print('evaluator: warming Sage...', flush=True)
    build_namespace()
    print('evaluator: listening on %s' % (socket_path,), flush=True)

    while True:
        try:
            connection, _ = server.accept()
        except InterruptedError:
            continue
        except OSError:
            break
        try:
            request = recv_frame(connection, timeout=REQUEST_TIMEOUT_SECONDS)
            send_frame(connection, handle_request(request))
        except ProtocolError as error:
            print('evaluator: protocol error: %s' % (error,),
                  file=sys.stderr, flush=True)
        except Exception:  # noqa: BLE001 - the loop must never die
            traceback.print_exc()
        finally:
            try:
                connection.close()
            except OSError:
                pass


if __name__ == '__main__':
    serve(sys.argv[1] if len(sys.argv) > 1 else DEFAULT_SOCKET_PATH)
