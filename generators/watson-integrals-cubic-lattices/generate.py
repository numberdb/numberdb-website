"""Watson integrals of the cubic lattices -- numberdb.org/T393.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores the normalised nearest-neighbour lattice Green function at
the origin for the three cubic Bravais lattices. The generator evaluates the
closed gamma-product forms in ball arithmetic, and the identity-check mode
compares them with Watson's complete-elliptic-integral forms.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField
from sage.rings.complex_arb import ComplexBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T393")

# Measured before filling the draft: the three rows write 100 digits, the
# longest stored value is 101 characters, and the entries block is under 1 KB.
LATTICES = ("Z", "A", "A*")
DIMENSION = "3"

# Bits beyond the requested digits. At 100 digits, all three gamma products and
# all three elliptic-integral checks have radii below 1e-131 with this guard.
WORKING_GUARD = 128


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _real_field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _complex_field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _gamma(R, numerator, denominator):
    return R(QQ(numerator) / QQ(denominator)).gamma()


def _positive_power(R, base, numerator, denominator):
    exponent = R(QQ(numerator) / QQ(denominator))
    return (exponent * R(base).log()).exp()


def watson_integral(family, digits=100):
    R = _real_field(digits)
    pi = R.pi()

    if family == "Z":
        return (
            R(6).sqrt()
            * _gamma(R, 1, 24)
            * _gamma(R, 5, 24)
            * _gamma(R, 7, 24)
            * _gamma(R, 11, 24)
            / (32 * pi**3)
        )
    if family == "A":
        return (
            9
            * _gamma(R, 1, 3) ** 6
            / (_positive_power(R, 2, 14, 3) * pi**4)
        )
    if family == "A*":
        return _gamma(R, 1, 4) ** 4 / (4 * pi**3)
    raise ValueError("unknown cubic lattice family %r" % (family,))


def _real_part(value):
    if not value.imag().contains_zero():
        raise ArithmeticError("elliptic check is not real: %s" % value)
    real = value.real()
    if not real.is_finite():
        raise ArithmeticError("elliptic check is not finite: %s" % value)
    return real


def _elliptic_k_from_modulus(C, modulus):
    """MathWorld's K(k), evaluated by arb's parameter convention K(m)."""
    m = modulus * modulus
    return C(m).elliptic_k()


def watson_integral_elliptic(family, digits=100):
    C = _complex_field(digits)
    pi = C.pi()

    if family == "A*":
        k = C(QQ(1) / QQ(2)).sqrt()
        value = 4 * _elliptic_k_from_modulus(C, k) ** 2 / pi**2
        return _real_part(value)

    if family == "A":
        k = (C(6).sqrt() - C(2).sqrt()) / 4
        value = 3 * C(3).sqrt() * _elliptic_k_from_modulus(C, k) ** 2 / pi**2
        return _real_part(value)

    if family == "Z":
        k = (C(2) - C(3).sqrt()) * (C(3).sqrt() - C(2).sqrt())
        coefficient = 18 + 12 * C(2).sqrt() - 10 * C(3).sqrt() - 7 * C(6).sqrt()
        value = 12 * coefficient * _elliptic_k_from_modulus(C, k) ** 2 / pi**2
        return _real_part(value)

    raise ValueError("unknown cubic lattice family %r" % (family,))


def check_identities(digits=100):
    widest = None
    for family in LATTICES:
        gamma_value = watson_integral(family, digits)
        elliptic_value = watson_integral_elliptic(family, digits)
        difference = gamma_value - elliptic_value
        if not difference.contains_zero():
            raise ArithmeticError(
                "%s: gamma product and elliptic form do not overlap: %s"
                % (family, difference)
            )
        radius = difference.diameter()
        if widest is None or radius > widest[1]:
            widest = (family, radius, difference)
    print("checked %d Watson integral identities" % len(LATTICES))
    print("widest gamma-minus-elliptic difference: %s at family=%s"
          % (widest[2], widest[0]))


class WatsonIntegralsCubicLattices(numberdb.Generator):
    table = TABLE
    parameters = ("family", "n")
    type = "R"
    digits = 100
    rigour = "proven"
    files = ("generate.py",)

    def enumerate(self):
        for family in LATTICES:
            yield {"family": family, "n": DIMENSION}

    def value(self, params, digits):
        if params["n"] != DIMENSION:
            raise ValueError("this table only contains cubic lattices, n=3")
        return watson_integral(params["family"], digits)


def fill_draft_once(generator, message):
    """Fill a fresh draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries, to_text

    table = generator.table
    run = _run_name(generator)
    entries = Entries(*generator.parameters)

    for params in generator.enumerate():
        params = dict(params)
        wanted = generator.digits_for(params)
        entry = generator._entry(params, wanted)
        value = entry["number"]
        identity = ",".join(str(params[name]) for name in generator.parameters)
        _check_rigour(generator, table, identity, value)

        written = to_text(value, wanted, generator.format)
        _check_precision(table, identity, written, wanted, lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=wanted)

    answer = submit_entries(
        table,
        entries,
        message=message,
        produced_by=_producer(generator),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    files = _source_files(generator)
    stored = []
    for name, body in sorted(files.items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


if __name__ == "__main__":
    _key_from_stdin()
    generator = WatsonIntegralsCubicLattices()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        check_identities(generator.digits)
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Watson integrals from gamma products"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
