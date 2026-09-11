"""Real periods of genus 2 curves over Q -- numberdb.org/T213.

For a genus 2 curve C over Q with Jacobian A, this stores the real period
Omega_A as the LMFDB records it for C.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

The curve labels, equations and real periods are frozen from the LMFDB genus 2
curve database.  The generator transcribes 28 significant digits from the
LMFDB real_period field; the BSD fields in curve_data.py are used only for
independent consistency checks.
"""

import ast
import os
import sys

import numberdb.sage as numberdb

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from curve_data import CURVE_DATA  # noqa: E402

MAX_CONDUCTOR = 1000
WRITTEN_DIGITS = 28

_BY_LABEL = {record["label"]: record for record in CURVE_DATA}


def label_sort_key(label):
    conductor, family, discriminant, curve = label.split(".")
    return (int(conductor), family, int(discriminant), int(curve))


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def truncate_significant(text, digits=WRITTEN_DIGITS):
    """Return the decimal string cut to ``digits`` significant digits."""
    if digits <= 0:
        raise ValueError("digits must be positive")
    source = str(text).strip()
    sign = ""
    if source.startswith(("-", "+")):
        sign, source = source[0], source[1:]

    significant = 0
    seen_nonzero = False
    out = []
    for character in source:
        if character == ".":
            out.append(character)
            continue
        if not character.isdigit():
            raise ValueError("not a plain decimal: %r" % text)
        if seen_nonzero or character != "0":
            seen_nonzero = True
            significant += 1
        out.append(character)
        if significant == digits:
            break

    result = sign + "".join(out)
    return result[:-1] if result.endswith(".") else result


def _lmfdb_curve_url(label):
    conductor, family, discriminant, curve = label.split(".")
    return ("https://www.lmfdb.org/Genus2Curve/Q/%s/%s/%s/%s"
            % (conductor, family, discriminant, curve))


def _term(coefficient, power):
    coefficient = int(coefficient)
    if power == 0:
        body = str(abs(coefficient))
    elif power == 1:
        body = "x" if abs(coefficient) == 1 else "%d x" % abs(coefficient)
    else:
        body = ("x^%d" % power if abs(coefficient) == 1
                else "%d x^%d" % (abs(coefficient), power))
    return "-" if coefficient < 0 else "+", body


def _polynomial_text(coefficients):
    terms = [
        _term(coefficient, power)
        for power, coefficient in reversed(list(enumerate(coefficients)))
        if coefficient
    ]
    if not terms:
        return "0"

    first_sign, first_body = terms[0]
    pieces = [("-" if first_sign == "-" else "") + first_body]
    for sign, body in terms[1:]:
        pieces.append(" %s %s" % (sign, body))
    return "".join(pieces)


def _nonzero_terms(coefficients):
    return [(int(coefficient), power)
            for power, coefficient in enumerate(coefficients)
            if coefficient]


def _times_y_text(coefficient, power):
    coefficient = abs(int(coefficient))
    if power == 0:
        return "y" if coefficient == 1 else "%d y" % coefficient
    if power == 1:
        return "xy" if coefficient == 1 else "%d xy" % coefficient
    body = "x^%d y" % power
    return body if coefficient == 1 else "%d %s" % (coefficient, body)


def equation_text(record):
    f_coefficients, h_coefficients = ast.literal_eval(record["equation"])
    left = "y^2"
    h_terms = _nonzero_terms(h_coefficients)
    if len(h_terms) == 1:
        coefficient, power = h_terms[0]
        sign = " - " if coefficient < 0 else " + "
        left += sign + _times_y_text(coefficient, power)
    elif h_terms:
        h_text = _polynomial_text(h_coefficients)
        left += " + (%s)y" % h_text
    return "%s = %s" % (left, _polynomial_text(f_coefficients))


def entry_comment(record):
    return (
        "Curve HREF{%s}[LMFDB %s] has isogeny class %s and model $%s$."
        % (_lmfdb_curve_url(record["label"]), record["label"],
           record["class_label"], equation_text(record))
    )


class Genus2RealPeriods(numberdb.Generator):

    table = os.environ.get("NUMBERDB_TABLE", "T213")
    parameters = ("label",)
    type = "R"
    digits = WRITTEN_DIGITS
    rigour = "heuristic"
    files = ("generate.py", "curve_data.py")

    def enumerate(self, max_conductor=MAX_CONDUCTOR):
        for record in sorted(CURVE_DATA, key=lambda row: label_sort_key(row["label"])):
            if record["conductor"] <= max_conductor:
                yield {"label": record["label"]}

    def value(self, params, digits):
        record = _BY_LABEL[params["label"]]
        return {
            "number": truncate_significant(record["real_period"], digits),
            "comment": entry_comment(record),
        }


if __name__ == "__main__":
    _key_from_stdin()
    generator = Genus2RealPeriods()

    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(
            message=("genus 2 real periods from LMFDB for conductor <= %d")
                    % (MAX_CONDUCTOR,)))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
