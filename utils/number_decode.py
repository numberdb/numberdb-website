"""Plain-Python decoding of stored numbers -- no Sage.

Phase A of moving the web container off SageMath. `web` holds the database
credentials and the Django secret; it currently also carries a computer algebra
system that shells out to Singular, GAP, PARI and Maxima, and pays ~187 MB of
RSS and 3.7 s of import time per worker for it. None of that is needed to
render a number that is already stored as bytes.

The stored format is fortunately Sage-independent already -- integers via
``int.to_bytes`` and interval endpoints via ``numpy.float64.tobytes`` -- so the
bytes on disk do not change. Only the layer that interprets them does.

What this module is decoding
----------------------------
The bytes here are the **search index**, not the canonical value. The number as
the contributor wrote it lives in ``TableData`` as text; these floats are a
deliberately widened working copy, because a written interval like ``5.5?`` has
exact decimal bounds that binary floating point cannot represent, so conversion
must round outward. See ``docs/design/number-representation.md``.

That matters for what "correct" means here. The goal is to reproduce the
existing rendering of the working copy byte-for-byte. It is **not** to recover
the contributor's string: text -> interval -> text is not a fixed point (Sage
turns ``3.14159?`` into ``3.1416?`` and then ``3.142?``), so a decoder that
appeared to "improve" precision would be wrong, and one that round-tripped
through this path back into ``TableData`` would corrupt data.

Correctness is pinned by ``tests/golden/number_decoding.json``, captured from
real production rows using the Sage implementation. Anything claimed in
``SUPPORTED_TYPES`` must reproduce Sage byte-for-byte, and the golden test
enforces it on a plain interpreter with no Sage and no database.

Progress so far
---------------
Implemented: ``__str__`` for stored integers and rationals.

Not yet: everything that renders through a real interval. Sage prints those in
its ``?`` notation (``8.03973715568147?``, ``1.1240007277776077?e21``), where
the digits are those known to be correct and ``?`` marks uncertainty in the
last place. Reproducing that exactly -- including the exponent form and the
fallback to ``[lo,uo]`` when relative precision is poor -- is the substantial
piece of this migration, and it is deliberately left until the harness above
can prove it.
"""

from fractions import Fraction

__all__ = [
    'SUPPORTED_TYPES',
    'NUMBER_TYPE_ZZ',
    'NUMBER_TYPE_QQ',
    'NUMBER_TYPE_RIF',
    'NUMBER_TYPE_RBF',
    'HALF_BLOB_LENGTH',
    'UnsupportedType',
    'decode_to_text',
]

NUMBER_TYPE_ZZ = b'z'
NUMBER_TYPE_QQ = b'q'
NUMBER_TYPE_RIF = b'r'
NUMBER_TYPE_RBF = b'b'

#: Mirrors ``Number.HALF_BLOB_LENGTH``. The blob is two halves of this size.
HALF_BLOB_LENGTH = 8

#: Types whose ``__str__`` this module reproduces exactly. Adding a type here
#: makes the golden test enforce it -- so add only once it genuinely matches.
SUPPORTED_TYPES = frozenset({NUMBER_TYPE_ZZ, NUMBER_TYPE_QQ})


class UnsupportedType(Exception):
    """Stored type has no plain-Python renderer yet."""


def _as_bytes(value):
    """Normalise Django's BinaryField, which may hand back memoryview."""
    if isinstance(value, memoryview):
        return value.tobytes()
    if isinstance(value, (bytes, bytearray)):
        return bytes(value)
    raise TypeError('expected bytes-like, got %s' % (type(value).__name__,))


def decode_integer(blob):
    """Stored integer -> int. Big-endian, signed, matching ``Number.__init__``."""
    return int.from_bytes(_as_bytes(blob), byteorder='big', signed=True)


def decode_rational(blob):
    """Stored rational -> Fraction.

    Numerator is signed, denominator unsigned -- asymmetric, and that asymmetry
    is load-bearing: reading the denominator as signed silently corrupts any
    fraction whose denominator has its top bit set.
    """
    data = _as_bytes(blob)
    numerator = int.from_bytes(data[:HALF_BLOB_LENGTH], byteorder='big', signed=True)
    denominator = int.from_bytes(data[HALF_BLOB_LENGTH:], byteorder='big', signed=False)
    if denominator == 0:
        raise ValueError('stored rational has zero denominator')
    return Fraction(numerator, denominator)


def decode_to_text(number_type, blob):
    """Reproduce ``Number.__str__`` for a stored row.

    ``number_type`` may be bytes or a one-character string.
    """
    if isinstance(number_type, str):
        number_type = number_type.encode('latin-1')
    number_type = _as_bytes(number_type)

    if number_type == NUMBER_TYPE_ZZ:
        return str(decode_integer(blob))

    if number_type == NUMBER_TYPE_QQ:
        value = decode_rational(blob)
        # Sage prints a rational with denominator 1 as a bare integer, and
        # Fraction.__str__ does the same, so no special case is needed. It is
        # asserted in the golden test rather than assumed here.
        return str(value)

    raise UnsupportedType(
        'no plain-Python renderer for stored type %r yet; see module docstring'
        % (number_type,)
    )
