"""The Falkner-Skan separation parameter -- numberdb.org/T420

This generator computes the separation value of the Falkner-Skan Hartree
parameter beta, where the wall shear f''(0) is zero, and the equivalent
external-velocity exponent m = beta / (2 - beta).

Run it with SageMath:

    $ sage -pip install numberdb scipy numpy
    $ sage -python generate.py
    $ sage -python generate.py --publish

For this repository's build environment, use:

    $ agents/sage.sh generate.py
    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 NUMBERDB_PUBLISH=1 \
        agents/sage.sh generate.py

The computation imposes f(0)=f'(0)=f''(0)=0 and solves for the beta for which
the finite-interval initial-value solution has f'(eta_max)=1. The stored
digits are required to agree between two working precisions and two truncation
lengths; a SciPy collocation solve with beta as an unknown parameter checks the
same endpoint by an independent code path.
"""

import gc
import os
import sys

import numberdb.sage as numberdb

from mpmath import mp


TABLE = "T420"
DIGITS = 30
PARAMETERISATIONS = ("beta", "m")
BRACKET = ("-0.199", "-0.1985")
ETA_MAX_LOW = "40"
ETA_MAX_HIGH = "50"
ETA_MAX_CHECK = "60"
LOW_EXTRA_DIGITS = 14
HIGH_EXTRA_DIGITS = 22

_CACHE = {}


def _progress(message):
    print(message, flush=True)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _format_decimal(value, digits):
    return mp.nstr(
        value,
        n=digits,
        strip_zeros=False,
        min_fixed=-100,
        max_fixed=100,
    )


def _integrate(beta, dps, eta_max):
    mp.dps = dps
    beta = mp.mpf(beta)
    eta_max = mp.mpf(eta_max)

    def rhs(_eta, y):
        f, fp, fpp = y
        return [
            fp,
            fpp,
            -f * fpp - beta * (1 - fp * fp),
        ]

    solution = mp.odefun(
        rhs,
        mp.mpf("0"),
        (mp.mpf("0"), mp.mpf("0"), mp.mpf("0")),
        tol=mp.mpf(10) ** (-(dps - 12)),
        degree=30,
    )
    end = solution(eta_max)
    del solution
    gc.collect()
    return end


def _residual(beta, dps, eta_max):
    end = _integrate(beta, dps, eta_max)
    return end[1] - 1


def _solve_beta(dps, eta_max, digits):
    mp.dps = dps
    lo = mp.mpf(BRACKET[0])
    hi = mp.mpf(BRACKET[1])
    f_lo = _residual(lo, dps, eta_max)
    f_hi = _residual(hi, dps, eta_max)
    if f_lo == 0:
        return lo
    if f_hi == 0:
        return hi
    if f_lo * f_hi > 0:
        raise ArithmeticError(
            "separation bracket has no sign change at dps=%s, eta=%s: %s, %s"
            % (dps, eta_max, mp.nstr(f_lo, 12), mp.nstr(f_hi, 12))
        )

    previous_x, previous_f = lo, f_lo
    current_x, current_f = hi, f_hi
    tolerance = mp.mpf(10) ** (-(digits + 8))

    for _ in range(60):
        if current_f != previous_f:
            candidate = current_x - current_f * (current_x - previous_x) / (
                current_f - previous_f
            )
        else:
            candidate = (lo + hi) / 2
        if candidate <= lo or candidate >= hi:
            candidate = (lo + hi) / 2

        f_candidate = _residual(candidate, dps, eta_max)
        if f_candidate == 0:
            return candidate
        if f_lo * f_candidate < 0:
            hi, f_hi = candidate, f_candidate
        else:
            lo, f_lo = candidate, f_candidate

        previous_x, previous_f = current_x, current_f
        current_x, current_f = candidate, f_candidate
        if abs(hi - lo) < tolerance:
            return (lo + hi) / 2

    raise ArithmeticError(
        "separation solve did not converge: width=%s, residual=%s"
        % (mp.nstr(abs(hi - lo), 12), mp.nstr(current_f, 12))
    )


def _m_from_beta(beta):
    return beta / (mp.mpf(2) - beta)


def _scipy_beta_check():
    import numpy as np
    from scipy.integrate import solve_bvp

    eta_max = 40.0
    x = np.linspace(0.0, eta_max, 600)
    fp = 1.0 - np.exp(-0.02 * x ** 3)
    f = np.cumsum(fp) * (x[1] - x[0])
    fpp = 0.06 * x ** 2 * np.exp(-0.02 * x ** 3)
    guess = np.vstack((f, fp, fpp))

    def ode(_x, y, p):
        beta = p[0]
        return np.vstack((
            y[1],
            y[2],
            -y[0] * y[2] - beta * (1 - y[1] * y[1]),
        ))

    def bc(left, right, _p):
        return np.array((left[0], left[1], left[2], right[1] - 1.0))

    answer = solve_bvp(
        ode,
        bc,
        x,
        guess,
        p=np.array([-0.198837735]),
        tol=1e-9,
        max_nodes=20000,
        verbose=0,
    )
    if not answer.success:
        raise ArithmeticError("SciPy solve_bvp failed: %s" % answer.message)
    return mp.mpf(str(answer.p[0]))


def _values_for_digits(digits):
    low_dps = digits + LOW_EXTRA_DIGITS
    high_dps = digits + HIGH_EXTRA_DIGITS

    _progress("computing beta_s at %d digits, eta_max=%s" % (low_dps, ETA_MAX_LOW))
    beta_low = _solve_beta(low_dps, ETA_MAX_LOW, digits)
    _progress("computing beta_s at %d digits, eta_max=%s" % (high_dps, ETA_MAX_HIGH))
    beta_high = _solve_beta(high_dps, ETA_MAX_HIGH, digits)
    _progress("checking beta_s at %d digits, eta_max=%s" % (high_dps, ETA_MAX_CHECK))
    beta_check = _solve_beta(high_dps, ETA_MAX_CHECK, digits)

    candidates = (beta_low, beta_high, beta_check)
    beta_texts = [_format_decimal(beta, digits) for beta in candidates]
    if len(set(beta_texts)) != 1:
        raise ArithmeticError(
            "beta_s disagrees between precision or truncation checks: %s"
            % ", ".join(beta_texts)
        )

    m_texts = [_format_decimal(_m_from_beta(beta), digits) for beta in candidates]
    if len(set(m_texts)) != 1:
        raise ArithmeticError(
            "m_s disagrees between precision or truncation checks: %s"
            % ", ".join(m_texts)
        )

    scipy_beta = _scipy_beta_check()
    if abs(scipy_beta - beta_high) > mp.mpf("5e-10"):
        raise ArithmeticError(
            "SciPy beta check failed: %s versus %s"
            % (mp.nstr(scipy_beta, 20), mp.nstr(beta_high, 20))
        )

    if not beta_texts[0].startswith("-0.198837735"):
        raise ArithmeticError("literature check failed for beta_s")

    return {
        "beta": beta_texts[0],
        "m": m_texts[0],
    }


def _ensure_cache(digits):
    if digits not in _CACHE:
        _CACHE[digits] = _values_for_digits(digits)
    return _CACHE[digits]


class FalknerSkanSeparationParameter(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE", TABLE)
    parameters = ("parameterisation",)
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def enumerate(self):
        for parameterisation in PARAMETERISATIONS:
            yield {"parameterisation": parameterisation}

    def value(self, params, digits):
        parameterisation = params["parameterisation"]
        if parameterisation not in PARAMETERISATIONS:
            raise ValueError("unknown parameterisation %r" % (parameterisation,))
        label = "$\\beta_s$" if parameterisation == "beta" else "$m_s$"
        return {
            "number": _ensure_cache(digits)[parameterisation],
            "param-latex": label,
        }


def self_check(digits=DIGITS):
    values = _ensure_cache(digits)
    print("self-check passed for %d entries" % (len(values),))
    print("beta_s = %s" % values["beta"])
    print("m_s = %s" % values["m"])


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
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
    generator = FalknerSkanSeparationParameter()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        self_check(generator.digits)
        print(fill_draft_once(
            generator,
            message="computed Falkner-Skan separation parameter",
        ))
    elif os.environ.get("NUMBERDB_PREVIEW") == "1" or "--preview" in sys.argv:
        print(generator.preview())
    else:
        self_check(generator.digits)
        if os.environ.get("NUMBERDB_API_KEY"):
            report = generator.verify(sample=None)
            print(report)
            sys.exit(0 if report.ok else 1)
        print("NUMBERDB_API_KEY is not set, so verify() was skipped")
