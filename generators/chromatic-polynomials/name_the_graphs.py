"""Attach the readable names to the graph entries of a table.

    manage.py shell < name_the_graphs.py          (APPLY=1 to commit)

Thirty-five of the 996 connected graphs on at most seven vertices have a name
somebody would recognise. The rest do not, which is why the graph6 string is
the parameter; the name is a comment on the entry, shown under the value.

Separate from the generator because a generator produces values and the
package has no hook for anything else. Run it after the generator, on each
table that is indexed by these graphs.
"""

import os
import sys

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'
TIDS = (os.environ.get('TIDS') or 'T125').split(',')

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
NAMED = {}
with open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       'generate.py')) as handle:
    source = handle.read()
exec(source[source.index('NAMED = {'):source.index('}\n', source.index('NAMED = {')) + 1],
     {}, NAMED)
NAMED = NAMED['NAMED']

for tid in TIDS:
    table = Table.objects.get(tid=tid.strip())
    tree = dict(tree_of(table.head_revision))
    entries = list(tree['Numbers'])
    touched = 0
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        name = NAMED.get(str((entry.get('params') or {}).get('g')))
        if name and entry.get('comment') != name:
            entry['comment'] = name
            touched += 1
    tree['Numbers'] = entries
    print('%s: %d of %d entries named' % (tid, touched, len(entries)))
    if APPLY and touched:
        commit_table(table, tree, author=User.objects.get(username='bmatschke'),
                     base=table.head_revision,
                     produced_by='table document, assisted by claude-opus-5',
                     message='the names of the graphs that have one')
        print('   committed')
