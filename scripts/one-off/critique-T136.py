"""T136, from the stage-three critique of 2026-09-03.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/critique-T136.py
    ... apply

Each finding was checked against the live document before being acted on,
which is the part a repair stage must not skip:

  1. $E_{n+1}$ is used in the first formula and defined in a comment. True
     as the page draws it: the document has Comments before Formulas, the
     page draws Formulas first, so a reader meets five polynomials called
     $E$ with no $E$ defined. The same page-order trap as "the formula
     below". The definition moves to the front of Formulas.
  2. Comment (11) restates formula (4) and closes on what a search returns.
     Checked: `formula-symmetry` is $x_{2n+2-k}=-x_k$, $w_{2n+2-k}=w_k$, the
     same sentence, and `complete-note` already says "both halves".
  3. "the digits written are those the ball supports" -- checked against
     every entry: all 772 carry exactly 100 significant digits, so 100 is a
     cap and the sentence tells a reader the wrong rule for how far to
     trust them.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))

from agents.api_edit import edit_over_api, use_socks_proxy_if_set

APPLY = 'apply' in sys.argv[1:]
HOST = os.environ.get('NUMBERDB_HOST', 'https://numberdb.org')
KEY = os.path.expanduser(os.environ.get('NUMBERDB_KEY_FILE')
                         or '~/.config/numberdb/bmatschke-key')


def document(tid):
	use_socks_proxy_if_set()
	with open(KEY, encoding='utf8') as handle:
		token = handle.read().strip()
	request = urllib.request.Request(
		'%s/api/table?id=%s' % (HOST, tid),
		headers={'Authorization': 'Bearer %s' % (token,)})
	with urllib.request.urlopen(request, timeout=120) as response:
		return json.loads(response.read().decode('utf8'))


tree = document('T136')

# 1 --------------------------------------------------------------------------
# The definition of the nodes leads the Formulas section, where a reader goes
# to find out how they are computed. The interlacing and the rest stay in the
# comment, which is about how to read the listing.
comments = dict(tree['Comments'])
whole = comments['comment-nodes']
cut = 'for $0\\leq j\\leq n$. '
if cut not in whole:
	raise SystemExit('T136: comment-nodes does not read as expected')
definition, rest = whole.split(cut, 1)
definition = definition + 'for $0\\leq j\\leq n$.'
#The comment kept the pronoun of a sentence that has moved, so it needs the
#noun back: "Its roots" referred to $E_{n+1}$ in the sentence now in Formulas.
if not rest.startswith('Its roots are'):
	raise SystemExit('T136: comment-nodes continues unexpectedly: %r'
	                 % (rest[:40],))
comments['comment-nodes'] = rest.replace(
	'Its roots are', 'The roots of $E_{n+1}$ are', 1)
tree['Comments'] = comments

formulas = dict(tree['Formulas'])
reordered = {'formula-nodes': definition}
reordered.update(formulas)
tree['Formulas'] = reordered

# 2 --------------------------------------------------------------------------
del comments['comment-both-halves']
tree['Comments'] = comments

# 3 --------------------------------------------------------------------------
properties = dict(tree['Data properties'])
before = ('and the digits written are those the ball supports (the widest, a '
          'weight of the 61-point rule, supports 124')
after = ('and a hundred digits are written, which every ball supports (the '
         'widest, a weight of the 61-point rule, supports 124')
if before not in properties['rigour details']:
	raise SystemExit('T136: the sentence about digits moved')
properties['rigour details'] = properties['rigour details'].replace(
	before, after)
tree['Data properties'] = properties

print('formulas now :', list(tree['Formulas']))
print('comments now :', list(tree['Comments']))
print()
print('formula-nodes:', tree['Formulas']['formula-nodes'])
print()
print('comment-nodes:', tree['Comments']['comment-nodes'][:200])

if APPLY:
	reply = edit_over_api(
		'T136', tree,
		('define the Stieltjes polynomial in Formulas, where the first '
		 'formula uses it and the page draws it before the comment that '
		 'defined it; drop a comment that restates formula (4) and ends on '
		 'what a search returns; and say that a hundred digits are written '
		 'rather than as many as the ball supports -- all 772 carry exactly '
		 'a hundred'),
		assistant='claude-opus-5', key_file=KEY)
	print('\ncommitted:', json.dumps(reply)[:220])
else:
	print('\ndry run; pass "apply" to send it')
