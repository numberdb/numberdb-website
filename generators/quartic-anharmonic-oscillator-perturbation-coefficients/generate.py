"""Quartic anharmonic oscillator perturbation coefficients -- numberdb.org/T406

For the Bender-Wu Hamiltonian

    H(g) = p^2/2 + x^2/2 + g x^4,

this table stores the exact rational coefficients E_n^(k) in

    E_n(g) ~ sum_{k >= 0} E_n^(k) g^k.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The recurrence works in the unnormalised oscillator basis (a^dagger)^m |0>.
There a lowers with coefficient m and a^dagger raises with coefficient 1, so
x^4 = (a + a^dagger)^4 / 4 has rational matrix entries. The intermediate
wavefunction coefficients and every stored energy coefficient are therefore
computed exactly over QQ.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ


MAX_N = 2
MAX_K = 100

_CACHE = {}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _b_times(vector):
    """Apply a + a^dagger in the unnormalised oscillator basis."""
    out = {}
    for m, coefficient in vector.items():
        if m > 0:
            out[m - 1] = out.get(m - 1, QQ(0)) + coefficient * QQ(m)
        out[m + 1] = out.get(m + 1, QQ(0)) + coefficient
    return {m: c for m, c in out.items() if c}


def _x4_times(vector):
    out = dict(vector)
    for _ in range(4):
        out = _b_times(out)
    return {m: c / QQ(4) for m, c in out.items() if c}


def _energy_coefficients(level, order):
    level = int(level)
    order = int(order)
    if level < 0:
        raise ValueError("level must be nonnegative")
    if order < 0:
        raise ValueError("order must be nonnegative")

    cached = _CACHE.get(level)
    if cached is not None and len(cached) > order:
        return cached

    energies = [QQ(level) + QQ(1) / QQ(2)]
    wavefunctions = [{level: QQ(1)}]

    for k in range(1, order + 1):
        acted = _x4_times(wavefunctions[k - 1])
        energy = acted.get(level, QQ(0))
        energies.append(energy)

        support = set(acted)
        for previous in wavefunctions[1:]:
            support.update(previous)

        next_wavefunction = {}
        for m in sorted(support):
            if m == level:
                continue
            numerator = -acted.get(m, QQ(0))
            for j in range(1, k + 1):
                numerator += energies[j] * wavefunctions[k - j].get(m, QQ(0))
            coefficient = numerator / QQ(m - level)
            if coefficient:
                next_wavefunction[m] = coefficient

        if next_wavefunction.get(level, QQ(0)):
            raise ArithmeticError("normalisation failed at level %d order %d" % (level, k))
        wavefunctions.append(next_wavefunction)

    _check_first_order(level, energies)
    _check_signs(level, energies)
    _CACHE[level] = energies
    return energies


def _check_first_order(level, energies):
    if len(energies) < 2:
        return
    expected = QQ(3) * QQ(2 * level * level + 2 * level + 1) / QQ(4)
    if energies[1] != expected:
        raise ArithmeticError("first-order coefficient disagrees for n=%d" % level)


def _check_signs(level, energies):
    for k, value in enumerate(energies[1:], 1):
        if value == 0:
            raise ArithmeticError("unexpected zero coefficient for n=%d k=%d" % (level, k))
        if (k % 2 == 1 and value <= 0) or (k % 2 == 0 and value >= 0):
            raise ArithmeticError("unexpected sign for n=%d k=%d" % (level, k))


def coefficient(level, order):
    return _energy_coefficients(level, order)[order]


class QuarticAnharmonicOscillatorPerturbation(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T406")
    parameters = ("n", "k")
    type = "Q"
    rigour = "exact"

    def enumerate(self, max_n=MAX_N, max_k=MAX_K):
        for n in range(max_n + 1):
            for k in range(max_k + 1):
                yield {"n": str(n), "k": str(k)}

    def value(self, params, digits):
        return coefficient(int(params["n"]), int(params["k"]))


if __name__ == "__main__":
    _key_from_stdin()
    generator = QuarticAnharmonicOscillatorPerturbation()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="computed exact quartic perturbation coefficients"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
