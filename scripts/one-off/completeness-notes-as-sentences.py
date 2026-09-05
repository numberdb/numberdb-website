"""The completeness notes are index-card notes, not sentences.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/completeness-notes-as-sentences.py [apply]

The field renders as "Table is complete: no (<note>)", and five quadrature
tables fill it with a noun phrase and a telegraphic appendix -- "every rule
with n <= 30 is here, nodes and weights, both halves". A reader cannot tell
what the appendix modifies: whether both halves of every rule are listed, or
both halves of something else, or whether "nodes and weights" is a second
thing the table contains beside the rules.

T136 is the worst of them: it drops "is here" as well, so the sentence has no
verb at all, and it names "the three larger rules of QUADPACK" without saying
that QUADPACK uses them rather than defines them.

What each one has to say is: which rules are here, what a rule is indexed by,
and that a rule is listed in full. Said as a clause that finishes the
sentence it is put inside.
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

#: The rule's index n and how many points it has, per table, so the note can
#: say both rather than leaving a reader to work it out.
NOTES = {
	'T132': ('it holds every rule with $n\\leq 30$, where $n$ is the number '
	         'of nodes; each rule is listed in full, every node with its '
	         'weight, and both halves of the symmetric set'),
	'T134': ('it holds every rule with $n\\leq 30$, where $n$ is the number '
	         'of nodes; each rule is listed in full, every node with its '
	         'weight, and both halves of the symmetric set'),
	'T135': ('it holds every rule with $n\\leq 30$, where $n$ is the number '
	         'of nodes; each rule is listed in full, every node with its '
	         'weight. The nodes lie in $(0,\\infty)$ and are not symmetric, '
	         'so there are no halves to list'),
	'T136': ('it holds every rule with $n\\leq 15$, from 3 to 31 points, '
	         'together with the three larger rules that QUADPACK uses, '
	         '$n=20,25,30$, of 41, 51 and 61 points; $n$ is the number of '
	         'points of the embedded Gauss rule, and the Kronrod rule built '
	         'on it has $2n+1$ points. Each rule is listed in full, every '
	         'node with its '
	         'weight, and both halves of the symmetric set'),
	'T137': ('it holds every rule with $2\\leq n\\leq 30$, where $n$ is the '
	         'number of nodes, the two endpoints included; each rule is '
	         'listed in full, every node with its weight, and both halves of '
	         'the symmetric set'),
}

use_socks_proxy_if_set()
token = open(KEY, encoding='utf8').read().strip()


def document(tid):
	request = urllib.request.Request(
		'https://numberdb.org/api/table?id=%s' % (tid,),
		headers={'Authorization': 'Bearer %s' % (token,)})
	with urllib.request.urlopen(request, timeout=120) as response:
		return json.loads(response.read().decode('utf8'))


for tid, note in sorted(NOTES.items()):
	tree = document(tid)
	properties = dict(tree['Data properties'])
	was = properties.get('complete-note', '')
	if was == note:
		print('%s already says it' % (tid,))
		continue
	properties['complete-note'] = note
	tree['Data properties'] = properties
	print('%s' % (tid,))
	print('  was: %s' % (was,))
	print('  now: %s' % (note,))
	if APPLY:
		edit_over_api(
			tid, tree,
			('the completeness note is read as part of a sentence and was a '
			 'noun phrase with a telegraphic appendix; say which rules are '
			 'here, what n indexes, and that each is listed in full'),
			assistant='claude-opus-5', key_file=KEY)
		print('  committed')

if not APPLY:
	print('\ndry run; pass "apply" to send them')
