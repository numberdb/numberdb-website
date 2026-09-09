"""A value's label is a label, not a second copy of its comment.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/ramanujan-label-is-a-label.py [apply]

Every product in T167 is labelled `<name>, <the product>`: "Artin's constant,
$\\prod_p(1-\\frac{1}{p(p-1)})$". The Ramanujan row instead leads with the
closed form, "$15/\\pi^2$, $\\prod_p(1+\\frac{1}{p^2})$" -- and that closed form
is what its comment already says, in the sentence that gives it its name:
"$\\prod_p(1+p^{-2})=15/\\pi^2$, an identity of Ramanujan".

So the label says it twice and breaks the column's pattern. The product alone
is the label; the identity stays where the identity is explained.
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
WAS = '$15/\\pi^2$, $\\prod_p(1+\\frac{1}{p^2})$'
NOW = "Ramanujan's product, $\\prod_p(1+\\frac{1}{p^2})$"

use_socks_proxy_if_set()
token = open(KEY, encoding='utf8').read().strip()

request = urllib.request.Request(
	'https://numberdb.org/api/table?id=T167',
	headers={'Authorization': 'Bearer %s' % (token,)})
with urllib.request.urlopen(request, timeout=120) as response:
	tree = json.loads(response.read().decode('utf8'))

values = dict(((tree.get('Parameters') or {}).get('product') or {}).get('values') or {})
current = values.get('ramanujan')
print('was: %s' % (current,))
if current != WAS:
	print('not the text this expected; nothing done')
	raise SystemExit
values['ramanujan'] = NOW
tree['Parameters']['product']['values'] = values
print('now: %s' % (NOW,))
if APPLY:
	edit_over_api(
		'T167', tree,
		("the Ramanujan row's label led with $15/\\pi^2$, which its own comment "
		 "already gives as the identity; every other label here is a name and "
		 "its product, and now so is this one"),
		assistant='claude-opus-5', key_file=KEY)
	print('committed')
else:
	print('\ndry run; pass "apply" to send it')
