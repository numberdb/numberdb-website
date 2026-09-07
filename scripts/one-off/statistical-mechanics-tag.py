"""Six tables on critical phenomena, filed under "physics".

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/statistical-mechanics-tag.py [apply]

T152 to T157 are percolation thresholds, lattice entropy constants, Ising
critical couplings, two-dimensional critical exponents, k-core thresholds and
connective constants. Every one of them is statistical mechanics, and they
carry "physics", "combinatorics" and "probability theory" between them --
tags that do not distinguish them from an elliptic curve.

They went in that way because the skill said to use an existing tag rather
than invent one, which is right for a single table and wrong for six. The
rule now asks for three, and this is the tag those six were waiting for.
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
TAG = 'statistical mechanics'
TABLES = ('T152', 'T153', 'T154', 'T155', 'T156', 'T157')

use_socks_proxy_if_set()
token = open(KEY, encoding='utf8').read().strip()


def document(tid):
	request = urllib.request.Request(
		'https://numberdb.org/api/table?id=%s' % (tid,),
		headers={'Authorization': 'Bearer %s' % (token,)})
	with urllib.request.urlopen(request, timeout=120) as response:
		return json.loads(response.read().decode('utf8'))


for tid in TABLES:
	tree = document(tid)
	tags = list(tree.get('Tags') or [])
	if TAG in tags:
		print('%s already carries it' % (tid,))
		continue
	#First, because it is the subject; the others qualify it.
	tags.insert(0, TAG)
	tree['Tags'] = tags
	print('%s: %s' % (tid, ', '.join(tags)))
	if APPLY:
		edit_over_api(
			tid, tree,
			('tagged "%s": six tables on critical phenomena carried only '
			 '"physics" and "combinatorics", which does not distinguish them '
			 'from anything' % (TAG,)),
			assistant='claude-opus-5', key_file=KEY)
		print('  committed')

if not APPLY:
	print('\ndry run; pass "apply" to send them')
