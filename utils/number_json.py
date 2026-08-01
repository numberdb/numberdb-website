"""JSON encoding for Sage numbers crossing the evaluator boundary.

Shared by the sandbox (which encodes) and Django (which decodes). Replaces the
Sage pickles that used to travel over Pyro.

Why not pickle: the web container holds the database credentials and the Django
secret key. Unpickling anything the evaluator sends hands code execution to
whatever the evaluator has become, which would defeat the point of sandboxing
it. Every value here is plain JSON, and decoding dispatches on a ``kind`` tag
through a fixed table -- never on a name supplied by the payload.

Encoding aims to be exact rather than approximate. Interval endpoints are
carried as exact rationals (``p/q`` strings) instead of decimal
approximations, so an interval survives the round trip without silently
widening or narrowing. ``api.py`` blurs intervals before searching anyway, but
that is its decision to make, not a rounding artefact of transport.
"""

from sage.rings.all import ZZ, QQ, RIF, CIF, Qp, PolynomialRing, RBF

__all__ = ['encode_number', 'decode_number', 'UnsupportedNumber']


class UnsupportedNumber(Exception):
    """Raised for a value with no defined wire representation."""


def _exact_rational_string(endpoint):
    """Exact ``p/q`` for a real endpoint, so intervals round-trip losslessly."""
    try:
        return str(QQ(endpoint.exact_rational()))
    except (AttributeError, TypeError, ValueError):
        # Infinities and anything without an exact rational fall back to the
        # decimal form; decode handles both.
        return str(endpoint)


def _is_p_adic(parent):
    try:
        method = getattr(parent, 'is_pAdicField', None)
        if callable(method):
            return bool(method())
    except Exception:
        pass
    text = str(parent).lower()
    return ('adic' in text) and ('field' in text or 'ring' in text)


def _is_polynomial_ring(parent):
    text = str(parent)
    return text.startswith('Multivariate Polynomial Ring') or \
        text.startswith('Univariate Polynomial Ring')


def encode_number(value):
    """Encode one Sage number as a JSON-serialisable dict.

    Raises ``UnsupportedNumber`` if there is no representation for it; callers
    report that as a per-parameter error rather than failing the whole search.
    """
    parent = value.parent()

    if _is_p_adic(parent):
        prime = int(parent.prime())
        try:
            precision = int(value.precision_absolute())
        except (AttributeError, TypeError):
            precision = int(parent.precision_cap())
        # A rational representative, not an integer lift. An integer spans only
        # Z_p, so every value of negative valuation -- 1/5 in Q_5, 1/2 in Q_2 --
        # was unrepresentable, and 1000 of the 6712 stored p-adics have one.
        #
        # Built from valuation and unit part rather than by coercing to QQ:
        # the unit is always a p-adic integer, so its lift is an honest integer,
        # and p**valuation carries the rest exactly.
        if value == 0:
            representative = QQ(0)
        else:
            valuation = int(value.valuation())
            unit = int(value.unit_part().lift())
            representative = QQ(prime) ** valuation * QQ(unit)
        return {'kind': 'Qp', 'prime': prime, 'precision': precision,
                'value': str(representative)}

    if _is_polynomial_ring(parent):
        return {'kind': 'polynomial',
                'variables': int(len(value.parent().gens())),
                'value': str(value).replace(' ', '')}

    if parent is CIF or parent == CIF:
        real, imaginary = value.real(), value.imag()
        return {'kind': 'CIF',
                're_lower': _exact_rational_string(real.lower()),
                're_upper': _exact_rational_string(real.upper()),
                'im_lower': _exact_rational_string(imaginary.lower()),
                'im_upper': _exact_rational_string(imaginary.upper())}

    if parent is RIF or parent == RIF:
        return {'kind': 'RIF',
                'lower': _exact_rational_string(value.lower()),
                'upper': _exact_rational_string(value.upper())}

    # Exactly-known values. Carried as text rather than JSON numbers: the
    # database holds integers of over a thousand digits, and a JSON number is
    # a double to most parsers, which would silently round them.
    if parent is ZZ or parent == ZZ:
        return {'kind': 'ZZ', 'value': str(ZZ(value))}

    if parent is QQ or parent == QQ:
        return {'kind': 'QQ', 'value': str(QQ(value))}

    # A ball, carried by its endpoints as exact rationals -- the same treatment
    # as an interval, and for the same reason.
    #
    # Centre and radius would be the natural encoding and are wrong here: the
    # radius has no exact rational form, so it serialises through str() and
    # rounds. Rounding it *down* yields a ball narrower than the one stored,
    # which no longer contains the number it describes. Measured on the 73 ball
    # values in the database, 28 came back too narrow. Endpoints round outward
    # by construction, so the ball can only ever widen.
    if parent is RBF or parent == RBF:
        interval = RIF(value)
        return {'kind': 'RBF',
                'lower': _exact_rational_string(interval.lower()),
                'upper': _exact_rational_string(interval.upper())}

    raise UnsupportedNumber('no wire representation for parent %s' % (parent,))


def _rational(text):
    try:
        return QQ(text)
    except (TypeError, ValueError):
        # Decimal fallback from _exact_rational_string.
        return RIF(text).lower()


def _decode_RIF(record):
    return RIF(_rational(record['lower']), _rational(record['upper']))


def _decode_CIF(record):
    return CIF(RIF(_rational(record['re_lower']), _rational(record['re_upper'])),
               RIF(_rational(record['im_lower']), _rational(record['im_upper'])))


def _decode_Qp(record):
    precision = int(record['precision'])
    prime = int(record['prime'])
    field = Qp(prime, prec=max(abs(precision) + 1, 1))
    # add_bigoh sets *absolute* precision, which is what the record carries;
    # Qp's own prec argument is a relative cap and would not reproduce it.
    return field(QQ(record['value'])).add_bigoh(precision)


def _decode_ZZ(record):
    return ZZ(record['value'])


def _decode_QQ(record):
    return QQ(record['value'])


def _decode_RBF(record):
    # Via an interval, so the ball contains the endpoints rather than being
    # fitted to them.
    return RBF(RIF(_rational(record['lower']), _rational(record['upper'])))


def _decode_polynomial(record):
    variables = max(int(record['variables']), 1)
    ring = PolynomialRing(QQ, variables, 'x')
    return ring(record['value'])


#: Fixed dispatch table. Decoding never resolves a name from the payload.
_DECODERS = {
    'RIF': _decode_RIF,
    'CIF': _decode_CIF,
    'ZZ': _decode_ZZ,
    'QQ': _decode_QQ,
    'RBF': _decode_RBF,
    'Qp': _decode_Qp,
    'polynomial': _decode_polynomial,
}


def decode_number(record):
    """Rebuild a Sage number from an ``encode_number`` record."""
    if not isinstance(record, dict):
        raise UnsupportedNumber('number record must be an object')
    decoder = _DECODERS.get(record.get('kind'))
    if decoder is None:
        raise UnsupportedNumber('unknown number kind %r' % (record.get('kind'),))
    return decoder(record)
