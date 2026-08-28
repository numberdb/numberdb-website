"""Compute and check a table without creating one.

    sage -python dry_run.py path/to/generate.py [--identities checks.py]

A table's history is public and permanent, so a table should not be built in
it. Everything a run wants to get right -- the range, the exactness, the
identities, the length of the longest entry -- can be settled before the table
exists, and then the table is created once and filled once.

The evidence for bothering: the Fibonacci polynomials took nine revisions
because they were repaired in public, six of those being corrections that
could have happened here. The tables built after this pattern took two.

The generator needs no table for this. It is asked for its parameters and its
values directly; nothing is sent anywhere and no key is needed.
"""

import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from check import exactness, measure, names_its_rings          # noqa: E402


def load(path):
    spec = importlib.util.spec_from_file_location('generator_under_test', path)
    module = importlib.util.module_from_spec(spec)
    #A generator names its table at class level; it does not need to exist yet.
    os.environ.setdefault('NUMBERDB_TABLE', 'TBD')
    spec.loader.exec_module(module)
    for name in dir(module):
        thing = getattr(module, name)
        if isinstance(thing, type) and hasattr(thing, 'enumerate') \
                and hasattr(thing, 'value') and thing.__module__ == module.__name__:
            return thing()
    raise SystemExit('no generator class found in %s' % path)


def main(argv):
    if not argv:
        raise SystemExit(__doc__)
    path = argv[0]
    generator = load(path)

    print('== the generator itself ==')
    for complaint in names_its_rings(path) or ['names its rings, initialises Sage']:
        print('  ', complaint)

    print()
    print('== computing every entry ==')
    values = {}
    digits = getattr(generator, 'digits', 100)
    for params in generator.enumerate():
        key = ','.join('%s=%s' % (k, params[k]) for k in sorted(params))
        values[key] = generator.value(params, digits)
    print('   %d entries computed' % len(values))

    print()
    print('== exactness ==')
    complaints = exactness(values)
    for complaint in complaints[:5]:
        print('  ', complaint)
    if not complaints:
        print('   every coefficient is an exact Sage number')

    print()
    print('== size ==')
    measured = measure(values)
    print('   %(entries)d entries, longest %(longest)d characters at %(longest_at)s, '
          'block %(block_kb).1f KB' % measured)
    if measured['longest'] > 1300:
        print('   TOO LONG: the tables here stop around 1100 to 1300 characters,')
        print('   where an entry stops being something a person reads.')
    if measured['block_kb'] > 160:
        print('   OVER THE TARGET: aim at half the 320 KB soft limit, so the')
        print('   next person can extend the table without breaching it.')

    print()
    print('Nothing was sent. Create the table only when the above is clean and')
    print('the identities have been checked; then fill it once.')
    return 1 if complaints else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
