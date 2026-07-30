"""Django-side client for the sandboxed evaluator.

Replaces the Pyro proxy in ``numberdb_app/api.py``. Returns the same
``(param_numbers, messages)`` shape the old code expected, so the call site
barely changes:

* ``param_numbers`` -- list of ``(parameter_label, sage_number)`` pairs, or
  ``None`` if the expression could not be evaluated.
* ``messages`` -- list of ``{'tags': ..., 'text': ...}`` dicts for the user.

The evaluator lives in a container with no network at all; the only channel is
a Unix socket on a shared volume. Nothing here unpickles: numbers arrive as
JSON records and are rebuilt through a fixed dispatch table in
``utils.number_json``.

The evaluator being unreachable is normal and must stay non-fatal -- the search
page has always degraded gracefully when it is down.
"""

import os
import socket

from workers.protocol import ProtocolError, recv_frame, send_frame
from utils.number_json import decode_number, UnsupportedNumber

__all__ = ['EvaluatorUnavailable', 'evaluate_search_program']

SOCKET_PATH = os.environ.get('EVALUATOR_SOCKET', '/run/eval/evaluator.sock')

#: Must exceed the evaluator's own evaluation budget, so its structured
#: timeout message wins over a blunt connection timeout here.
CLIENT_TIMEOUT_SECONDS = 20.0

_UNAVAILABLE_MESSAGE = {
    'tags': 'alert-danger',
    'text': ('Error: The advanced search server is currently not running and '
             'has to be restarted. We apologize.'),
}


class EvaluatorUnavailable(Exception):
    """The evaluator could not be reached."""


def _request(payload, socket_path=None, timeout=CLIENT_TIMEOUT_SECONDS):
    path = socket_path or SOCKET_PATH
    connection = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    connection.settimeout(timeout)
    try:
        try:
            connection.connect(path)
        except (FileNotFoundError, ConnectionRefusedError, PermissionError,
                socket.timeout, OSError) as error:
            raise EvaluatorUnavailable(str(error))
        try:
            send_frame(connection, payload)
            return recv_frame(connection, timeout=timeout)
        except (ProtocolError, OSError) as error:
            raise EvaluatorUnavailable(str(error))
    finally:
        try:
            connection.close()
        except OSError:
            pass


def ping(socket_path=None):
    """True if the evaluator answers. For health checks and tests."""
    try:
        reply = _request({'op': 'ping', 'echo': 'alive'}, socket_path)
    except EvaluatorUnavailable:
        return False
    return bool(reply.get('ok')) and reply.get('pong') == 'alive'


def evaluate_search_program(source, max_numbers=1000, socket_path=None):
    """Evaluate ``source`` in the sandbox.

    Never raises. The two failure modes are kept distinct because the old Pyro
    path treated them differently, and the response shape follows from it:

    * evaluator **unreachable** -> ``(None, messages)``; the caller stops and
      reports ``results: None``.
    * evaluator **answered** but produced nothing usable (rejected, timed out,
      evaluation error) -> ``([], messages)``; the caller proceeds and reports
      ``results: []``.
    """
    try:
        reply = _request({'op': 'search_program',
                          'source': source,
                          'max_numbers': max_numbers}, socket_path)
    except EvaluatorUnavailable:
        return None, [dict(_UNAVAILABLE_MESSAGE)]

    if not isinstance(reply, dict):
        return None, [dict(_UNAVAILABLE_MESSAGE)]

    messages = reply.get('messages') or []
    if not isinstance(messages, list):
        messages = []

    records = reply.get('numbers')
    if not reply.get('ok') or records is None:
        # It answered; messages already explain why there is nothing.
        return [], messages

    param_numbers = []
    undecodable = 0
    for record in records:
        if not isinstance(record, dict):
            undecodable += 1
            continue
        try:
            param_numbers.append((record.get('param', ''),
                                  decode_number(record.get('number'))))
        except (UnsupportedNumber, TypeError, ValueError, ArithmeticError):
            undecodable += 1

    if undecodable:
        messages.append({
            'tags': 'alert-warning',
            'text': '%d result(s) could not be decoded.' % (undecodable,),
        })

    return param_numbers, messages
