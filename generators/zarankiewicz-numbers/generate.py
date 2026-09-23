"""Zarankiewicz numbers z(m,n;s,t) -- numberdb.org/T442

For positive integers m, n, s and t, this stores the maximum number of edges in
a subgraph of K_{m,n} with no K_{s,t} subgraph. The current range is diagonal:
z(m,n;s,s), stored with m <= n.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # fill the draft, with NUMBERDB_API_KEY set

The values are exact integers, except for z(32,32;2,2), which is the integer
interval [189, 190] as written in the source table. The tables for 3 <= s <= 6
are parsed from the source LaTeX rows below; only entries marked as bold in the
paper are stored, because the unbolded entries are one-sided upper bounds.
"""

import os
import re
import sys

import numberdb.sage as numberdb
from sage.rings.integer_ring import ZZ


TABLE = os.environ.get("NUMBERDB_TABLE", "T442")


Z_N_2 = {
    1: 1,
    2: 3,
    3: 6,
    4: 9,
    5: 12,
    6: 16,
    7: 21,
    8: 24,
    9: 29,
    10: 34,
    11: 39,
    12: 45,
    13: 52,
    14: 56,
    15: 61,
    16: 67,
    17: 74,
    18: 81,
    19: 88,
    20: 96,
    21: 105,
    22: 108,
    23: 115,
    24: 122,
    25: 130,
    26: 138,
    27: 147,
    28: 156,
    29: 165,
    30: 175,
    31: 186,
    32: "[189, 190]",
}


SOURCE_ROWS = {
    3: r"""
      6 & \mathbf{26}^\ast & \mathbf{29} & \mathbf{32} & \mathbf{36}^\ast & \mathbf{39}^\ast & \mathbf{42} & \mathbf{45}^\ast & \mathbf{48}^\ast & \mathbf{50} & \mathbf{53} & \mathbf{56} & \mathbf{58} & 61\\\hline
      7 & & \mathbf{33}^\ast & \mathbf{37}^\ast & \mathbf{40} & \mathbf{44}^\ast & \mathbf{47} & \mathbf{50} & \mathbf{53} & \mathbf{56} & \mathbf{60}^\ast & \mathbf{63}^\ast & \mathbf{66} & 69 \\\cline{0-0}\cline{3-14}
      8 & \multicolumn{2}{|c|}{} & \mathbf{42}^\ast & \mathbf{45} & \mathbf{50}^\ast & \mathbf{53} & \mathbf{57}^\ast & \mathbf{60} & \mathbf{64}^\ast & \mathbf{67} & \mathbf{70} & \mathbf{74}^\ast & 78 \\\cline{0-0}\cline{4-14}
      9 & \multicolumn{3}{|c|}{} & \mathbf{49} & \mathbf{54} & \mathbf{59}^\ast & \mathbf{64}^\ast & \mathbf{67}^\ast & \mathbf{70} & \mathbf{73} & \mathbf{77} & \mathbf{81} & 85 \\\cline{0-0}\cline{5-14}
      10 & \multicolumn{4}{|c|}{} & \mathbf{60}^\dagger & \mathbf{64}^\ast & \mathbf{68} & \mathbf{73}^\ast & \mathbf{77} & \mathbf{81}^\ast & \mathbf{85}^\ast & \mathbf{90}^\ast & 94 \\\cline{0-0}\cline{6-14}
      11 & \multicolumn{5}{|c|}{} & \mathbf{69}^\ast & \mathbf{74} & \mathbf{80} & \mathbf{84} & \mathbf{88} & \mathbf{92} & \mathbf{96} & 101\\\cline{0-0}\cline{7-14}
      12 & \multicolumn{6}{|c|}{} & \mathbf{80} & \mathbf{86}^\ast & \mathbf{91}^\ast & \mathbf{96} & \mathbf{99} & \mathbf{103}^\ast & 109 \\\cline{0-0}\cline{8-14}
      13 & \multicolumn{7}{|c|}{} & \mathbf{92}^\ast & \mathbf{98}^\ast & \mathbf{104}^\ast & \mathbf{107} & \mathit{110} & 116\\\cline{0-0}\cline{9-14}
      14 & \multicolumn{8}{|c|}{} & \mathbf{105}^\ast & \mathbf{112}^\ast & \mathbf{115}^\ast & 118 & 124 \\\cline{0-0}\cline{10-14}
      15 & \multicolumn{9}{|c|}{} & \mathbf{120}^\dagger & \mathbf{123}^\ast & 126 & 132\\\cline{0-0}\cline{11-14}
      16 & \multicolumn{10}{|c|}{} & \mathbf{128}^\ast & \it{133} & 140 \\\cline{0-0}\cline{12-14}
      17 & \multicolumn{11}{|c|}{} & 141 & 148 \\\cline{0-0}\cline{13-14}
      18 & \multicolumn{12}{|c|}{} & 156 \\\cline{0-0}\cline{14-14}
    """,
    4: r"""
      6 & \mathbf{31}^\ast & \mathbf{36}^\ast & \mathbf{39} & \mathbf{43} & \mathbf{47} & \mathbf{51} & \mathbf{55} & \mathbf{59} & \mathbf{63} & \mathbf{67} & \mathbf{71}^\ast & \mathbf{75}^\ast & \mathbf{78}\\\hline
      7 & & \mathbf{42}^\dagger & \mathbf{45} & \mathbf{49} & \mathbf{54} & \mathbf{58} & \mathbf{63} & \mathbf{68}^\ast & \mathbf{72} & \mathbf{77} & \mathbf{82}^\ast & \mathbf{87^\ast} & \mathbf{90}\\\cline{0-0}\cline{3-14}
      8 & \multicolumn{2}{|c|}{} & \mathbf{51}^\ast & \mathbf{55} & \mathbf{60} & \mathbf{65} & \mathbf{70} & \mathbf{75} & \mathbf{80} & \mathbf{85} & \mathbf{90} & \mathbf{95}^\ast & \mathbf{99} \\\cline{0-0}\cline{4-14}
      9 & \multicolumn{3}{|c|}{} & \mathbf{61} & \mathbf{67} & \mathbf{72} & \mathbf{78}^\ast & \mathbf{84}^\ast & \mathbf{88} & \mathbf{94} & \mathbf{99} & \mathbf{104} & \mathit{109} \\\cline{0-0}\cline{5-14}
      10 & \multicolumn{4}{|c|}{} & \mathbf{74}^\ast & \mathbf{79} & \mathbf{86}^\ast & \mathbf{93}^\ast & \mathbf{97} & \mathbf{103} & \mathbf{109} & \mathbf{115} & \mathbf{120} \\\cline{0-0}\cline{6-14}
      11 & \multicolumn{5}{|c|}{} & \mathbf{86} & \mathbf{93}^\ast & \mathbf{100}^\ast & \mathbf{105} & \mathbf{111} & \mathit{117} & 124 & 131 \\\cline{0-0}\cline{7-14}
      12 & \multicolumn{6}{|c|}{} & 101 & 109 & 114 & 121 & 127 & 134 & 141 \\\cline{0-0}\cline{8-14}
      13 & \multicolumn{7}{|c|}{} & 118 & 123 & 131 & 137 & 145 & 152\\\cline{0-0}\cline{9-14}
      14 & \multicolumn{8}{|c|}{} & 132 & 141 & 147 & 156 & 163 \\\cline{0-0}\cline{10-14}
      15 & \multicolumn{9}{|c|}{} & 151 & 157 & 166 & 174\\\cline{0-0}\cline{11-14}
      16 & \multicolumn{10}{|c|}{} & 167 & 177 & 185\\\cline{0-0}\cline{12-14}
      17 & \multicolumn{11}{|c|}{} & 188 & 196 \\\cline{0-0}\cline{13-14}
      18 & \multicolumn{12}{|c|}{} & 207 \\\cline{0-0}\cline{14-14}
    """,
    5: r"""
      6 & \mathbf{33}^\ast & \mathbf{38}^\ast & \mathbf{43}^\ast & \mathbf{48}^\ast & \mathbf{52} & \mathbf{57} & \mathbf{62} & \mathbf{67}^\ast & \mathbf{72}^\ast & \mathbf{76} & \mathbf{81} & \mathbf{86} & 91 \\\hline
      7 & & \mathbf{44}^\ast & \mathbf{50}^\ast & \mathbf{56}^\ast & \mathbf{60} & \mathbf{66} & \mathbf{72} & \mathbf{78}^\ast & \mathbf{84}^\dagger & \mathbf{88} & \mathbf{92}^\ast & \mathbf{96} & 101\\\cline{0-0}\cline{3-14}
      8 & \multicolumn{2}{|c|}{} & \mathbf{57}^\ast & \mathbf{64}^\ast & \mathbf{68} & \mathbf{74} & \mathbf{80} & \mathbf{86}^\ast & \mathbf{92}^\ast & \mathbf{97} & \mathbf{103} & \mathbf{109} & 115\\\cline{0-0}\cline{4-14}
      9 & \multicolumn{3}{|c|}{} & \mathbf{72}^\dagger & \mathbf{76} & \mathbf{82} & \mathbf{88} & \mathbf{95} & \mathbf{101} & \mathbf{108} & \mathbf{114} & \mathbf{121} & 128 \\\cline{0-0}\cline{5-14}
      10 & \multicolumn{4}{|c|}{} & \mathbf{84}^\ast & \mathbf{90} & \mathbf{97} & \mathbf{104} & \mathbf{110} & \mathbf{117} & \mathbf{124} & \mathbf{131} & 138 \\\cline{0-0}\cline{6-14}
      11 & \multicolumn{5}{|c|}{} & \mathbf{98} & \mathbf{106} & \mathbf{113} & \mathbf{120} & \mathbf{127} & \mathbf{135}^\ast & \mathbf{142} & 150 \\\cline{0-0}\cline{7-14}
      12 & \multicolumn{6}{|c|}{} & \mathbf{114} & \mathbf{122} & \mathbf{130} & \mathbf{138} & \mathit{146} & \mathbf{154}^\ast & 163 \\\cline{0-0}\cline{8-14}
      13 & \multicolumn{7}{|c|}{} &  \mathbf{132}^\ast & \mathbf{140} & \mathbf{149}^\ast  & \mathit{156}  & \mathit{165} & 174 \\\cline{0-0}\cline{9-14}
      14 & \multicolumn{8}{|c|}{} & \mathbf{150}^\ast & \mathbf{160}^\ast & \mathit{168} & \mathit{177} & 187 \\\cline{0-0}\cline{10-14}
      15 & \multicolumn{9}{|c|}{} & \mathbf{171}^\ast & \mathit{180} & \mathit{189} & 200 \\\cline{0-0}\cline{11-14}
      16 & \multicolumn{10}{|c|}{} & \mathbf{192}^\dagger & \mathit{201} & 212 \\\cline{0-0}\cline{12-14}
      17 & \multicolumn{11}{|c|}{} & \mathit{213} & 225 \\\cline{0-0}\cline{13-14}
      18 & \multicolumn{12}{|c|}{} & 238 \\\cline{0-0}\cline{14-14}
    """,
    6: r"""
      6 & \mathbf{35}^\ast & \mathbf{40} & \mathbf{45} & \mathbf{50} & \mathbf{55} & \mathbf{60} & \mathbf{65} & \mathbf{70} & \mathbf{75} & \mathbf{80} & \mathbf{85} & \mathbf{90} & \mathbf{95}\\\hline
      7 & & \mathbf{46}^\ast & \mathbf{52}^\ast & \mathbf{58}^\ast & \mathbf{64}^\ast & \mathbf{70}^\ast & \mathbf{75} & \mathbf{81} & \mathbf{87} & \mathbf{93} & \mathbf{99}^\ast & \mathbf{105}^\ast & \mathbf{110} \\\cline{0-0}\cline{3-14}
      8 & \multicolumn{2}{|c|}{} & \mathbf{59}^\ast & \mathbf{66}^\ast & \mathbf{73}^\ast & \mathbf{80}^\ast & \mathbf{85} & \mathbf{92} & \mathbf{99} & \mathbf{106} & \mathbf{113}^\ast & \mathbf{120}^\ast & \mathbf{125} \\\cline{0-0}\cline{4-14}
      9 & \multicolumn{3}{|c|}{} & \mathbf{74}^\ast & \mathbf{82}^\ast & \mathbf{90}^\ast & \mathbf{95} & \mathbf{102} & \mathbf{109} & \mathbf{116} & \mathbf{123} & \mathbf{130} & \mathbf{137} \\\cline{0-0}\cline{5-14}
      10 & \multicolumn{4}{|c|}{} & \mathbf{95}^\ast & \mathbf{100}^\ast & \mathbf{105} & \mathbf{112} & \mathbf{120} & \mathbf{127} & \mathbf{135} & \mathbf{142} & \mathbf{150} \\\cline{0-0}\cline{6-14}
      11 & \multicolumn{5}{|c|}{} & \mathbf{110}^\ast & \mathbf{115} & \mathbf{122} & \mathbf{130} & \mathbf{138} & \mathbf{147} & \mathbf{155} & \mathbf{163}\\\cline{0-0}\cline{7-14}
      12 & \multicolumn{6}{|c|}{} & \mathbf{125}^\ast & \mathbf{132} & \mathbf{141} & \mathbf{150}^\ast & \mathbf{158} & \mathbf{167} & \mathbf{176} \\\cline{0-0}\cline{8-14}
      13 & \multicolumn{7}{|c|}{} & \mathbf{142} & \mathbf{152}^\ast & \mathbf{161} & \mathbf{170} & \mathbf{180} & \mathbf{189}\\\cline{0-0}\cline{9-14}
      14 & \multicolumn{8}{|c|}{} & \mathbf{162} & \mathbf{172} & \mathit{182} & \mathbf{192}^\ast & \mathit{202} \\\cline{0-0}\cline{10-14}
      15 & \multicolumn{9}{|c|}{} & \mathbf{184}^\ast & 195 & 205 & 216\\\cline{0-0}\cline{11-14}
      16 & \multicolumn{10}{|c|}{} & 208 & 218 & 230 \\\cline{0-0}\cline{12-14}
      17 & \multicolumn{11}{|c|}{} & 231 & 244 \\\cline{0-0}\cline{13-14}
      18 & \multicolumn{12}{|c|}{} & 258 \\\cline{0-0}\cline{14-14}
    """,
}


def _key_from_stdin():
    if os.environ.get("NUMBERDB_KEY_FROM_STDIN") != "1":
        return
    token = sys.stdin.read().strip()
    if "=" in token and token.split("=", 1)[0].isupper():
        token = token.split("=", 1)[1].strip().strip("'\"")
    if token:
        os.environ["NUMBERDB_API_KEY"] = token


def _expand_multicolumns(cells):
    expanded = []
    for cell in cells:
        found = re.search(r"\\multicolumn\{(\d+)\}", cell)
        if found:
            expanded.extend([""] * int(found.group(1)))
        else:
            expanded.append(cell)
    return expanded


def _split_rows(text):
    for raw in text.splitlines():
        row = raw.strip()
        if not row or "&" not in row:
            continue
        row = row.split(r"\\", 1)[0].strip()
        first, rest = row.split("&", 1)
        first = first.strip()
        if not first.isdigit():
            continue
        yield int(first), _expand_multicolumns(rest.split("&"))


def _bold_value(cell):
    found = re.search(r"\\mathbf\{\\?(\d+)", cell)
    if not found:
        return None
    return int(found.group(1))


def _source_entries():
    for n, value in sorted(Z_N_2.items()):
        yield (n, n, 2, 2), value
    for s, rows in sorted(SOURCE_ROWS.items()):
        for m, cells in _split_rows(rows):
            if len(cells) != 13:
                raise ValueError("row m=%s, s=%s has %s cells" % (m, s, len(cells)))
            for offset, cell in enumerate(cells):
                n = 6 + offset
                value = _bold_value(cell)
                if value is not None:
                    yield (m, n, s, s), value


def _entries():
    entries = dict(_source_entries())
    if len(entries) != len(list(_source_entries())):
        raise ValueError("duplicate Zarankiewicz entry")
    return entries


ENTRIES = _entries()


def _as_record_value(value):
    if isinstance(value, str):
        return {
            "number": value,
            "comment": (
                r"The source writes $189/190$ for the first open diagonal "
                r"$s=2$ case."
            ),
        }
    return ZZ(value)


def _one_full_side_value(m, n, s, t):
    if m == s and n >= t:
        return (s - 1) * n + t - 1
    if n == t and m >= s:
        return (t - 1) * m + s - 1
    return None


def _check_identities():
    for (m, n, s, t), value in ENTRIES.items():
        if not (m <= n and s == t):
            raise AssertionError("entry is not stored as a diagonal m<=n value")
        if isinstance(value, str):
            continue
        expected = _one_full_side_value(m, n, s, t)
        if expected is not None and expected != value:
            raise AssertionError(
                "one-full-side formula gives %s for %s, stored %s"
                % (expected, (m, n, s, t), value)
            )
    for (m, n, s, t), value in ENTRIES.items():
        if isinstance(value, str):
            continue
        left = ENTRIES.get((m - 1, n, s, t))
        below = ENTRIES.get((m, n - 1, s, t))
        for previous in (left, below):
            if isinstance(previous, int) and previous > value:
                raise AssertionError(
                    "monotonicity fails at %s with previous %s" % ((m, n, s, t), previous)
                )


class ZarankiewiczNumbers(numberdb.Generator):

    table = TABLE
    parameters = ("m", "n", "s", "t")
    type = "Z"
    rigour = "proven"

    def enumerate(self):
        for m, n, s, t in sorted(ENTRIES, key=lambda item: (item[2], item[3], item[0], item[1])):
            yield {"m": str(m), "n": str(n), "s": str(s), "t": str(t)}

    def value(self, params, digits=None):
        key = tuple(int(params[name]) for name in self.parameters)
        return _as_record_value(ENTRIES[key])


if __name__ == "__main__":
    _check_identities()
    _key_from_stdin()
    generator = ZarankiewiczNumbers()
    if os.environ.get("NUMBERDB_PUBLISH") == "1" or "--publish" in sys.argv:
        print(generator.publish(message="transcribed exact Zarankiewicz values"))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
