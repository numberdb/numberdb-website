"""Satisfiability thresholds of random $k$-SAT -- numberdb.org/T277.

For k >= 3, alpha_s(k) is the one-step replica-symmetry-breaking
cavity-method prediction for the satisfiability threshold of random k-SAT,
with density alpha = m/n clauses per variable. Mertens, Mezard and Zecchina
tabulate these values as alpha_c for k = 3..7; this table uses alpha_s(k),
the notation of Krzakala, Montanari, Ricci-Tersenghi, Semerjian and
Zdeborova for the SAT-UNSAT threshold.

This generator transcribes the published values:

    k = 3: 4.26675 +/- 0.00015 from MMZ Eq. (43)
    k = 4..7: 9.931, 21.117, 43.37, 87.79 from MMZ Table 1

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are heuristic because they come from the cavity-method population
dynamics calculation. The rows k = 4, 5, 6 were checked against the rounded
values in Krzakala et al. Table 1, and every row was compared with the
large-k asymptotic 2^k log(2) - (1 + log(2))/2.
"""

import os
import sys

import numberdb.sage as numberdb
from numberdb._compare import digits_of


TABLE = os.environ.get("NUMBERDB_TABLE", "T277")

VALUES = {
    3: "4.26675 +/- 0.00015",
    4: "9.931",
    5: "21.117",
    6: "43.37",
    7: "87.79",
}

COMMENTS = {
    3: (
        r"Mertens, Mezard and Zecchina give "
        r"$\alpha_s(3)=4.26675\pm0.00015$ in Eq. (43), using the notation "
        r"$\alpha_c$ for the satisfiability threshold CITE{MMZ}."
    ),
    4: (
        r"Mertens, Mezard and Zecchina print $9.931$ CITE{MMZ}; "
        r"Krzakala, Montanari, Ricci-Tersenghi, Semerjian and Zdeborova "
        r"round it to $9.93$ CITE{KMRTSZ}."
    ),
    5: (
        r"Mertens, Mezard and Zecchina print $21.117$ CITE{MMZ}; "
        r"Krzakala, Montanari, Ricci-Tersenghi, Semerjian and Zdeborova "
        r"round it to $21.12$ CITE{KMRTSZ}."
    ),
    6: (
        r"Mertens, Mezard and Zecchina print $43.37$ CITE{MMZ}; "
        r"Krzakala, Montanari, Ricci-Tersenghi, Semerjian and Zdeborova "
        r"round it to $43.4$ CITE{KMRTSZ}."
    ),
    7: (
        r"Mertens, Mezard and Zecchina print $87.79$ CITE{MMZ}."
    ),
}

KRZAKALA_ROUNDED = {
    4: "9.93",
    5: "21.12",
    6: "43.4",
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def check_against_krzakala():
    """Return complaints if the source cross-check no longer matches."""
    from decimal import Decimal, ROUND_HALF_UP

    complaints = []
    for k, expected in KRZAKALA_ROUNDED.items():
        places = abs(Decimal(expected).as_tuple().exponent)
        rounded = Decimal(VALUES[k]).quantize(
            Decimal(1).scaleb(-places),
            rounding=ROUND_HALF_UP,
        )
        if format(rounded, "f") != expected:
            complaints.append(
                "k=%d: %s rounds to %s, not %s"
                % (k, VALUES[k], format(rounded, "f"), expected)
            )
    return complaints


def large_k_leading(k):
    """The leading large-k prediction used only as a scale check."""
    from decimal import Decimal, localcontext

    with localcontext() as context:
        context.prec = 60
        log_two = Decimal(2).ln()
        return (Decimal(2) ** k) * log_two - (Decimal(1) + log_two) / 2


def asymptotic_differences():
    """Absolute differences from the leading large-k expression."""
    from decimal import Decimal

    out = {}
    for k, text in VALUES.items():
        centre = text.split("+/-", 1)[0].strip()
        out[k] = abs(Decimal(centre) - large_k_leading(k))
    return out


class RandomKSATSatisfiabilityThresholds(numberdb.Generator):

    table = TABLE
    parameters = ("k",)
    type = "R"
    digits = 5
    rigour = "heuristic"

    def enumerate(self):
        for k in sorted(VALUES):
            yield {"k": str(k)}

    def value(self, params, digits):
        k = int(params["k"])
        text = VALUES[k]
        return {
            "number": text,
            "digits": digits_of(text),
            "comment": COMMENTS[k],
        }


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

        written = to_text(value, entry.get("digits", wanted), generator.format)
        _check_precision(table, identity, written, entry.get("digits", wanted), lowering=False)

        record = dict(entry)
        record.pop("digits", None)
        entries.add(**params, **record, digits=entry.get("digits", wanted))

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
    generator = RandomKSATSatisfiabilityThresholds()
    if "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message=(
                "random k-SAT cavity-method satisfiability thresholds for 3 <= k <= 7, "
                "transcribed from MMZ and checked against Krzakala et al."
            ),
        ))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
