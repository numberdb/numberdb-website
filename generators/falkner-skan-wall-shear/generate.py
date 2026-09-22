"""Wall shear f''(0) of the Falkner-Skan wedge flows -- numberdb.org/T418.

This generator fills T418 with the upper-branch Falkner-Skan wall shear on the
two-decimal Hartree beta grid -0.19 <= beta <= 1.99. It stores both the
Hartree and wedge normalisations.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The Hartree value is found by shooting on f''(0). Each shooting residual is
computed by a constant-memory Taylor integration of the Falkner-Skan initial
value problem. The stored digits come from agreement between two Taylor
settings, one of them at higher working precision and smaller step size.
"""

import os
import sys

import mpmath as mp
import numberdb.sage as numberdb
from numberdb._write import to_text


TABLE = os.environ.get("NUMBERDB_TABLE", "T418")
DIGITS = 30
BETA_MIN = -19
BETA_MAX = 199
ETA_MAX = "18"

# The first upper-branch root, at beta = -0.19, is used only as a shooting
# starting point. The root is recomputed from the differential equation.
FIRST_ROOT_GUESS = "0.08569974405981233"

COARSE = {
    "dps": 70,
    "order": 60,
    "step": "0.05",
    "eta_max": ETA_MAX,
}
FINE = {
    "dps": 90,
    "order": 70,
    "step": "0.025",
    "eta_max": ETA_MAX,
}

# Literature values in the Hartree normalisation, used as external checks.
KNOWN_HARTREE = {
    "0.00": "0.469599988361",
    "0.50": "0.927680039837",
    "1.00": "1.232587656820",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _beta_label(hundredths):
    sign = "-" if hundredths < 0 else ""
    hundredths = abs(hundredths)
    return "%s%d.%02d" % (sign, hundredths // 100, hundredths % 100)


def _beta_value(label):
    return mp.mpf(label)


def _decimal_text(value, digits):
    text = mp.nstr(value, n=digits, strip_zeros=False, min_fixed=-6, max_fixed=100)
    if "." not in text and "e" not in text.lower():
        text += ".0"
    return text


def _taylor_integrate(beta, shear, config):
    """Integrate the Hartree Falkner-Skan IVP to eta_max."""
    with mp.workdps(config["dps"]):
        beta = mp.mpf(beta)
        h = mp.mpf(config["step"])
        eta_max = mp.mpf(config["eta_max"])
        order = int(config["order"])
        f = mp.mpf("0")
        fp = mp.mpf("0")
        fpp = mp.mpf(shear)

        def step(f, fp, fpp, step_h):
            a = [mp.mpf("0")] * (order + 1)
            b = [mp.mpf("0")] * (order + 1)
            c = [mp.mpf("0")] * (order + 1)
            a[0], b[0], c[0] = f, fp, fpp

            for k in range(order):
                a[k + 1] = b[k] / (k + 1)
                b[k + 1] = c[k] / (k + 1)
                ac = mp.fsum(a[i] * c[k - i] for i in range(k + 1))
                bb = mp.fsum(b[i] * b[k - i] for i in range(k + 1))
                forcing = 1 if k == 0 else 0
                c[k + 1] = (-ac - beta * (forcing - bb)) / (k + 1)

            hp = mp.mpf("1")
            nf = mp.mpf("0")
            nfp = mp.mpf("0")
            nfpp = mp.mpf("0")
            for k in range(order + 1):
                nf += a[k] * hp
                nfp += b[k] * hp
                nfpp += c[k] * hp
                hp *= step_h
            return nf, nfp, nfpp

        whole_steps = int(mp.floor(eta_max / h))
        remainder = eta_max - whole_steps * h
        for _ in range(whole_steps):
            f, fp, fpp = step(f, fp, fpp, h)
            if not (mp.isfinite(f) and mp.isfinite(fp) and mp.isfinite(fpp)):
                raise ArithmeticError("Taylor integration became non-finite")
            if abs(fp) > mp.mpf("1e30"):
                raise ArithmeticError("shooting trial diverged")
        if remainder:
            f, fp, fpp = step(f, fp, fpp, remainder)
        return f, fp, fpp


def _residual(beta, shear, config):
    return _taylor_integrate(beta, shear, config)[1] - 1


def _solve_root(beta, guess, config):
    """Secant shooting, with small bracketed fallbacks near the previous root."""
    with mp.workdps(config["dps"]):
        beta = mp.mpf(beta)
        guess = mp.mpf(guess)
        tolerance = mp.mpf(10) ** (-(DIGITS + 10))

        def residual(shear):
            return _residual(beta, shear, config)

        candidates = [
            (guess - mp.mpf("0.002"), guess + mp.mpf("0.002")),
            (guess - mp.mpf("0.005"), guess + mp.mpf("0.005")),
            (guess - mp.mpf("0.010"), guess + mp.mpf("0.010")),
            (guess - mp.mpf("0.020"), guess + mp.mpf("0.020")),
        ]
        for left, right in candidates:
            left = max(left, mp.mpf("1e-20"))
            try:
                root = mp.findroot(
                    residual, (left, right), tol=tolerance, verify=False, maxsteps=12
                )
                if root > 0 and abs(residual(root)) < mp.mpf(10) ** (-(DIGITS + 6)):
                    return +root
            except Exception:
                pass

        # Last resort: a bisection bracket close to the predictor. This is
        # slower but keeps the branch choice explicit.
        for width in ("0.01", "0.02", "0.04", "0.08"):
            width = mp.mpf(width)
            lo = max(guess - width, mp.mpf("1e-20"))
            hi = guess + width
            try:
                flo = residual(lo)
                fhi = residual(hi)
            except Exception:
                continue
            if flo == 0:
                return lo
            if fhi == 0:
                return hi
            if flo * fhi > 0:
                continue
            for _ in range(DIGITS + 20):
                mid = (lo + hi) / 2
                fmid = residual(mid)
                if abs(fmid) < mp.mpf(10) ** (-(DIGITS + 6)):
                    return +mid
                if flo * fmid <= 0:
                    hi = mid
                    fhi = fmid
                else:
                    lo = mid
                    flo = fmid
            return +((lo + hi) / 2)

    raise ArithmeticError("could not solve shooting problem at beta=%s" % beta)


class FalknerSkanWallShear(numberdb.Generator):
    table = TABLE
    parameters = ("beta", "branch", "normalisation")
    type = "R"
    digits = DIGITS
    rigour = "heuristic (agreement-checked)"

    def __init__(self):
        self._coarse_roots = {}
        self._coarse_last = None
        self._fine_roots = {}
        self._fine_last = None

    def enumerate(self, beta_min=BETA_MIN, beta_max=BETA_MAX):
        for hundredths in range(beta_min, beta_max + 1):
            beta = _beta_label(hundredths)
            yield {"beta": beta, "branch": "upper", "normalisation": "wedge"}
            yield {"beta": beta, "branch": "upper", "normalisation": "hartree"}

    def _next_guess(self, cache, state, hundredths):
        if hundredths == BETA_MIN:
            return mp.mpf(FIRST_ROOT_GUESS)
        last_hundredths, last_root, previous_root = state
        if previous_root is None:
            return last_root + mp.mpf("0.025")
        return last_root + (last_root - previous_root)

    def _root_with(self, hundredths, config, cache, state_name):
        state = getattr(self, state_name)
        while state is None or state[0] < hundredths:
            next_hundredths = BETA_MIN if state is None else state[0] + 1
            beta = _beta_value(_beta_label(next_hundredths))
            guess = self._next_guess(cache, state, next_hundredths)
            root = _solve_root(beta, guess, config)
            previous = None if state is None else state[1]
            state = (next_hundredths, root, previous)
            cache[next_hundredths] = root
            setattr(self, state_name, state)
        return cache[hundredths]

    def _hartree_root(self, beta_label):
        hundredths = int(mp.mpf(beta_label) * 100)
        coarse = self._root_with(hundredths, COARSE, self._coarse_roots, "_coarse_last")
        if hundredths not in self._fine_roots:
            fine = _solve_root(_beta_value(beta_label), coarse, FINE)
            self._fine_roots[hundredths] = fine
        fine = self._fine_roots[hundredths]
        tolerance = mp.mpf(10) ** (-(self.digits + 4)) * max(1, abs(fine))
        if abs(coarse - fine) > tolerance:
            raise ArithmeticError(
                "Taylor settings disagree at beta=%s: %s vs %s"
                % (beta_label, coarse, fine)
            )
        return fine

    def value(self, params, digits):
        if params["branch"] != "upper":
            raise ValueError("this draft fills only the upper branch")
        beta = params["beta"]
        hartree = self._hartree_root(beta)
        if params["normalisation"] == "hartree":
            return _decimal_text(hartree, digits)
        if params["normalisation"] == "wedge":
            factor = (mp.mpf("2") - _beta_value(beta)).sqrt()
            return _decimal_text(hartree / factor, digits)
        raise ValueError("unknown normalisation %r" % (params["normalisation"],))


def run_integrity_checks(generator):
    for beta, expected in KNOWN_HARTREE.items():
        got = mp.mpf(generator.value(
            {"beta": beta, "branch": "upper", "normalisation": "hartree"},
            DIGITS,
        ))
        if abs(got - mp.mpf(expected)) > mp.mpf("2e-12"):
            raise ArithmeticError(
                "published-value check failed at beta=%s: %s vs %s"
                % (beta, got, expected)
            )
    print("literature checks passed at beta=0.00, 0.50, 1.00")


def fill_draft_once(generator, message):
    """Fill a fresh prose draft without the client's empty upsert probe."""
    from numberdb._generate import (
        _check_precision,
        _check_rigour,
        _producer,
        _run_name,
        _source_files,
    )
    from numberdb._write import Entries, attach, submit_entries

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
    generator = FalknerSkanWallShear()
    run_integrity_checks(generator)
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Falkner-Skan upper-branch wall shear for two-decimal beta"))
    elif os.environ.get("NUMBERDB_INTEGRITY_ONLY") == "1":
        print("integrity-only run complete")
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
