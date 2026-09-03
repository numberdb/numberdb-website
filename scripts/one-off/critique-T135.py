"""T135, from the stage-three critique of 2026-09-03.

    ALL_PROXY=socks5h://127.0.0.1:1080 python3 scripts/one-off/critique-T135.py
    ... apply                                     # to send it

The first edit to go through the API rather than the ORM.

  1. Formula (4) tells the reader to fold the Gauss-Hermite rule and does not
     link it. The corpus holds it, and this is its first mention in the
     Formulas section; the link is a section later, in a comment.
  2. Comment (10) says "no node is rational, since ... and no integer is a
     root". The last clause is the whole difficulty, asserted rather than
     shown. What is true is stronger: Schur proved $L_n$ irreducible over
     $\\mathbb{Q}$, so the nodes are conjugate of degree exactly $n$ -- which
     is also why the $n=3,4$ polynomials printed on the entries are minimal.
     Checked here for every rule the table holds, $n=1..30$: irreducible,
     and $3!L_3$, $4!L_4$ are the two polynomials the comment prints.
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


def document(tid):
	use_socks_proxy_if_set()
	with urllib.request.urlopen('%s/api/table?id=%s' % (HOST, tid),
	                            timeout=120) as response:
		return json.loads(response.read().decode('utf8'))


def swap(tree, section, label, before, after):
	block = dict(tree[section])
	if before not in block[label]:
		raise SystemExit('T135 %s/%s: not found:\n%r' % (section, label, before))
	block[label] = block[label].replace(before, after, 1)
	tree[section] = block


tree = document('T135')

#`/api/table` serves `Parameters` in a different order from the stored
#document -- k, n, expression against n, k, expression -- so writing back what
#it served is refused, rightly, as changing every entry's identity. The order
#below is the stored one, which the refusal itself reports. Read-modify-write
#through the public API needs this until the read endpoint preserves order.
STORED_PARAMETER_ORDER = ('n', 'k', 'expression')
parameters = tree.get('Parameters') or {}
if set(parameters) != set(STORED_PARAMETER_ORDER):
	raise SystemExit('T135 parameters are %s, not %s'
	                 % (sorted(parameters), sorted(STORED_PARAMETER_ORDER)))
tree['Parameters'] = {name: parameters[name]
                      for name in STORED_PARAMETER_ORDER}

# 1 --------------------------------------------------------------------------
# The first mention, in the section that asks the reader to use it.
swap(tree, 'Formulas', 'formula-half-integer',
     'the positive nodes of the Gauss–Hermite rule with $2n$ points',
     'the positive nodes of the '
     'HREF{Nodes_and_weights_of_Gauss_Hermite_quadrature}[Gauss–Hermite rule] '
     'with $2n$ points')

# 2 --------------------------------------------------------------------------
swap(tree, 'Comments', 'comment-exact-entries',
     r'For $n\geq 2$ no node is rational, since $n!\,L_n$ has integer '
     r'coefficients with constant term $n!$ and leading coefficient $\pm 1$ '
     'and no integer is a root.',
     r'For $n\geq 2$ no node is rational: $L_n$ is irreducible over '
     r'$\mathbb{Q}$ CITE{Schur}, so the $n$ nodes of a rule are conjugate '
     r'algebraic numbers of degree exactly $n$.')

references = dict(tree['References'])
references['Schur'] = {
	'bib': ('I. Schur, Einige S\u00e4tze \u00fcber Primzahlen mit Anwendungen '
	        'auf Irreduzibilit\u00e4tsfragen I, Sitzungsber. Preuss. Akad. '
	        'Wiss. Phys.-Math. Kl. 1929, 125\u2013136.'),
}
tree['References'] = references

print('formula-half-integer:', tree['Formulas']['formula-half-integer'][:200])
print()
print('comment-exact-entries:', tree['Comments']['comment-exact-entries'])
print()
print('references          :', sorted(tree['References']))

if APPLY:
	reply = edit_over_api(
		'T135', tree,
		('link the Gauss-Hermite rule where the formula asks the reader to '
		 'fold it, and replace "no integer is a root" -- which asserts the '
		 'difficulty -- with Schur\'s irreducibility, checked here for every '
		 'n the table holds'),
		assistant='claude-opus-5')
	print('\ncommitted:', json.dumps(reply)[:300])
else:
	print('\ndry run; pass "apply" to send it')
