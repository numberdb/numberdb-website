r"""Cusp shapes of the hyperbolic prime knots with at most ten crossings -- numberdb.org/T317

For every hyperbolic prime knot K = n_k of the Rolfsen table with at most ten
crossings, this draft stores the cusp shape tau(S^3 \ K) in SnapPy's
meridian-longitude basis, for the knot as KnotInfo draws it and for the mirror
image of each chiral hyperbolic knot.

Run it with SageMath and SnapPy:

    $ sage -pip install numberdb snappy   # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The exterior is built from KnotInfo's braid word, not from SnapPy's manifold
name, for the same reason as the neighboring knot tables: SnapPy's built-in
Rolfsen names use pre-Perko numbering for part of the ten-crossing table.
"""

import os
import sys

import numberdb.sage as numberdb
import sage.symbolic.ring  # noqa: F401
from sage.rings.real_mpfi import RealIntervalField
from snappy import Link

from knotinfo_prime_knots import (
    AMPHICHIRAL,
    KNOTINFO_BRAIDS,
    NAMED,
    TORUS,
    names,
)


TABLE = os.environ.get("NUMBERDB_TABLE", "T317")
WORKING_BITS = 540
GEOMETRIC = "all tetrahedra positively oriented"


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def hyperbolic_names():
    keys = [key for key in names() if key in set(KNOTINFO_BRAIDS) - set(TORUS)]
    if len(keys) != 243:
        raise ArithmeticError("expected 243 hyperbolic knots, got %d" % len(keys))
    return keys


def _exterior(n, k, mirror=False):
    strands, word = KNOTINFO_BRAIDS[(n, k)]
    link = Link(braid_closure=[int(letter) for letter in word])
    if mirror:
        link = link.mirror()
    manifold = link.exterior()
    for _attempt in range(50):
        if manifold.solution_type() == GEOMETRIC:
            return manifold
        manifold.randomize()
    raise ArithmeticError("%d_%d: no geometric triangulation found" % (n, k))


def _shape(n, k, image):
    return _exterior(n, k, mirror=(image == "mirror")).cusp_info(
        "shape", verified=True, bits_prec=WORKING_BITS
    )[0]


def _complex_contains_zero(z):
    return z.real().contains_zero() and z.imag().contains_zero()


def _check_figure_eight(z):
    rif = RealIntervalField(WORKING_BITS)
    target = 2 * rif(3).sqrt()
    if not z.real().contains_zero() or not (z.imag() - target).contains_zero():
        raise ArithmeticError("4_1: cusp shape does not contain 2*sqrt(-3)")


def _entry_comment(n, k, image):
    if (n, k) not in NAMED:
        return None
    name = NAMED[(n, k)]
    if image == "mirror":
        name = "mirror image of " + name
    return name


class CuspShapes(numberdb.Generator):

    table = TABLE
    parameters = ("n", "k", "knot")
    type = "C"
    digits = 90
    rigour = "proven"
    files = ("generate.py", "knotinfo_prime_knots.py")

    def __init__(self):
        super().__init__()
        self._values = {}
        self._checked = set()

    def enumerate(self):
        for n, k in hyperbolic_names():
            yield {"n": int(n), "k": int(k), "knot": "K"}
            if (n, k) not in AMPHICHIRAL:
                yield {"n": int(n), "k": int(k), "knot": "mirror"}

    def _ensure_checked(self, n, k):
        key = (n, k)
        if key in self._checked:
            return

        z = _shape(n, k, "K")
        self._values[(n, k, "K")] = z

        if key == (4, 1):
            _check_figure_eight(z)

        if key in AMPHICHIRAL:
            if not z.real().contains_zero():
                raise ArithmeticError("%d_%d: amphichiral cusp shape has nonzero real part" % (n, k))
        else:
            mirror = _shape(n, k, "mirror")
            self._values[(n, k, "mirror")] = mirror
            if not _complex_contains_zero(mirror + z.conjugate()):
                raise ArithmeticError("%d_%d: mirror cusp shape is not -conjugate" % (n, k))

        self._checked.add(key)

    def value(self, params, digits):
        n, k = int(params["n"]), int(params["k"])
        image = params["knot"]
        if (n, k) not in set(KNOTINFO_BRAIDS) - set(TORUS):
            raise ValueError("%d_%d is not a hyperbolic prime knot with at most ten crossings" % (n, k))
        if image not in ("K", "mirror"):
            raise ValueError("knot is 'K' or 'mirror', not %r" % image)
        if image == "mirror" and (n, k) in AMPHICHIRAL:
            raise ValueError("%d_%d is amphichiral and has one entry" % (n, k))

        self._ensure_checked(n, k)
        entry = {"number": self._values[(n, k, image)]}
        comment = _entry_comment(n, k, image)
        if comment:
            entry["comment"] = comment
        return entry


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
        asked = generator.digits_for(params)
        entry = generator._entry(params, asked)
        wanted = entry.get("digits", asked)
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
        produced_by=_producer(generator, os.environ.get("NUMBERDB_ASSISTED_BY", "")),
        upsert=False,
        run=run,
        rigour=generator.rigour,
    )

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message, rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = CuspShapes()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(
            generator,
            message=("cusp shapes of the 243 hyperbolic prime knots with at most "
                     "ten crossings and the mirror images of the chiral ones")))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
