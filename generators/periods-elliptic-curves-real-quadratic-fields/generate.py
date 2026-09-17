r"""Periods of elliptic curves over real quadratic fields -- numberdb.org/T294.

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish

The generator reads ecnf-data's `curves` and `mwdata` files for the five real
quadratic fields with $D\in\{5,8,12,13,17\}$ at the pinned commit below. It
stores the `omega` column for every curve with conductor norm at most $60$,
keeping $35$ significant digits and adding the LMFDB curve label, conductor
ideal, rank and Weierstrass equation as the entry comment.
"""

import os
import sys
import urllib.request

import numberdb.sage as numberdb


SOURCE_COMMIT = "10b28418e80392032b106ea00e6c5aa109d28e7b"
SOURCE_BASE = (
    "https://raw.githubusercontent.com/JohnCremona/ecnf-data/"
    + SOURCE_COMMIT
    + "/RQF"
)
DISCRIMINANTS = (5, 8, 12, 13, 17)
CONDUCTOR_NORM_BOUND = 60


def source_file(kind, discriminant):
    name = f"{kind}.2.2.{discriminant}.1"
    mounted = os.path.join("/work", name)
    if os.path.exists(mounted):
        with open(mounted, encoding="utf8") as handle:
            return handle.read()
    with urllib.request.urlopen(f"{SOURCE_BASE}/{name}", timeout=60) as answer:
        return answer.read().decode("utf8")


def significant_decimal(text, digits):
    if "." not in text:
        return text
    sign = ""
    if text.startswith("-"):
        sign = "-"
        text = text[1:]
    before, after = text.split(".", 1)
    before_digits = len(before.lstrip("0"))
    if before_digits:
        keep = max(0, digits - before_digits)
    else:
        leading = 0
        while leading < len(after) and after[leading] == "0":
            leading += 1
        keep = leading + digits
    return sign + before + "." + after[:keep]


def equation_with_w(equation):
    return equation.replace("\\phi", "w")


class RealQuadraticEllipticCurvePeriods(numberdb.Generator):
    table = os.environ.get("NUMBERDB_TABLE", "T294")
    parameters = ("D", "conductor", "class", "curve")
    type = "R"
    digits = 35
    rigour = "heuristic (agreement-checked)"

    def _rows(self):
        if hasattr(self, "_cached_rows"):
            return self._cached_rows

        rows = []
        for discriminant in DISCRIMINANTS:
            curves = {}
            for line in source_file("curves", discriminant).splitlines():
                cols = line.split()
                key = tuple(cols[:4])
                curves[key] = {
                    "norm": int(cols[5]),
                    "ideal": cols[4],
                    "equation": equation_with_w(cols[10]),
                }

            for line in source_file("mwdata", discriminant).splitlines():
                cols = line.split()
                key = tuple(cols[:4])
                curve = curves[key]
                if curve["norm"] > CONDUCTOR_NORM_BOUND:
                    continue
                field_label, conductor, iso_class, curve_number = key
                label = f"{field_label}-{conductor}-{iso_class}{curve_number}"
                rows.append(
                    {
                        "D": int(field_label.split(".")[2]),
                        "conductor": conductor,
                        "class": iso_class,
                        "curve": int(curve_number),
                        "rank": int(cols[4]),
                        "omega": significant_decimal(cols[14], self.digits),
                        "label": label,
                        "ideal": curve["ideal"],
                        "equation": curve["equation"],
                    }
                )

        self._cached_rows = rows
        self._cached_by_key = {
            (row["D"], row["conductor"], row["class"], row["curve"]): row
            for row in rows
        }
        return rows

    def enumerate(self):
        for row in self._rows():
            yield {
                "D": row["D"],
                "conductor": row["conductor"],
                "class": row["class"],
                "curve": row["curve"],
            }

    def value(self, params, digits):
        self._rows()
        key = (
            int(params["D"]),
            str(params["conductor"]),
            str(params["class"]),
            int(params["curve"]),
        )
        row = self._cached_by_key[key]
        return {
            "number": row["omega"],
            "comment": (
                f"LMFDB curve {row['label']} has conductor ideal "
                f"${row['ideal']}$, rank ${row['rank']}$, and equation "
                f"${row['equation']}$."
            ),
        }


def main():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") == "1":
        numberdb.configure(api_key=sys.stdin.read().strip())

    generator = RealQuadraticEllipticCurvePeriods()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="filled from ecnf-data omega values"))
        return

    report = generator.verify(sample=None)
    print(report)
    raise SystemExit(0 if report.ok else 1)


if __name__ == "__main__":
    main()
