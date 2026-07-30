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
from utils.numbers import parse_real, parse_complex, ParseError

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
    if f.name == 'numbers.yaml':
        section = doc
    elif isinstance(doc, dict):
        section = doc.get('Numbers')
    else:
        continue
    if section is None or isinstance(section, str) and section.startswith('INPUT{'):
        continue
    for value in number_values(section):
        text = str(value).strip()
        if not text or text.startswith('INPUT{') or text.startswith('HREF{'):
            continue
        kind = classify(text)
        total[kind] += 1
        if kind != 'real-or-complex':
            continue
        parsed = False
        for fn in (parse_real, parse_complex):
            try:
                fn(text); parsed = True; break
            except Exception:
                pass
        if parsed:
            ok[kind] += 1
        else:
            shape = re.sub(r'\d', 'D', text)[:36]
            failures[shape] += 1
            examples.setdefault(shape, text[:64])

print('stored number entries by kind:')
for kind in sorted(total):
    print('   %-18s %6d' % (kind, total[kind]))
print()
n = total['real-or-complex']
print('real/complex handled by the exact layer: %d/%d  (%.2f%%)' % (ok['real-or-complex'], n, 100.0*ok['real-or-complex']/max(n,1)))
print()
if failures:
    print('remaining failures:')
    for shape, count in failures.most_common(12):
        print('  %6d  %-38s e.g. %s' % (count, shape, examples[shape]))
else:
    print('no failures')
