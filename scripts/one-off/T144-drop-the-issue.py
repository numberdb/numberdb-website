"""T144 discusses the issue that asked for it. That belongs in the issue.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/T144-drop-the-issue.py [apply]

A table is encyclopedic. What was asked for, by whom, and what is still
missing is a conversation, and it has two homes already: the issue itself,
and the table's own discussion page.

The mathematics in the comment stays -- the twisted sum, what it is for the
trivial and quadratic characters, and the LMFDB cross-check. What goes is the
framing that made it a reply to a request, and the reference to the issue,
which holds nothing a reader of the mathematics needs: it is a title and an
empty body.

The answer to the requester was posted to numberdb-data#13 first.
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
HOST = 'https://numberdb.org'

use_socks_proxy_if_set()
with open(KEY, encoding='utf8') as handle:
	token = handle.read().strip()
request = urllib.request.Request('%s/api/table?id=T144' % (HOST,),
                                 headers={'Authorization': 'Bearer %s' % token})
with urllib.request.urlopen(request, timeout=120) as response:
	tree = json.loads(response.read().decode('utf8'))

comments = dict(tree['Comments'])
before = comments['comment-twisted']
opening = ('The issue this table answers CITE{issue13} asks for Kloosterman '
           'sums of Dirichlet characters, ')
if not before.startswith(opening):
	raise SystemExit('T144: comment-twisted does not open as expected:\n'
	                 + repr(before[:120]))
#Rewritten rather than spliced: cutting the opening left "The twisted
#Kloosterman sum $K(...)$, which ... is $K(a,b;p)$", a sentence with no main
#verb. Moving text leaves the remainder holding grammar that belonged to
#what was removed.
rest = before[len(opening):]
tail = rest.split(', which for the trivial character', 1)
if len(tail) != 2:
	raise SystemExit('T144: the sentence does not continue as expected')
formula, remainder = tail
comments['comment-twisted'] = (
	'The twisted Kloosterman sum ' + formula
	+ ' is $K(a,b;p)$ for the trivial character $\\chi$ and in general not '
	  'real for a nontrivial one'
	+ remainder.split('is in general not real', 1)[1])
tree['Comments'] = comments

references = dict(tree['References'])
if 'issue13' not in references:
	raise SystemExit('T144: the issue13 reference is already gone')
del references['issue13']
tree['References'] = references

#Nothing else may cite it, or the page renders a citation to a label that is
#no longer there.
import re

for section in ('Definition', 'Comments', 'Formulas', 'Programs', 'Links',
                'Data properties'):
	blob = tree.get(section)
	texts = ([blob] if isinstance(blob, str)
	         else list(blob.values()) if isinstance(blob, dict) else [])
	for text in texts:
		if isinstance(text, str) and 'issue13' in text:
			raise SystemExit('T144: %s still cites issue13' % (section,))

print('comment now:', comments['comment-twisted'][:190])
print()
print('references :', sorted(references))

if APPLY:
	reply = edit_over_api(
		'T144', tree,
		('the table discussed the issue that asked for it; the mathematics '
		 'stays, the request goes to the issue, where it was answered'),
		assistant='claude-opus-5', key_file=KEY)
	print('\ncommitted:', json.dumps(reply)[:160])
else:
	print('\ndry run; pass "apply" to send it')
