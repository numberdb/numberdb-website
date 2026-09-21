"""Zeros of the Hurwitz zeta function zeta(s,a) -- numberdb.org/T386.

For rational 0 < a <= 1 with denominator at most 4, this stores the
non-real zeros rho of zeta(s,a) with 0 < Im(rho) <= 40.

Run it with SageMath:

    $ sage -pip install numberdb mpmath   # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

Under this repository's build wrapper:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generators/hurwitz-zeta-zeros/generate.py
"""

from fractions import Fraction
import os
import sys

import mpmath as mp

import numberdb.sage as numberdb
from numberdb import ComplexInterval, RealInterval
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


TABLE = os.environ.get("NUMBERDB_TABLE", "T386")
MAX_DENOMINATOR = 4
HEIGHT = 40
DIGITS = 30
WORKING_DIGITS = (50, 65)

SIGMA_MIN = Fraction(-4)
SIGMA_MAX = Fraction(2)
GRID_STEP = Fraction(1, 4)
GRID_SHIFTS = (Fraction(0),)
SEED_LIMIT = 45

_ROOTS = {}
_CHECKED = False


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token
        numberdb.configure(api_key=token)


def _fraction_text(value):
    return str(value.numerator) if value.denominator == 1 else "%d/%d" % (
        value.numerator,
        value.denominator,
    )


def _parameters():
    for denominator in range(1, MAX_DENOMINATOR + 1):
        for numerator in range(1, denominator + 1):
            frac = Fraction(numerator, denominator)
            if frac.denominator == denominator:
                yield frac


def _mp_fraction(frac):
    return mp.mpf(frac.numerator) / mp.mpf(frac.denominator)


def _mp_text(value, digits):
    return mp.nstr(value, digits - 5, min_fixed=-100, max_fixed=100)


def _component_interval(compute):
    interval = numberdb.agreeing(compute, at=WORKING_DIGITS)
    return _sage_real_interval(interval)


def _sage_real_interval(interval):
    return RealInterval(_endpoint(interval.lower()), _endpoint(interval.upper()))


def _endpoint(value):
    exact = getattr(value, "exact_rational", None)
    if exact is not None:
        rational = exact()
        return Fraction(int(rational.numerator()), int(rational.denominator()))
    return Fraction(str(value))


def _zeta_roots(working):
    mp.mp.dps = int(working)
    roots = []
    n = 1
    while True:
        zero = mp.zetazero(n)
        if zero.imag > HEIGHT:
            return roots
        roots.append(
            {
                "real": Fraction(1, 2),
                "imag": zero.imag,
                "kind": "zeta",
                "source_index": n,
            }
        )
        n += 1


def _half_roots(working):
    mp.mp.dps = int(working)
    roots = list(_zeta_roots(working))
    k = 1
    while True:
        imaginary = 2 * mp.pi * k / mp.log(2)
        if imaginary > HEIGHT:
            break
        roots.append(
            {
                "real": Fraction(0),
                "imag": imaginary,
                "kind": "two-power",
                "source_index": k,
            }
        )
        k += 1
    roots.sort(key=lambda root: (root["imag"], root["real"]))
    return roots


def _local_minima_seeds(frac, working):
    mp.mp.dps = int(min(45, max(35, working - 5)))
    a_value = _mp_fraction(frac)

    def f(z):
        return mp.zeta(z, a_value)

    seeds = []
    for shift in GRID_SHIFTS:
        sigmas = []
        sigma = mp.mpf(SIGMA_MIN.numerator) / SIGMA_MIN.denominator
        sigma += mp.mpf(shift.numerator) / shift.denominator
        sigma_max = mp.mpf(SIGMA_MAX.numerator) / SIGMA_MAX.denominator
        step = mp.mpf(GRID_STEP.numerator) / GRID_STEP.denominator
        while sigma <= sigma_max + mp.mpf("1e-30"):
            sigmas.append(sigma)
            sigma += step

        ts = []
        t = step + mp.mpf(shift.numerator) / shift.denominator
        while t <= HEIGHT + mp.mpf("1e-30"):
            ts.append(t)
            t += step

        grid = {}
        for i, sigma in enumerate(sigmas):
            for j, t in enumerate(ts):
                try:
                    grid[(i, j)] = abs(f(mp.mpc(sigma, t)))
                except Exception:
                    grid[(i, j)] = mp.inf

        for i, sigma in enumerate(sigmas):
            for j, t in enumerate(ts):
                value = grid[(i, j)]
                if not mp.isfinite(value):
                    continue
                neighbours = [
                    grid.get((ii, jj), mp.inf)
                    for ii in (i - 1, i, i + 1)
                    for jj in (j - 1, j, j + 1)
                    if (ii, jj) != (i, j)
                ]
                if value <= min(neighbours):
                    seeds.append((value, mp.mpc(sigma, t)))

    seeds.sort(key=lambda item: item[0])
    return seeds


def _generic_roots(frac, working):
    mp.mp.dps = int(working)
    a_value = _mp_fraction(frac)

    def f(z):
        return mp.zeta(z, a_value)

    roots = []
    for _value, seed in _local_minima_seeds(frac, working)[:SEED_LIMIT]:
        try:
            root = mp.findroot(
                f,
                seed,
                tol=mp.mpf(10) ** (-(working - 10)),
                maxsteps=50,
            )
        except Exception:
            continue
        if not (mp.isfinite(root.real) and mp.isfinite(root.imag)):
            continue
        if root.imag <= mp.mpf("1e-15") or root.imag > HEIGHT + mp.mpf("1e-15"):
            continue
        if root.real < -10 or root.real > 6:
            continue
        try:
            residual = abs(f(root))
        except Exception:
            continue
        if residual > mp.mpf(10) ** (-(working // 2)):
            continue
        if any(abs(root - old["root"]) < mp.mpf("1e-24") for old in roots):
            continue
        roots.append({"root": root, "kind": "generic"})

    roots.sort(key=lambda row: (row["root"].imag, row["root"].real))
    return roots


def _roots_for(frac, working):
    key = (frac, int(working))
    if key in _ROOTS:
        return _ROOTS[key]
    if frac == Fraction(1, 1):
        roots = _zeta_roots(working)
    elif frac == Fraction(1, 2):
        roots = _half_roots(working)
    else:
        roots = _generic_roots(frac, working)
    _ROOTS[key] = roots
    return roots


def _root_count(frac):
    return len(_roots_for(frac, WORKING_DIGITS[0]))


def _generic_component(frac, index, part, working):
    root = _roots_for(frac, working)[index - 1]["root"]
    return _mp_text(root.real if part == "real" else root.imag, working)


def _special_imaginary(frac, index, working):
    return _mp_text(_roots_for(frac, working)[index - 1]["imag"], working)


def _root_value(frac, index):
    if frac in (Fraction(1, 1), Fraction(1, 2)):
        root = _roots_for(frac, WORKING_DIGITS[0])[index - 1]
        return ComplexInterval(
            root["real"],
            _component_interval(lambda working: _special_imaginary(frac, index, working)),
        )
    return ComplexInterval(
        _component_interval(lambda working: _generic_component(frac, index, "real", working)),
        _component_interval(lambda working: _generic_component(frac, index, "imag", working)),
    )


def _entry_comment(frac, index):
    if frac == Fraction(1, 1):
        root = _roots_for(frac, WORKING_DIGITS[0])[index - 1]
        n = root["source_index"]
        return (
            "The imaginary part is "
            "HREF{Zeros_of_the_Riemann_zeta_function#%d}[$t_%d$]." % (n, n)
        )
    if frac == Fraction(1, 2):
        root = _roots_for(frac, WORKING_DIGITS[0])[index - 1]
        if root["kind"] == "zeta":
            n = root["source_index"]
            return (
                "This zero comes from the factor $\\zeta(s)$; its imaginary "
                "part is HREF{Zeros_of_the_Riemann_zeta_function#%d}[$t_%d$]."
                % (n, n)
            )
        k = root["source_index"]
        return "This zero is $2\\pi\\mathrm{i}%d/\\log 2$, from the factor $2^s-1$." % k
    return None


def _assert_root_lists_agree():
    global _CHECKED
    if _CHECKED:
        return
    tolerance = mp.mpf("1e-28")
    for frac in _parameters():
        first = _roots_for(frac, WORKING_DIGITS[0])
        second = _roots_for(frac, WORKING_DIGITS[1])
        if len(first) != len(second):
            raise ArithmeticError(
                "a=%s found %d roots at %d digits and %d roots at %d digits"
                % (
                    _fraction_text(frac),
                    len(first),
                    WORKING_DIGITS[0],
                    len(second),
                    WORKING_DIGITS[1],
                )
            )
        for index, (one, two) in enumerate(zip(first, second), 1):
            if frac in (Fraction(1, 1), Fraction(1, 2)):
                delta = abs(one["imag"] - two["imag"])
            else:
                delta = abs(one["root"] - two["root"])
            if delta > tolerance:
                raise ArithmeticError(
                    "a=%s n=%d differs between working precisions by %s"
                    % (_fraction_text(frac), index, delta)
                )
    _CHECKED = True


def _arb_residual(frac, root, digits=80):
    field = ComplexBallField(numberdb.bits(digits, losing=96))
    s = field(str(root.real)) + field.gen(0) * field(str(root.imag))
    a_value = field(QQ(frac.numerator) / QQ(frac.denominator))
    return s.zeta(a_value).abs()


def check_controls():
    """Checks independent of the generic Hurwitz root search."""
    _assert_root_lists_agree()
    mp.mp.dps = int(WORKING_DIGITS[1])

    zeta_expected = (
        "14.134725141734693790457251983562",
        "21.022039638771554992628479593897",
        "25.010857580145688763213790992563",
        "30.424876125859513210311897530584",
        "32.935061587739189690662368964075",
        "37.586178158825671257217763480705",
    )
    for index, expected in enumerate(zeta_expected, 1):
        got = _mp_text(_roots_for(Fraction(1, 1), WORKING_DIGITS[1])[index - 1]["imag"], 40)
        if not got.startswith(expected[:30]):
            raise ArithmeticError("T3 control n=%d gave %s" % (index, got))

    half_roots = _roots_for(Fraction(1, 2), WORKING_DIGITS[1])
    two_power = [root for root in half_roots if root["kind"] == "two-power"]
    if len(two_power) != 4:
        raise ArithmeticError("expected four zeros of 2^s-1 below height 40")
    for k, root in enumerate(two_power, 1):
        expected = 2 * mp.pi * k / mp.log(2)
        if abs(root["imag"] - expected) > mp.mpf("1e-50"):
            raise ArithmeticError("2^s-1 control k=%d failed" % k)

    for frac in _parameters():
        if frac in (Fraction(1, 1), Fraction(1, 2)):
            continue
        for index, root in enumerate(_roots_for(frac, WORKING_DIGITS[1]), 1):
            residual = _arb_residual(frac, root["root"])
            if not (residual.upper() < QQ(1) / (QQ(10) ** 35)):
                raise ArithmeticError(
                    "arb residual for a=%s n=%d is %s"
                    % (_fraction_text(frac), index, residual)
                )

    counts = ", ".join(
        "%s:%d" % (_fraction_text(frac), len(_roots_for(frac, WORKING_DIGITS[0])))
        for frac in _parameters()
    )
    print("root counts below height %d: %s" % (HEIGHT, counts))


class HurwitzZetaZeros(numberdb.Generator):
    table = TABLE
    parameters = ("a", "n")
    type = "C"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"
    files = ("generate.py",)

    def enumerate(self):
        _assert_root_lists_agree()
        for frac in _parameters():
            for index in range(1, _root_count(frac) + 1):
                yield {"a": _fraction_text(frac), "n": index}

    def value(self, params, digits):
        frac = Fraction(params["a"])
        index = int(params["n"])
        if frac.denominator > MAX_DENOMINATOR or not (0 < frac <= 1):
            raise ValueError("this table covers 0 < a <= 1 with denominator at most %d" % MAX_DENOMINATOR)
        if index < 1 or index > _root_count(frac):
            raise ValueError("no stored zero n=%d for a=%s" % (index, params["a"]))
        entry = {"number": _root_value(frac, index)}
        comment = _entry_comment(frac, index)
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
    generator = HurwitzZetaZeros()
    check_controls()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(fill_draft_once(generator, message="computed Hurwitz zeta zeros"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
