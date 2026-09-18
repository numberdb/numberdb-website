"""Mahler measures of 1+x_1+...+x_{n-1} -- numberdb.org/T283.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores the logarithmic Mahler measures

    mu_n = m(1 + x_1 + ... + x_{n-1}) = W_n'(0)

for the classical short uniform random-walk cases n = 3, 4, 5, 6.  The first
two are Smyth's closed forms.  The last two are computed from the
Rodriguez-Villegas eta-integrals as stated by Borwein, Straub, Wan and
Zudilin; the table therefore declares heuristic (agreement-checked) rigour
rather than proven rigour.
"""

import os
import sys

import mpmath as mp
import numberdb.sage as numberdb


TABLE = os.environ.get("NUMBERDB_TABLE", "T283")
FIRST_N = 3
LAST_N = 6
DIGITS = 50

# The eta integrals are stable at 50 digits when repeated at 50, 80 and 120
# working digits.  The generator uses the largest of those by default.
WORKING_DIGITS = 120

# Values printed in the screening report and in BSWZ, used as an outside
# smoke test before writing.
KNOWN_PREFIXES = {
    3: "0.32306594721945051",
    4: "0.42627839881750579",
    5: "0.54441256175218558",
    6: "0.62731707483690980",
}

_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _eta_q(q):
    """Dedekind eta as eta(q) = q^(1/24) product (1 - q^m)."""
    if not q:
        return mp.mpf(0)
    total = mp.mpf(1)
    n = 1
    while True:
        term1 = (-1) ** n * q ** (n * (3 * n - 1) / 2)
        term2 = (-1) ** n * q ** (n * (3 * n + 1) / 2)
        total += term1 + term2
        if abs(term1) + abs(term2) < mp.eps * max(1, abs(total)) / 10:
            break
        n += 1
        if n > 100000:
            raise ArithmeticError("Dedekind eta series did not converge")
    return q ** (mp.mpf(1) / 24) * total


def _eta_exp(a, t):
    """Dedekind eta for q = exp(-a*t), using eta(i y)=eta(i/y)/sqrt(y)."""
    if not t or t == mp.inf:
        return mp.mpf(0)
    y = a * t / (2 * mp.pi)
    if y < 1:
        return _eta_q(mp.e ** (-2 * mp.pi / y)) / mp.sqrt(y)
    return _eta_q(mp.e ** (-2 * mp.pi * y))


def _mu5():
    factor = (mp.mpf(15) / (4 * mp.pi ** 2)) ** (mp.mpf(5) / 2)

    def integrand(t):
        return (
            _eta_exp(3, t) ** 3 * _eta_exp(5, t) ** 3
            + _eta_exp(1, t) ** 3 * _eta_exp(15, t) ** 3
        ) * t ** 3

    return factor * mp.quad(integrand, [0, 0.1, 0.5, 1, 2, 5, 10, mp.inf])


def _mu6():
    factor = (mp.mpf(3) / (mp.pi ** 2)) ** 3

    def integrand(t):
        return (
            _eta_exp(1, t) ** 2
            * _eta_exp(2, t) ** 2
            * _eta_exp(3, t) ** 2
            * _eta_exp(6, t) ** 2
        ) * t ** 4

    return factor * mp.quad(integrand, [0, 0.1, 0.5, 1, 2, 5, 10, mp.inf])


def _mahler_measure(n, working_digits=WORKING_DIGITS):
    key = (int(n), int(working_digits))
    if key in _CACHE:
        return _CACHE[key]

    with mp.workdps(working_digits):
        if n == 3:
            value = mp.clsin(2, mp.pi / 3) / mp.pi
        elif n == 4:
            value = 7 * mp.zeta(3) / (2 * mp.pi ** 2)
        elif n == 5:
            value = _mu5()
        elif n == 6:
            value = _mu6()
        else:
            raise ValueError("this draft covers 3 <= n <= 6")
        value = +value
    _CACHE[key] = value
    return value


def _decimal(value, digits):
    return mp.nstr(value, digits, strip_zeros=False)


def _entry_comment(n):
    if n == 3:
        return (
            r"Smyth's value $\mu_3=\mathrm{Cl}_2(\pi/3)/\pi="
            r"\frac{3\sqrt3}{4\pi}L(2,\chi_{-3})$."
        )
    if n == 4:
        return r"Smyth's value $\mu_4=7\zeta(3)/(2\pi^2)$."
    if n == 5:
        return (
            r"Rodriguez-Villegas' eta-integral conjecture for $\mu_5$, "
            r"confirmed numerically by Borwein, Straub, Wan and Zudilin."
        )
    if n == 6:
        return (
            r"Rodriguez-Villegas' eta-integral conjecture for $\mu_6$, "
            r"confirmed numerically by Borwein, Straub, Wan and Zudilin."
        )
    return ""


def run_integrity_checks():
    for n, prefix in KNOWN_PREFIXES.items():
        text = _decimal(_mahler_measure(n, WORKING_DIGITS), 25)
        if not text.startswith(prefix):
            raise ArithmeticError("n=%d: %s does not begin with %s" % (n, text, prefix))

    for n in (5, 6):
        low = _decimal(_mahler_measure(n, 80), DIGITS)
        high = _decimal(_mahler_measure(n, 120), DIGITS)
        if low != high:
            raise ArithmeticError("n=%d: 80- and 120-digit eta runs disagree" % n)


class ShortWalkMahlerMeasures(numberdb.Generator):
    table = TABLE
    parameters = ("n",)
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self, first=FIRST_N, last=LAST_N):
        for n in range(first, last + 1):
            yield {"n": str(n)}

    def value(self, params, digits):
        n = int(params["n"])
        value = _decimal(_mahler_measure(n, WORKING_DIGITS), digits)
        return {"number": value, "comment": _entry_comment(n)}


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
    generator = ShortWalkMahlerMeasures()
    run_integrity_checks()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="short-random-walk Mahler measures, n = %d..%d" % (FIRST_N, LAST_N),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
