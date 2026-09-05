"""What this generator would write, against what T35 holds now.

The question the port has to answer: does it reproduce the table, and where
it does not, is the difference the one that was asked for?
"""

import json
import os
import sys


def stored(path=None):
    """The table's entries as it holds them now, keyed 'a2,a1,a0/n'.

    Read from a file rather than fetched: this runs in a container with no
    route to the site, and the document is the same either way.
    """
    path = path or os.environ.get('NUMBERDB_STORED', '/work/T35.json')
    with open(path, encoding='utf8') as handle:
        document = json.load(handle)

    flat = {}

    def walk(node, prefix):
        if isinstance(node, dict) and not {'number', 'equals'} & set(node):
            for key, value in node.items():
                walk(value, prefix + [str(key)])
            return
        value = node.get('number') if isinstance(node, dict) else node
        flat['/'.join(prefix)] = str(value)

    walk(document['Numbers'], [])
    return flat


def main(generator):
    from numberdb._write import to_text

    here = stored()
    same = 0
    changed = []
    missing = []
    for params in generator.enumerate():
        key = '%s,%s,%s/%s' % (params['a2'], params['a1'], params['a0'],
                               params['n'])
        entry = generator.value(params, generator.digits)
        number = entry['number'] if isinstance(entry, dict) else entry
        now = to_text(number, generator.digits)
        was = here.pop(key, None)
        if was is None:
            missing.append(key)
        elif was == now:
            same += 1
        else:
            changed.append((key, was, now))

    spelling = [c for c in changed if ('/' in c[2]) != ('/' in c[1])]
    rounding = [c for c in changed if c not in spelling]
    print('identical : %d' % (same,))
    print('  of the changed:')
    print('    exactness now said  : %d' % (len(spelling),))
    print('    last digit re-rounded: %d' % (len(rounding),))
    if spelling:
        key, was, now = spelling[0]
        print('    e.g. %s' % (key,))
        print('      was: %s' % (was[:60],))
        print('      now: %s' % (now[:60],))
    print('changed   : %d' % (len(changed),))
    print('not stored: %d' % (len(missing),))
    print('stored but not generated: %d' % (len(here),))
    def where(a, b):
        for index, (one, two) in enumerate(zip(a, b)):
            if one != two:
                return index
        return min(len(a), len(b))

    for key, was, now in changed[:6]:
        at = where(was, now)
        print()
        print('  %s   lengths %d -> %d, first differ at %d'
              % (key, len(was), len(now), at))
        print('    was: ...%s' % (was[max(0, at - 12):at + 24],))
        print('    now: ...%s' % (now[max(0, at - 12):at + 24],))
    if len(changed) > 8:
        print('\n  ... and %d more' % (len(changed) - 8,))
    return 0 if not missing and not here else 1
