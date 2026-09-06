"""`family` was rendering as the product of six variables.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/family-parameter-display.py [apply]

A parameter with no `display` is written `$name$`, which is right for `n` and
`D` and wrong for a name that is a word: `$family$` is maths italic with the
letters spaced as a product. T17 has always done this properly --
`display: constraint`, plain text -- and two lattice tables did not.

Only these two are affected. Eighteen other word-named parameters lack a
display as well, all of them called `expression` or `constant`, and every one
carries `show-in-parameter-list: no`, so none of them is rendered.
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

#: table -> parameter -> how it should be written.
DISPLAYS = {
	'T147': {'family': 'family'},
	'T150': {'family': 'family'},
}

use_socks_proxy_if_set()
token = open(KEY, encoding='utf8').read().strip()


def document(tid):
	request = urllib.request.Request(
		'https://numberdb.org/api/table?id=%s' % (tid,),
		headers={'Authorization': 'Bearer %s' % (token,)})
	with urllib.request.urlopen(request, timeout=120) as response:
		return json.loads(response.read().decode('utf8'))


for tid, wanted in sorted(DISPLAYS.items()):
	tree = document(tid)
	parameters = dict(tree.get('Parameters') or {})
	changed = []
	for name, display in wanted.items():
		spec = dict(parameters.get(name) or {})
		if spec.get('display') == display:
			continue
		#Before `title`, so the two read in the order the page shows them.
		spec['display'] = display
		parameters[name] = spec
		changed.append(name)
	if not changed:
		print('%s already says how to write them' % (tid,))
		continue
	tree['Parameters'] = parameters
	print('%s: %s' % (tid, ', '.join('%s -> %r' % (n, wanted[n])
	                                 for n in changed)))
	if APPLY:
		edit_over_api(
			tid, tree,
			('the parameter %s is a word, and with no display it was written '
			 '$%s$ -- maths italic, the letters spaced as a product. Written '
			 'as itself, the way T17 writes "constraint"'
			 % (', '.join(changed), changed[0])),
			assistant='claude-opus-5', key_file=KEY)
		print('  committed')

if not APPLY:
	print('\ndry run; pass "apply" to send them')
