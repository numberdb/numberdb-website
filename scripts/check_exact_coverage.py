"""Check that the exact number layer can parse every number in numberdb-data.

    python3 scripts/check_exact_coverage.py [path-to-numberdb-data/data]

No Sage and no database: it reads the YAML directly. Run it after touching the
parsers, and before trusting any schema built on them -- the design is only as
good as its coverage of the real corpus, and running this is what turned up the
undocumented uncertainty notation and the bare "-i".
"""
import os, sys, pathlib, collections, re
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import yaml
from utils.numbers import (parse_real, parse_complex, parse_p_adic,
                           parse_polynomial, ParseError)

DATA = pathlib.Path(sys.argv[1] if len(sys.argv) > 1
                    else os.path.expanduser('~/Melodi/numberdb-data/data'))

def number_values(node):
    """Scalars in a Numbers section: scalar, or dict with number/datum."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key in ('number', 'datum'):
                yield from number_values(value)
            elif key in ('equals', 'param-latex', 'comment', 'reference'):
                continue
            else:
                yield from number_values(value)
    elif isinstance(node, list):
        for value in node:
            yield from number_values(value)
    elif isinstance(node, (str, int, float)):
        yield node

def classify(text):
    if 'O(' in text or re.match(r'^[QZ]\d+:', text):
        return 'p-adic'
    if re.search(r'[a-zA-Z]', text.replace('e','').replace('E','').replace('I','').replace('i','')):
        return 'polynomial/other'
    return 'real-or-complex'

total = collections.Counter(); ok = collections.Counter()
failures = collections.Counter(); examples = {}

for f in sorted(DATA.rglob('*.yaml')):
    if f.name in ('id.yaml', 'next_ids.yaml'):
        continue
    try:
        doc = yaml.load(f.read_text(errors='ignore'), Loader=yaml.BaseLoader)
    except Exception:
        continue
    if doc is None: continue
    if f.name in ('numbers.yaml', 'polynomials.yaml'):
        section = doc
    elif isinstance(doc, dict):
        #Polynomial tables use "Data:", everything else "Numbers:". Missing
        #that is how an earlier run reported full coverage while never looking
        #at a polynomial.
        section = doc.get('Numbers', doc.get('Data'))
    else:
        continue
    if section is None or isinstance(section, str) and section.startswith('INPUT{'):
        continue
    for value in number_values(section):
        text = str(value).strip()
        #Template directives, citations and links live in these sections too.
        if (not text or text.startswith('INPUT{') or text.startswith('HREF{')
                or text.startswith('CITE{') or text.startswith('http')):
            continue
        total['all'] += 1
        parsed = False
        for fn in (parse_real, parse_complex, parse_p_adic, parse_polynomial):
            try:
                fn(text); parsed = True; break
            except Exception:
                pass
        kind = 'all'
        if parsed:
            ok[kind] += 1
        else:
            shape = re.sub(r'\d', 'D', text)[:36]
            failures[shape] += 1
            examples.setdefault(shape, text[:64])

n = total['all']
print('stored entries examined: %d' % n)
print('handled by the exact layer: %d  (%.2f%%)' % (ok['all'], 100.0*ok['all']/max(n,1)))
print()
if failures:
    print('remaining failures:')
    for shape, count in failures.most_common(12):
        print('  %6d  %-38s e.g. %s' % (count, shape, examples[shape]))
else:
    print('no failures')
