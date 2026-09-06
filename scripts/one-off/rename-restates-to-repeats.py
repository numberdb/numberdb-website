"""`restating` already meant something else.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/rename-restates-to-repeats.py [apply]

The Python client's `publish(restating=True)` rewrites entries whose stored
value says the same thing to the same precision in different digits. The table
field declared a day later -- one table repeats another's values -- is close
enough in wording to be confused with it and means something else entirely.

The client's argument is published on PyPI and other people's generators pass
it, so the field is the side that moves. `repeats` is the better word for it
anyway: the claim is that this table repeats that one.

Two documents say it, and the column was renamed by migration 0044, so this
only rewrites the key in the documents.
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
TABLES = ('T136', 'T148')

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
	properties = dict(tree.get('Data properties') or {})
	if 'repeats' in properties and 'restates' not in properties:
		print('%s already says repeats' % (tid,))
		continue
	if 'restates' not in properties:
		print('%s declares neither -- nothing to do' % (tid,))
		continue
	#Rebuilt in order rather than popped, so the key stays where it was
	#rather than moving to the end of the section.
	properties = {('repeats' if key == 'restates' else key): value
	              for key, value in properties.items()}
	tree['Data properties'] = properties
	print('%s: restates -> repeats (%s)' % (tid, properties['repeats']))
	if APPLY:
		edit_over_api(
			tid, tree,
			('the field is named repeats: the numberdb package already uses '
			 'restating for rewriting an entry in different digits, which is '
			 'a different thing, and its argument is published'),
			assistant='claude-opus-5', key_file=KEY)
		print('  committed')

if not APPLY:
	print('\ndry run; pass "apply" to send them')
