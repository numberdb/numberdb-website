"""Two tables say which table states their shared values first.

Superseded: the field was renamed `restates` -> `repeats` the next day,
because the Python client already had `publish(restating=True)` for
something else. `rename-restates-to-repeats.py` moved the two documents;
this script is kept as the record of what was declared and why, and
would write the old key if it were run again.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/declare-restatements.py [apply]

T136 stores, for each Gauss-Kronrod rule, the nodes and weights of the Gauss
rule embedded in it -- the same roots of the same Legendre polynomial that T132
lists, 209 entries of it. T148 transcribes the centre densities and densities
of the lattices T147 already holds, 45 entries of it. In both cases a reader
who types the digits is told the same thing twice.

T149 is deliberately not declared, though all nine of its values are in T147:
Hermite's constant in dimension 8 equals the Hermite number of E_8 because
Blichfeldt proved the supremum is attained there, and two constructions
meeting is what a database of constants is for. See
docs/design/same-construction.md for why no rule on the values can tell the
two cases apart.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))

from agents.api_edit import edit_over_api, use_socks_proxy_if_set

APPLY = 'apply' in sys.argv[1:]
KEY = os.path.expanduser('~/.config/numberdb/bmatschke-key')

DECLARATIONS = {
	'T136': ('Nodes_and_weights_of_Gauss_Legendre_quadrature',
	         'the nodes and weights of the embedded Gauss rule are the '
	         'Gauss-Legendre nodes and weights, computed the same way'),
	'T148': ('Packing_densities_and_Hermite_numbers_of_the_classical_lattices',
	         'the densest known lattice in each dimension up to 24 is one this '
	         'table holds, and its density is that lattice\'s'),
}

use_socks_proxy_if_set()
token = open(KEY, encoding='utf8').read().strip()


def document(tid):
	request = urllib.request.Request(
		'https://numberdb.org/api/table?id=%s' % (tid,),
		headers={'Authorization': 'Bearer %s' % (token,)})
	with urllib.request.urlopen(request, timeout=120) as response:
		return json.loads(response.read().decode('utf8'))


for tid, (slug, why) in sorted(DECLARATIONS.items()):
	tree = document(tid)
	properties = dict(tree.get('Data properties') or {})
	wanted = 'HREF{%s}' % (slug,)
	if properties.get('restates') == wanted:
		print('%s already declares it' % (tid,))
		continue
	properties['restates'] = wanted
	tree['Data properties'] = properties
	print('%s restates %s' % (tid, slug))
	print('  because %s' % (why,))
	if APPLY:
		edit_over_api(
			tid, tree,
			('says which table states the shared values first: %s. Search '
			 'folds the repeat into the original rather than answering the '
			 'same number twice' % (why,)),
			assistant='claude-opus-5', key_file=KEY)
		print('  committed')

if not APPLY:
	print('\ndry run; pass "apply" to send them')
