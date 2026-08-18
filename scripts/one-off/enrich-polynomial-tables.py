"""Give T108 and T109 their references, cross-links and identities.

    manage.py shell < scripts/one-off/enrich-polynomial-tables.py

Every identity written here was checked in Sage over the whole range of the
tables before it was written down, and every link was fetched. What is *not*
here is an orthogonality claim: see the comment on `comment-not-orthogonal`.
"""
import os

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'
AUTHOR = User.objects.get(username='bmatschke')
PRODUCED_BY = 'table document, assisted by claude-opus-5'

LUCAS_SEQUENCE_COMMENT = (
	r'For integers $P, Q$ the Lucas sequences CITE{WikiLucasSeq} are the two '
	r'solutions of $X_n = P X_{n-1} - Q X_{n-2}$ picked out by their starting '
	r'values: $U_0 = 0$, $U_1 = 1$ and $V_0 = 2$, $V_1 = P$. '
	r'Taking $P = x$ and $Q = -1$ gives the polynomials in this pair: '
	r'$F_n(x) = U_n(x, -1)$ and $L_n(x) = V_n(x, -1)$, which at $x = 1$ are '
	r'the Fibonacci and the Lucas numbers.')

NOT_ORTHOGONAL = (
	r'These are <em>not</em> orthogonal polynomials in the usual sense. A '
	r'three-term recurrence $p_n = (x - c_n)p_{n-1} - k_n p_{n-2}$ gives a '
	r'family orthogonal for a positive measure on $\mathbb{R}$ exactly when '
	r'$k_n > 0$ (Favard), and here $k_n = -1$. What holds instead is inherited '
	r'from the Chebyshev polynomials of the second kind CITE{ChebyshevU} '
	r'through $F_n(x) = i^{n-1}U_{n-1}(-ix/2)$: along the segment $x = 2it$, '
	r'$t \in [-1,1]$, with weight $\sqrt{1-t^2}$, distinct $F_m, F_n$ pair to '
	r'zero while $\langle F_n, F_n\rangle$ alternates between $\pm\pi/2$ &mdash; '
	r'an indefinite form rather than an inner product.')

SHARED_LINKS = {
	'WikiLucasSeq': {'title': 'Wikipedia: Lucas sequence',
	                 'url': 'https://en.wikipedia.org/wiki/Lucas_sequence'},
}

SHARED_REFERENCES = {
	'Koshy': {'bib': 'Koshy, T., "Fibonacci and Lucas Numbers with '
	                 'Applications", Wiley-Interscience, 2001.'},
}

FIBONACCI = {
	'Formulas': {
		'formula-recurrence':
			r'$F_0(x) = 0$, $F_1(x) = 1$, and $F_{n}(x) = x F_{n-1}(x) + '
			r'F_{n-2}(x)$ for $n \geq 2$ (recurrence).',
		'formula-closed':
			r'$F_n(x) = \sum_{k=0}^{\lfloor (n-1)/2 \rfloor} \binom{n-k-1}{k} '
			r'x^{n-2k-1}$ (closed form). The coefficients are the rows of '
			r'CITE{OEIS}, indexed there from $F_{n+1}$.',
		'formula-generating-function':
			r'$\sum_{n=0}^\infty F_n(x) t^n = \frac{t}{1 - xt - t^2}$ '
			r'(generating function).',
		'formula-binet':
			r'$F_n(x) = \frac{\alpha^n - \beta^n}{\alpha - \beta}$ where '
			r'$\alpha, \beta = \frac{x \pm \sqrt{x^2+4}}{2}$ are the roots of '
			r'$z^2 - xz - 1$ (Binet form). At $x = 1$, $\alpha$ is the golden '
			r'ratio HREF{Golden_ratio}.',
		'formula-lucas':
			r'$L_n(x) = F_{n-1}(x) + F_{n+1}(x)$ and $F_{2n}(x) = F_n(x)L_n(x)$, '
			r'where $L_n$ are the Lucas polynomials HREF{Lucas_polynomials}.',
		'formula-pell':
			r'$L_n(x)^2 - (x^2+4)F_n(x)^2 = 4(-1)^n$.',
		'formula-divisibility':
			r'$\gcd(F_m, F_n) = F_{\gcd(m,n)}$, so for $n > 2$ the polynomial '
			r'$F_n$ divides $F_m$ exactly when $n$ divides $m$.',
		'formula-chebyshev':
			r'$F_n(x) = i^{n-1} U_{n-1}(-ix/2)$, where $U_n$ are the Chebyshev '
			r'polynomials of the second kind CITE{ChebyshevU}.',
	},
	'Comments': {
		'comment-lucas-sequence': LUCAS_SEQUENCE_COMMENT,
		'comment-not-orthogonal': NOT_ORTHOGONAL,
	},
	'Links': {
		'Wiki': {'title': 'Wikipedia: Fibonacci polynomials',
		         'url': 'https://en.wikipedia.org/wiki/Fibonacci_polynomials'},
		'MathWorld': {'title': 'MathWorld: Fibonacci Polynomial',
		              'url': 'https://mathworld.wolfram.com/FibonacciPolynomial.html'},
		'OEIS': {'title': 'OEIS A011973: coefficients, indexed from $F_{n+1}$',
		         'url': 'https://oeis.org/A011973'},
		'ChebyshevU': {'title': 'Wikipedia: Chebyshev polynomials',
		               'url': 'https://en.wikipedia.org/wiki/Chebyshev_polynomials'},
	},
	'Tags': ['polynomial', 'recurrence', 'generating function'],
}

LUCAS = {
	'Formulas': {
		'formula-recurrence':
			r'$L_0(x) = 2$, $L_1(x) = x$, and $L_{n}(x) = x L_{n-1}(x) + '
			r'L_{n-2}(x)$ for $n \geq 2$ (recurrence).',
		'formula-fibonacci':
			r'$L_n(x) = F_{n-1}(x) + F_{n+1}(x)$ for $n \geq 1$, where $F_n$ '
			r'are the Fibonacci polynomials HREF{Fibonacci_polynomials}.',
		'formula-generating-function':
			r'$\sum_{n=0}^\infty L_n(x) t^n = \frac{2 - xt}{1 - xt - t^2}$ '
			r'(generating function).',
		'formula-binet':
			r'$L_n(x) = \alpha^n + \beta^n$ where $\alpha, \beta = '
			r'\frac{x \pm \sqrt{x^2+4}}{2}$ are the roots of $z^2 - xz - 1$ '
			r'(Binet form). At $x = 1$, $\alpha$ is the golden ratio '
			r'HREF{Golden_ratio}.',
		'formula-doubling':
			r'$L_{2n}(x) = L_n(x)^2 - 2(-1)^n$.',
		'formula-pell':
			r'$L_n(x)^2 - (x^2+4)F_n(x)^2 = 4(-1)^n$.',
		'formula-coefficients':
			r'The coefficients are the rows of CITE{OEIS}.',
	},
	'Comments': {
		'comment-lucas-sequence': LUCAS_SEQUENCE_COMMENT,
		'comment-not-orthogonal': NOT_ORTHOGONAL.replace(
			'$F_n(x) = i^{n-1}U_{n-1}(-ix/2)$',
			'the same relation the Fibonacci polynomials have'),
	},
	'Links': {
		'Wiki': {'title': 'Wikipedia: Fibonacci polynomials (Lucas polynomials)',
		         'url': 'https://en.wikipedia.org/wiki/Fibonacci_polynomials'},
		'MathWorld': {'title': 'MathWorld: Lucas Polynomial',
		              'url': 'https://mathworld.wolfram.com/LucasPolynomial.html'},
		'OEIS': {'title': 'OEIS A034807: triangle of coefficients of Lucas polynomials',
		         'url': 'https://oeis.org/A034807'},
		'ChebyshevU': {'title': 'Wikipedia: Chebyshev polynomials',
		               'url': 'https://en.wikipedia.org/wiki/Chebyshev_polynomials'},
	},
	'Tags': ['polynomial', 'recurrence', 'generating function'],
}

for tid, changes in (('T108', FIBONACCI), ('T109', LUCAS)):
	table = Table.objects.get(tid=tid)
	tree = dict(tree_of(table.head_revision))
	for section, value in changes.items():
		if section == 'Links':
			merged = dict(value)
			merged.update(SHARED_LINKS)
			tree['Links'] = merged
		elif section == 'Tags':
			tree['Tags'] = value
		else:
			tree[section] = value
	tree['References'] = dict(SHARED_REFERENCES)

	print('%s: %d formulas, %d comments, %d links, %d references, tags %s'
	      % (tid, len(tree['Formulas']), len(tree['Comments']),
	         len(tree['Links']), len(tree['References']), tree['Tags']))

	if APPLY:
		commit_table(
			table, tree, author=AUTHOR, base=table.head_revision,
			produced_by=PRODUCED_BY,
			message='references, cross-links and the identities, each checked '
			        'in Sage over the whole range before being written down')
		print('   committed')

if not APPLY:
	print('\ndry run; set APPLY=1 to commit')
