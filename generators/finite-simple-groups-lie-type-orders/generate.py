"""Orders of finite simple groups of Lie type -- numberdb.org/T220

This generator stores exact integer orders for the simple groups in the
Lie-type part of the classification, including the Tits group. The parameter
q is the one used in the order formula: for example ${}^2A_n(q^2)$ is indexed
here by q, so the same group is also written PSU_{n+1}(q).

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The range is every listed Lie-type family with q <= 32 and order below
10^100, the Tits group, and every A_1(q) with prime-power q <= 1000.
"""

import os
import sys
from math import gcd

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = "T220"
Q_LIMIT = 32
A1_Q_LIMIT = 1000
ORDER_LIMIT = 10 ** 100
TITS_ORDER = 17971200

FAMILIES = (
    "A", "B", "C", "D",
    "E6", "E7", "E8", "F4", "G2",
    "2A", "2D", "2E6", "3D4",
    "2B2", "2F4", "2G2", "Tits",
)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def is_prime(n):
    if n < 2:
        return False
    if n % 2 == 0:
        return n == 2
    d = 3
    while d * d <= n:
        if n % d == 0:
            return False
        d += 2
    return True


def prime_powers(limit):
    powers = set()
    for p in range(2, limit + 1):
        if not is_prime(p):
            continue
        q = p
        while q <= limit:
            powers.add(q)
            q *= p
    return sorted(powers)


def suzuki_ree_qs(base, limit):
    out = []
    q = base ** 3
    while q <= limit:
        out.append(q)
        q *= base ** 2
    return out


def product(values):
    out = 1
    for value in values:
        out *= value
    return out


def order(family, n, q):
    if family == "A":
        return (q ** (n * (n + 1) // 2)
                * product(q ** (i + 1) - 1 for i in range(1, n + 1))
                // gcd(n + 1, q - 1))
    if family == "B" or family == "C":
        return (q ** (n * n)
                * product(q ** (2 * i) - 1 for i in range(1, n + 1))
                // gcd(2, q - 1))
    if family == "D":
        return (q ** (n * (n - 1)) * (q ** n - 1)
                * product(q ** (2 * i) - 1 for i in range(1, n))
                // gcd(4, q ** n - 1))
    if family == "E6":
        return (q ** 36
                * product(q ** i - 1 for i in (2, 5, 6, 8, 9, 12))
                // gcd(3, q - 1))
    if family == "E7":
        return (q ** 63
                * product(q ** i - 1 for i in (2, 6, 8, 10, 12, 14, 18))
                // gcd(2, q - 1))
    if family == "E8":
        return q ** 120 * product(q ** i - 1 for i in (2, 8, 12, 14, 18, 20, 24, 30))
    if family == "F4":
        return q ** 24 * product(q ** i - 1 for i in (2, 6, 8, 12))
    if family == "G2":
        return q ** 6 * (q ** 2 - 1) * (q ** 6 - 1)
    if family == "2A":
        return (q ** (n * (n + 1) // 2)
                * product(q ** (i + 1) - (-1) ** (i + 1) for i in range(1, n + 1))
                // gcd(n + 1, q + 1))
    if family == "2D":
        return (q ** (n * (n - 1)) * (q ** n + 1)
                * product(q ** (2 * i) - 1 for i in range(1, n))
                // gcd(4, q ** n + 1))
    if family == "2E6":
        return (q ** 36
                * product(q ** i - (-1) ** i for i in (2, 5, 6, 8, 9, 12))
                // gcd(3, q + 1))
    if family == "3D4":
        return q ** 12 * (q ** 8 + q ** 4 + 1) * (q ** 6 - 1) * (q ** 2 - 1)
    if family == "2B2":
        return q ** 2 * (q ** 2 + 1) * (q - 1)
    if family == "2F4":
        return q ** 12 * (q ** 6 + 1) * (q ** 4 - 1) * (q ** 3 + 1) * (q - 1)
    if family == "2G2":
        return q ** 3 * (q ** 3 + 1) * (q - 1)
    if family == "Tits":
        return TITS_ORDER
    raise ValueError("unknown family %s" % family)


def excluded(family, n, q):
    return (
        (family == "A" and n == 1 and q in (2, 3))
        or (family == "2A" and n == 2 and q == 2)
        or (family == "B" and n == 2 and q == 2)
        or (family == "G2" and q == 2)
        or (family in ("2B2", "2F4") and q == 2)
        or (family == "2G2" and q == 3)
    )


def rank_range(family):
    if family == "A":
        return range(1, 80)
    if family == "2A":
        return range(2, 80)
    if family == "B":
        return range(2, 80)
    if family == "C":
        return range(3, 80)
    if family in ("D", "2D"):
        return range(4, 80)
    fixed = {
        "E6": 6, "2E6": 6, "E7": 7, "E8": 8, "F4": 4, "G2": 2,
        "3D4": 4, "2B2": 2, "2G2": 2, "2F4": 4, "Tits": 4,
    }
    return range(fixed[family], fixed[family] + 1)


def qs_for_table(family, n):
    if family == "Tits":
        return [2]
    if family in ("2B2", "2F4"):
        return suzuki_ree_qs(2, Q_LIMIT)
    if family == "2G2":
        return suzuki_ree_qs(3, Q_LIMIT)
    limit = A1_Q_LIMIT if family == "A" and n == 1 else Q_LIMIT
    return prime_powers(limit)


def table_parameters():
    for family in FAMILIES:
        for n in rank_range(family):
            seen_below_limit = False
            for q in qs_for_table(family, n):
                if excluded(family, n, q):
                    continue
                value = order(family, n, q)
                if value >= ORDER_LIMIT and not (family == "A" and n == 1):
                    continue
                seen_below_limit = True
                yield {"family": family, "n": str(n), "q": str(q)}
            if family in ("A", "2A", "B", "C", "D", "2D") and not seen_below_limit:
                break


def group_name(family, n, q):
    if family == "A":
        return "$\\operatorname{PSL}_{%d}(%d)$" % (n + 1, q)
    if family == "2A":
        return "$\\operatorname{PSU}_{%d}(%d)$" % (n + 1, q)
    if family == "B":
        return "$B_%d(%d)$" % (n, q)
    if family == "C":
        return "$\\operatorname{PSp}_{%d}(%d)$" % (2 * n, q)
    if family == "D":
        return "$\\operatorname{P\\Omega}^{+}_{%d}(%d)$" % (2 * n, q)
    if family == "2D":
        return "$\\operatorname{P\\Omega}^{-}_{%d}(%d)$" % (2 * n, q)
    if family == "Tits":
        return "the Tits group ${}^2F_4(2)'$"
    if family in ("E6", "E7", "E8", "F4", "G2"):
        return "$%s(%d)$" % (family, q)
    if family == "2E6":
        return "${}^2E_6(%d^2)$" % q
    if family == "3D4":
        return "${}^3D_4(%d^3)$" % q
    if family == "2B2":
        return "${}^2B_2(%d)$" % q
    if family == "2G2":
        return "${}^2G_2(%d)$" % q
    if family == "2F4":
        return "${}^2F_4(%d)$" % q
    return "$%s_%d(%d)$" % (family, n, q)


def comment(family, n, q):
    parts = [group_name(family, n, q) + "."]
    if family == "A" and n == 1 and q in (4, 5):
        parts.append("This group is isomorphic to $A_5$.")
    if family == "A" and n == 1 and q == 7:
        parts.append("This group is isomorphic to $A_2(2)$.")
    if family == "A" and n == 1 and q == 9:
        parts.append("This group is isomorphic to $A_6$.")
    if family == "A" and n == 3 and q == 2:
        parts.append("This group is isomorphic to $A_8$.")
    if family == "2A" and n == 3 and q == 2:
        parts.append("This group is isomorphic to $B_2(3)$.")
    if family == "B" and n == 2 and q == 3:
        parts.append("This group is isomorphic to ${}^2A_3(2^2)$.")
    if family in ("B", "C") and n >= 3 and q % 2 == 0:
        other = "C" if family == "B" else "B"
        parts.append("It is isomorphic to the row %s_%d(%d)." % (other, n, q))
    if family in ("B", "C") and n >= 3 and q % 2 == 1:
        other = "C" if family == "B" else "B"
        parts.append("It has the same order as %s_%d(%d)." % (other, n, q))
    return " ".join(parts)


class LieTypeSimpleGroupOrders(numberdb.Generator):

    table = TABLE
    parameters = ("family", "n", "q")
    type = "Z"
    rigour = "exact"

    def enumerate(self):
        yield from table_parameters()

    def value(self, params, digits):
        family = str(params["family"])
        n = int(params["n"])
        q = int(params["q"])
        return {
            "number": ZZ(order(family, n, q)),
            "comment": comment(family, n, q),
        }


def fill_draft_once(generator, message):
    """Fill a fresh draft without the empty upsert probe."""
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

    for name, body in sorted(_source_files(generator).items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)

    return answer


if __name__ == "__main__":
    _key_from_stdin()
    generator = LieTypeSimpleGroupOrders()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="orders of finite simple groups of Lie type"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
