"""Eleven tables cite the issue that asked for them. A table is encyclopedic.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/drop-the-issue-references.py [apply]

Who asked for a table is not a fact about the mathematics. It has two homes
already: the issue itself, and the table's own discussion page. The skill
used to ask for the citation as "provenance of the idea"; it now says to
answer in the issue and leave the table clean.

Eight of these carry a `comment-requested` that says nothing else -- "Asked
for in [2], of which this is the quadratic case" -- and three carry the
reference uncited. None of the issues holds anything a reader of the
mathematics needs: six have an empty body, #93 is a bare link to the
Wikipedia article the table already cites, and #134 points at Goncharov on
odd-dimensional volumes, which is not what the knot-volume table lists.

T144 was done separately: its comment carried real mathematics, which stayed.
"""
import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(
	os.path.dirname(os.path.abspath(__file__)))))

from agents.api_edit import ApiRefused, edit_over_api, use_socks_proxy_if_set

APPLY = 'apply' in sys.argv[1:]
KEY = os.path.expanduser('~/.config/numberdb/bmatschke-key')
TIDS = ('T128 T130 T131 T132 T133 T134 T135 T141 T142 T143 T145').split()

use_socks_proxy_if_set()
token = open(KEY, encoding='utf8').read().strip()


def document(tid):
	request = urllib.request.Request(
		'https://numberdb.org/api/table?id=%s' % (tid,),
		headers={'Authorization': 'Bearer %s' % (token,)})
	with urllib.request.urlopen(request, timeout=120) as response:
		return json.loads(response.read().decode('utf8'))


for tid in TIDS:
	tree = document(tid)
	references = dict(tree.get('References') or {})
	issues = [k for k, v in references.items()
	          if 'numberdb-data issue' in json.dumps(v)]
	if not issues:
		print('%s  nothing to do' % (tid,))
		continue

	comments = dict(tree.get('Comments') or {})
	dropped = []
	for label, text in list(comments.items()):
		if not any(('CITE{%s}' % issue) in text for issue in issues):
			continue
		#Only a comment that is *about* the request. One that also carries
		#mathematics would have to be rewritten by hand, as T144's was.
		without = text
		for issue in issues:
			without = without.replace('CITE{%s}' % issue, '')
		if not without.strip().startswith('Asked for in'):
			raise SystemExit('%s/%s is not purely about the request:\n%s'
			                 % (tid, label, text))
		del comments[label]
		dropped.append(label)

	for issue in issues:
		del references[issue]
	tree['Comments'] = comments
	tree['References'] = references

	#Nothing may still cite what was removed.
	blob = json.dumps(tree)
	for issue in issues:
		if 'CITE{%s}' % issue in blob:
			raise SystemExit('%s still cites %s somewhere' % (tid, issue))

	print('%s  references %-22s comments %s'
	      % (tid, ','.join(issues), ','.join(dropped) or '(none cited)'))

	if APPLY:
		try:
			reply = edit_over_api(
				tid, tree,
				('who asked for a table is not a fact about the mathematics; '
				 'the issue is answered in the issue'),
				assistant='claude-opus-5', key_file=KEY)
			print('      committed %s' % (json.loads(json.dumps(reply))
			                              .get('revision', '')[:12],))
		except ApiRefused as refused:
			print('      REFUSED %s: %s' % (refused.status, refused.body[:150]))

if not APPLY:
	print('\ndry run; pass "apply" to send them')
