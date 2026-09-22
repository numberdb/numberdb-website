"""Madelung constants of the ionic crystal structures -- numberdb.org/T403.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The table stores the positive Madelung constants in the nearest-neighbour
normalisation used in lattice-energy calculations. The generator evaluates a
neutral-cell Ewald sum in ball arithmetic and adds explicit real-space and
reciprocal-space tail bounds.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


TABLE = os.environ.get("NUMBERDB_TABLE", "T403")

DIGITS = 100
WORKING_GUARD = 160
EWALD_ALPHA = QQ(4)


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _real_field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _as_R(R, value):
    try:
        if value.parent() is R:
            return value
    except AttributeError:
        pass
    return R(value)


def dot(u, v):
    return sum(a * b for a, b in zip(u, v))


def cross(u, v):
    return [
        u[1] * v[2] - u[2] * v[1],
        u[2] * v[0] - u[0] * v[2],
        u[0] * v[1] - u[1] * v[0],
    ]


def matrix_vector_columns(matrix, vector):
    return [
        sum(matrix[i][j] * vector[j] for j in range(3))
        for i in range(3)
    ]


def norm(vector, R):
    return R(dot(vector, vector)).sqrt()


def reciprocal_columns(A, R):
    a = [A[i][0] for i in range(3)]
    b = [A[i][1] for i in range(3)]
    c = [A[i][2] for i in range(3)]
    volume = dot(a, cross(b, c))
    two_pi = 2 * R.pi()
    columns = []
    for vector in (cross(b, c), cross(c, a), cross(a, b)):
        columns.append([two_pi * entry / volume for entry in vector])
    return [[columns[j][i] for j in range(3)] for i in range(3)], volume.abs()


def erfc(x):
    return 1 - x.erf()


def enlarge(ball, radius):
    widened = ball.add_error(radius)
    return ball if widened is None else widened


def shell_count(m):
    return (2 * m + 1) ** 3 - (2 * m - 1) ** 3


def real_tail_bound(R, alpha, q_abs, lower, cutoff):
    lower = R(lower)
    total = R(0)
    # For omitted translations with max norm m, the fractional displacement
    # between two sites moves by less than one cell in each coordinate.
    for m in range(cutoff + 1, cutoff + 81):
        radius = lower * R(m - 1)
        total += R(shell_count(m)) * erfc(alpha * radius) / radius
    return R(QQ(1) / QQ(2)) * R(q_abs) ** 2 * total + R("1e-170")


def reciprocal_tail_bound(R, alpha, q_abs, lower, cutoff):
    lower = R(lower)
    c = lower ** 2 / (4 * alpha ** 2)
    total = R(0)
    for m in range(cutoff + 1, cutoff + 81):
        total += (
            R(shell_count(m))
            * (-c * R(m) ** 2).exp()
            / (lower ** 2 * R(m) ** 2)
        )
    m = R(cutoff + 81)
    integral_tail = (
        R(25)
        * (-c * (m - 1) ** 2).exp()
        / (lower ** 2 * 2 * c * (m - 1))
    )
    return 2 * R.pi() * R(q_abs) ** 2 * (total + integral_tail)


def ewald_energy(R, A, basis, real_cut, recip_cut):
    alpha = R(EWALD_ALPHA)
    B, volume = reciprocal_columns(A, R)
    positions = [position for position, charge in basis]
    charges = [R(charge) for position, charge in basis]

    real_sum = R(0)
    for ix in range(-real_cut, real_cut + 1):
        for iy in range(-real_cut, real_cut + 1):
            for iz in range(-real_cut, real_cut + 1):
                translate = matrix_vector_columns(A, (ix, iy, iz))
                for i, ri in enumerate(positions):
                    for j, rj in enumerate(positions):
                        if i == j and ix == iy == iz == 0:
                            continue
                        delta = [
                            ri[k] - rj[k] + translate[k]
                            for k in range(3)
                        ]
                        distance = norm(delta, R)
                        real_sum += (
                            charges[i]
                            * charges[j]
                            * erfc(alpha * distance)
                            / distance
                        )
    real_sum *= R(QQ(1) / QQ(2))

    recip_sum = R(0)
    for hx in range(-recip_cut, recip_cut + 1):
        for hy in range(-recip_cut, recip_cut + 1):
            for hz in range(-recip_cut, recip_cut + 1):
                if hx == hy == hz == 0:
                    continue
                kvec = matrix_vector_columns(B, (hx, hy, hz))
                k2 = dot(kvec, kvec)
                rho_re = R(0)
                rho_im = R(0)
                for r, q in zip(positions, charges):
                    phase = dot(kvec, r)
                    rho_re += q * phase.cos()
                    rho_im += q * phase.sin()
                rho2 = rho_re ** 2 + rho_im ** 2
                recip_sum += (-k2 / (4 * alpha ** 2)).exp() * rho2 / k2
    recip_sum *= 2 * R.pi() / volume

    self_sum = -alpha / R.pi().sqrt() * sum(q ** 2 for q in charges)
    return real_sum + recip_sum + self_sum


def cubic_cell(R):
    return [
        [R(1), R(0), R(0)],
        [R(0), R(1), R(0)],
        [R(0), R(0), R(1)],
    ]


def cartesian(A, fractional):
    return matrix_vector_columns(A, fractional)


def fcc_positions():
    return (
        (QQ(0), QQ(0), QQ(0)),
        (QQ(0), QQ(1) / QQ(2), QQ(1) / QQ(2)),
        (QQ(1) / QQ(2), QQ(0), QQ(1) / QQ(2)),
        (QQ(1) / QQ(2), QQ(1) / QQ(2), QQ(0)),
    )


def cubic_structure(R, records):
    A = cubic_cell(R)
    return A, [(cartesian(A, position), charge) for position, charge in records]


def rock_salt(R):
    records = []
    for position in fcc_positions():
        records.append((position, 1))
    for position in (
        (QQ(1) / QQ(2), QQ(0), QQ(0)),
        (QQ(0), QQ(1) / QQ(2), QQ(0)),
        (QQ(0), QQ(0), QQ(1) / QQ(2)),
        (QQ(1) / QQ(2), QQ(1) / QQ(2), QQ(1) / QQ(2)),
    ):
        records.append((position, -1))
    return cubic_structure(R, records)


def caesium_chloride(R):
    return cubic_structure(R, [
        ((QQ(0), QQ(0), QQ(0)), 1),
        ((QQ(1) / QQ(2), QQ(1) / QQ(2), QQ(1) / QQ(2)), -1),
    ])


def zincblende(R):
    records = []
    for position in fcc_positions():
        records.append((position, 1))
    for position in fcc_positions():
        records.append((
            (
                position[0] + QQ(1) / QQ(4),
                position[1] + QQ(1) / QQ(4),
                position[2] + QQ(1) / QQ(4),
            ),
            -1,
        ))
    return cubic_structure(R, records)


def fluorite(R):
    records = []
    for position in fcc_positions():
        records.append((position, 2))
    for x in (QQ(1) / QQ(4), QQ(3) / QQ(4)):
        for y in (QQ(1) / QQ(4), QQ(3) / QQ(4)):
            for z in (QQ(1) / QQ(4), QQ(3) / QQ(4)):
                records.append(((x, y, z), -1))
    return cubic_structure(R, records)


def antifluorite(R):
    A, basis = fluorite(R)
    return A, [(position, -charge) for position, charge in basis]


def cuprite(R):
    return cubic_structure(R, [
        ((QQ(0), QQ(0), QQ(0)), -2),
        ((QQ(1) / QQ(2), QQ(1) / QQ(2), QQ(1) / QQ(2)), -2),
        ((QQ(1) / QQ(4), QQ(1) / QQ(4), QQ(1) / QQ(4)), 1),
        ((QQ(1) / QQ(4), QQ(3) / QQ(4), QQ(3) / QQ(4)), 1),
        ((QQ(3) / QQ(4), QQ(1) / QQ(4), QQ(3) / QQ(4)), 1),
        ((QQ(3) / QQ(4), QQ(3) / QQ(4), QQ(1) / QQ(4)), 1),
    ])


def wurtzite(R):
    root3 = R(3).sqrt()
    c_over_a = R(QQ(8) / QQ(3)).sqrt()
    A = [
        [R(1), -R(QQ(1) / QQ(2)), R(0)],
        [R(0), root3 / 2, R(0)],
        [R(0), R(0), c_over_a],
    ]
    u = QQ(3) / QQ(8)
    records = [
        ((QQ(0), QQ(0), QQ(0)), 1),
        ((QQ(2) / QQ(3), QQ(1) / QQ(3), QQ(1) / QQ(2)), 1),
        ((QQ(0), QQ(0), u), -1),
        ((QQ(2) / QQ(3), QQ(1) / QQ(3), QQ(1) / QQ(2) + u), -1),
    ]
    return A, [(cartesian(A, position), charge) for position, charge in records]


STRUCTURES = {
    "rock-salt": {
        "build": rock_salt,
        "formula_units": 4,
        "nearest_squared": QQ(1) / QQ(4),
        "comment": "the structure type of sodium chloride",
        "real_lower": QQ(1),
        "real_cut": 6,
        "recip_lower": QQ(6),
        "recip_cut": 22,
    },
    "caesium-chloride": {
        "build": caesium_chloride,
        "formula_units": 1,
        "nearest_squared": QQ(3) / QQ(4),
        "comment": "the structure type of caesium chloride",
        "real_lower": QQ(1),
        "real_cut": 6,
        "recip_lower": QQ(6),
        "recip_cut": 22,
    },
    "zincblende": {
        "build": zincblende,
        "formula_units": 4,
        "nearest_squared": QQ(3) / QQ(16),
        "comment": "the sphalerite structure type of zinc sulfide",
        "real_lower": QQ(1),
        "real_cut": 6,
        "recip_lower": QQ(6),
        "recip_cut": 22,
    },
    "fluorite": {
        "build": fluorite,
        "formula_units": 4,
        "nearest_squared": QQ(3) / QQ(16),
        "comment": "the structure type of calcium fluoride",
        "real_lower": QQ(1),
        "real_cut": 6,
        "recip_lower": QQ(6),
        "recip_cut": 22,
    },
    "antifluorite": {
        "build": antifluorite,
        "formula_units": 4,
        "nearest_squared": QQ(3) / QQ(16),
        "comment": (
            "the anti-fluorite structure has the same value as fluorite "
            "because all formal charges are multiplied by $-1$"
        ),
        "equals": "HREF{#fluorite}",
        "real_lower": QQ(1),
        "real_cut": 6,
        "recip_lower": QQ(6),
        "recip_cut": 22,
    },
    "cuprite": {
        "build": cuprite,
        "formula_units": 2,
        "nearest_squared": QQ(3) / QQ(16),
        "comment": "the structure type of cuprous oxide",
        "real_lower": QQ(1),
        "real_cut": 6,
        "recip_lower": QQ(6),
        "recip_cut": 22,
    },
    "wurtzite": {
        "build": wurtzite,
        "formula_units": 2,
        "nearest_squared": QQ(3) / QQ(8),
        "comment": "the ideal wurtzite structure with $c/a=\\sqrt{8/3}$ and $u=3/8$",
        "real_lower": QQ(2) / QQ(3),
        "real_cut": 8,
        "recip_lower": QQ(15) / QQ(4),
        "recip_cut": 38,
    },
}


def madelung_constant(structure, digits=DIGITS):
    R = _real_field(digits)
    data = STRUCTURES[structure]
    A, basis = data["build"](R)
    energy = ewald_energy(R, A, basis, data["real_cut"], data["recip_cut"])
    q_abs = sum(abs(charge) for position, charge in basis)
    real_tail = real_tail_bound(
        R, R(EWALD_ALPHA), q_abs, data["real_lower"], data["real_cut"])
    recip_tail = reciprocal_tail_bound(
        R, R(EWALD_ALPHA), q_abs, data["recip_lower"], data["recip_cut"])
    nearest = R(data["nearest_squared"]).sqrt()
    scale = nearest / R(data["formula_units"])
    value = -energy * scale
    return enlarge(value, (real_tail + recip_tail) * scale)


def _cosh(x):
    return (x.exp() + (-x).exp()) / 2


def rock_salt_benson(digits=DIGITS, cutoff=80):
    R = _real_field(digits)
    pi = R.pi()
    total = R(0)
    for m in range(1, cutoff + 1, 2):
        for n in range(1, cutoff + 1, 2):
            x = (pi / 2) * R(m * m + n * n).sqrt()
            total += 1 / (_cosh(x) ** 2)
    value = 12 * pi * total
    return enlarge(value, R("1e-105"))


def check_identities(digits=DIGITS):
    ewald = madelung_constant("rock-salt", digits)
    benson = rock_salt_benson(digits)
    if not (ewald - benson).contains_zero():
        raise ArithmeticError("rock-salt Ewald sum and Benson series disagree")

    prefixes = {
        "rock-salt": "1.747564594633182190636212035",
        "caesium-chloride": "1.762674773070",
        "zincblende": "1.638055053388",
        "fluorite": "5.038784879848",
        "cuprite": "4.44247",
        "wurtzite": "1.641321627371",
    }
    for structure, prefix in prefixes.items():
        text = str(madelung_constant(structure, digits).center())
        if not text.startswith(prefix):
            raise ArithmeticError(
                "%s: expected prefix %s, got %s"
                % (structure, prefix, text[:len(prefix) + 6]))
    print("checked rock-salt against Benson's series")
    print("checked %d published prefixes" % len(prefixes))


class MadelungConstantsIonicCrystalStructures(numberdb.Generator):
    table = TABLE
    parameters = ("structure",)
    type = "R"
    digits = DIGITS
    rigour = "proven"
    files = ("generate.py",)

    def enumerate(self):
        for structure in STRUCTURES:
            yield {"structure": structure}

    def value(self, params, digits):
        structure = params["structure"]
        data = STRUCTURES[structure]
        entry = {
            "number": madelung_constant(structure, digits),
            "comment": data["comment"],
        }
        if "equals" in data:
            entry["equals"] = data["equals"]
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

    files = _source_files(generator)
    stored = []
    for name, body in sorted(files.items()):
        attach(table, name, body, run=run, message=message,
               rigour=generator.rigour)
        stored.append(name)

    return {
        "tid": answer.get("tid", table),
        "revision": answer.get("revision"),
        "entries": len(entries),
        "files": stored,
    }


if __name__ == "__main__":
    _key_from_stdin()
    generator = MadelungConstantsIonicCrystalStructures()
    if os.environ.get("NUMBERDB_CHECK_IDENTITIES") == "1":
        check_identities(generator.digits)
    elif "--publish" in sys.argv or os.environ.get("NUMBERDB_PUBLISH") == "1":
        print(fill_draft_once(
            generator,
            message="Madelung constants from Ewald sums"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
