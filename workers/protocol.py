"""Length-prefixed JSON framing for the evaluator socket.

Deliberately tiny and dependency-free: this code sits on the trust boundary
between the web container and the sandbox, so it should be small enough to read
in one sitting.

Frame layout::

    +----------------+---------------------------+
    | 4 bytes, BE u32| UTF-8 JSON payload         |
    +----------------+---------------------------+

Every read is bounded. A sandbox that has been taken over will happily announce
a 4 GiB frame, so the length prefix is checked *before* allocating, and reads
stop at ``max_bytes`` regardless of what the header claims.

No pickle, in either direction, ever. The web container holds the database
credentials; handing it a pickle from the sandbox would invert the whole point
of having a sandbox.
"""

import json
import select
import socket
import struct

__all__ = [
    'ProtocolError',
    'FrameTooLarge',
    'Timeout',
    'MAX_FRAME_BYTES',
    'send_frame',
    'recv_frame',
]

_HEADER = struct.Struct('>I')
_HEADER_BYTES = _HEADER.size

#: Default ceiling for a single frame. Search results are lists of short
#: numeric records; a megabyte is already generous.
MAX_FRAME_BYTES = 1 << 20


class ProtocolError(Exception):
    """Malformed or truncated frame."""


class FrameTooLarge(ProtocolError):
    """Frame exceeds the negotiated ceiling."""


class Timeout(ProtocolError):
    """Deadline passed before a complete frame arrived."""


def _recv_exactly(sock, count, deadline_monotonic, clock):
    """Read exactly ``count`` bytes, honouring an absolute deadline."""
    chunks = []
    remaining = count
    while remaining > 0:
        timeout = deadline_monotonic - clock()
        if timeout <= 0:
            raise Timeout("timed out waiting for %d more byte(s)" % (remaining,))
        ready, _, _ = select.select([sock], [], [], timeout)
        if not ready:
            raise Timeout("timed out waiting for %d more byte(s)" % (remaining,))
        try:
            chunk = sock.recv(min(remaining, 65536))
        except (socket.timeout, BlockingIOError):
            continue
        if not chunk:
            raise ProtocolError(
                "connection closed with %d byte(s) outstanding" % (remaining,)
            )
        chunks.append(chunk)
        remaining -= len(chunk)
    return b''.join(chunks)


def send_frame(sock, payload, max_bytes=MAX_FRAME_BYTES):
    """Serialise ``payload`` as JSON and write one frame.

    Raises ``FrameTooLarge`` rather than truncating, so an oversized reply is a
    visible error instead of corrupt data.
    """
    body = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode('utf-8')
    if len(body) > max_bytes:
        raise FrameTooLarge(
            "payload is %d bytes, limit is %d" % (len(body), max_bytes)
        )
    sock.sendall(_HEADER.pack(len(body)) + body)


def recv_frame(sock, max_bytes=MAX_FRAME_BYTES, timeout=None, clock=None):
    """Read one frame and return the decoded object.

    ``timeout`` is total wall-clock seconds for the whole frame, not per read,
    so a peer dribbling one byte at a time cannot hold the connection open.
    """
    if clock is None:
        import time
        clock = time.monotonic
    deadline = (clock() + timeout) if timeout is not None else float('inf')

    header = _recv_exactly(sock, _HEADER_BYTES, deadline, clock)
    (length,) = _HEADER.unpack(header)

    # Checked before allocating anything.
    if length > max_bytes:
        raise FrameTooLarge(
            "peer announced %d bytes, limit is %d" % (length, max_bytes)
        )

    body = _recv_exactly(sock, length, deadline, clock) if length else b''
    try:
        return json.loads(body.decode('utf-8'))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise ProtocolError("undecodable frame: %s" % (error,))
