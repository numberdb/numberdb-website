"""Put T108 and T109 in order: each thing in the section it belongs to.

    manage.py shell < scripts/one-off/enrich-polynomial-tables.py   (APPLY=1 to commit)

The definitions had grown to hold a definition, two conventions, a caveat about
indexing and a pointer to the companion table. A definition should say what the
object is; the rest has sections of its own.

References to tables that exist here are internal -- `Similar tables` and
HREF -- rather than links to Wikipedia for something the database already
holds. Every identity below was checked in Sage over the whole range of the
tables before it was written down, and every external link was fetched.
"""
import os

from django.contrib.auth.models import User

from numberdb_app.editing import commit_table, tree_of
from numberdb_app.models import Table

APPLY = os.environ.get('APPLY') == '1'
AUTHOR = User.objects.get(username='bmatschke')
PRODUCED_BY = 'table document, assisted by claude-opus-5'

LUCAS_SEQUENCES = (
	r'For integers $P, Q$ the Lucas sequences CITE{WikiLucasSeq} are the two '
	r'solutions of $X_n = P X_{n-1} - Q X_{n-2}$ picked out by their starting '
	r'values: $U_0 = 0$, $U_1 = 1$ and $V_0 = 2$, $V_1 = P$. The polynomials '
	r'in this pair are the case $P = x$, $Q = -1$: $F_n(x) = U_n(x, -1)$ and '
	r'$L_n(x) = V_n(x, -1)$.')


def not_orthogonal(family, relation, weight, norm, chebyshev_href):
	"""Why the orthogonal polynomials tag does not belong on these tables.

	Per family, because the Fibonacci polynomials inherit from the Chebyshev
	polynomials of the second kind and the Lucas polynomials from those of the
	first, with different weights and different norms. The numbers came from
	Gauss-Chebyshev quadrature, which is exact for these weights -- Simpson is
	not, and gave a pairing of -0.023 for one that is exactly zero.
	"""
	return (
		r'These are <em>not</em> orthogonal polynomials in the usual sense. A '
		r'three-term recurrence $p_n = (x - c_n)p_{n-1} - k_n p_{n-2}$ gives a '
		r'family orthogonal for a positive measure on $\mathbb{R}$ exactly when '
		r'$k_n > 0$ (Favard), and here $k_n = -1$. What holds instead comes '
		r'from ' + chebyshev_href + r' through ' + relation + r': along the '
		r'segment $x = 2it$, $t \in [-1,1]$, with weight ' + weight + r', '
		r'distinct ' + family + r' pair to zero, while $\langle ' + norm[0] +
		r'\rangle$ alternates between $\pm' + norm[1] + r'$ &mdash; an '
		r'indefinite form rather than an inner product.')


CHEBYSHEV_U = r'HREF{Chebyshev_polynomials_of_the_second_kind}[$U_n$]'
CHEBYSHEV_T = r'HREF{Chebyshev_polynomials_of_the_first_kind}[$T_n$]'
FIBONACCI_HREF = r'HREF{Fibonacci_polynomials}[Fibonacci polynomials]'
LUCAS_HREF = r'HREF{Lucas_polynomials}[Lucas polynomials]'
GOLDEN = r'HREF{Golden_ratio}[golden ratio]'

SHARED_LINKS = {
	'WikiLucasSeq': {'title': 'Wikipedia: Lucas sequence',
	                 'url': 'https://en.wikipedia.org/wiki/Lucas_sequence'},
}
SHARED_REFERENCES = {
	'Koshy': {'bib': 'Koshy, T., "Fibonacci and Lucas Numbers with '
	                 'Applications", Wiley-Interscience, 2001.'},
}

TABLES = {
	'T108': {
		'Definition':
			r'The Fibonacci polynomials $F_n$ are defined by $F_0 = 0$, '
			r'$F_1 = 1$ and $F_n(x) = x F_{n-1}(x) + F_{n-2}(x)$ for '
			r'$n \geq 2$.',
		'Comments': {
			'comment-at-one':
				r'At $x = 1$ the values are the Fibonacci numbers, and the '
				r'ratio $F_{n+1}(1)/F_n(1)$ tends to the ' + GOLDEN + r', '
				r'which is the larger root of $z^2 - z - 1$.',
			'comment-indexing':
				r'Some authors index these from $F_1 = 1$, so that every '
				r'polynomial listed here appears one place earlier. The '
				r'coefficients in CITE{OEIS} are indexed that way.',
			'comment-companion':
				r'The same recurrence started at $2$ and $x$ gives the '
				+ LUCAS_HREF + r', which are listed separately.',
			'comment-lucas-sequence': LUCAS_SEQUENCES,
			'comment-reference':
				r'CITE{Koshy} is a book-length treatment of both families and '
				r'of the numbers they specialise to.',
			'comment-not-orthogonal': not_orthogonal(
				r'$F_m, F_n$', r'$F_n(x) = i^{n-1}U_{n-1}(-ix/2)$',
				r'$\sqrt{1-t^2}$', (r'F_n, F_n', r'\pi/2'), CHEBYSHEV_U),
		},
		'Formulas': {
			'formula-closed':
				r'$F_n(x) = \sum_{k=0}^{\lfloor (n-1)/2 \rfloor} '
				r'\binom{n-k-1}{k} x^{n-2k-1}$.',
			'formula-generating-function':
				r'$\sum_{n=0}^\infty F_n(x) t^n = \frac{t}{1 - xt - t^2}$.',
			'formula-binet':
				r'$F_n(x) = \frac{\alpha^n - \beta^n}{\alpha - \beta}$, where '
				r'$\alpha, \beta = \frac{x \pm \sqrt{x^2+4}}{2}$ are the roots '
				r'of $z^2 - xz - 1$.',
			'formula-lucas':
				r'$L_n(x) = F_{n-1}(x) + F_{n+1}(x)$ and $F_{2n}(x) = '
				r'F_n(x)L_n(x)$, where $L_n$ are the ' + LUCAS_HREF + r'.',
			'formula-pell':
				r'$L_n(x)^2 - (x^2+4)F_n(x)^2 = 4(-1)^n$.',
			'formula-divisibility':
				r'$\gcd(F_m, F_n) = F_{\gcd(m,n)}$, so for $n > 2$ the '
				r'polynomial $F_n$ divides $F_m$ exactly when $n$ divides $m$.',
			'formula-chebyshev':
				r'$F_n(x) = i^{n-1} U_{n-1}(-ix/2)$, where $U_n$ are the '
				+ CHEBYSHEV_U + r'.',
		},
		'Similar tables': [
			{'relation': 'companion sequence',
			 'table': r'HREF{Lucas_polynomials}[Lucas polynomials]'},
			{'relation': 'related by $F_n(x) = i^{n-1}U_{n-1}(-ix/2)$',
			 'table': r'HREF{Chebyshev_polynomials_of_the_second_kind}'
			          r'[Chebyshev polynomials of the second kind]'},
			{'relation': 'limit of $F_{n+1}(1)/F_n(1)$',
			 'table': r'HREF{Golden_ratio}[golden ratio]'},
		],
		'Links': {
			'Wiki': {'title': 'Wikipedia: Fibonacci polynomials',
			         'url': 'https://en.wikipedia.org/wiki/Fibonacci_polynomials'},
			'MathWorld': {'title': 'MathWorld: Fibonacci Polynomial',
			              'url': 'https://mathworld.wolfram.com/FibonacciPolynomial.html'},
			'OEIS': {'title': 'OEIS A011973: coefficients, indexed from $F_{n+1}$',
			         'url': 'https://oeis.org/A011973'},
		},
	},
	'T109': {
		'Definition':
			r'The Lucas polynomials $L_n$ are defined by $L_0 = 2$, '
			r'$L_1 = x$ and $L_n(x) = x L_{n-1}(x) + L_{n-2}(x)$ for '
			r'$n \geq 2$.',
		'Comments': {
			'comment-at-one':
				r'At $x = 1$ the values are the Lucas numbers, and the ratio '
				r'$L_{n+1}(1)/L_n(1)$ tends to the ' + GOLDEN + r'.',
			'comment-indexing':
				r'Some authors index these from $L_1$, and elsewhere they are '
				r'called the Fibonacci polynomials of the second kind.',
			'comment-companion':
				r'They obey the same recurrence as the ' + FIBONACCI_HREF +
				r' and differ only in the two starting values, which is why '
				r'each table says which it holds.',
			'comment-lucas-sequence': LUCAS_SEQUENCES,
			'comment-coefficients':
				r'The coefficients are the rows of CITE{OEIS}.',
			'comment-reference':
				r'CITE{Koshy} is a book-length treatment of both families and '
				r'of the numbers they specialise to.',
			'comment-not-orthogonal': not_orthogonal(
				r'$L_m, L_n$', r'$L_n(x) = 2i^{n}T_{n}(-ix/2)$',
				r'$1/\sqrt{1-t^2}$', (r'L_n, L_n', r'2\pi'), CHEBYSHEV_T),
		},
		'Formulas': {
			'formula-fibonacci':
				r'$L_n(x) = F_{n-1}(x) + F_{n+1}(x)$ for $n \geq 1$, where '
				r'$F_n$ are the ' + FIBONACCI_HREF + r'.',
			'formula-generating-function':
				r'$\sum_{n=0}^\infty L_n(x) t^n = \frac{2 - xt}{1 - xt - t^2}$.',
			'formula-binet':
				r'$L_n(x) = \alpha^n + \beta^n$, where $\alpha, \beta = '
				r'\frac{x \pm \sqrt{x^2+4}}{2}$ are the roots of '
				r'$z^2 - xz - 1$.',
			'formula-doubling':
				r'$L_{2n}(x) = L_n(x)^2 - 2(-1)^n$.',
			'formula-pell':
				r'$L_n(x)^2 - (x^2+4)F_n(x)^2 = 4(-1)^n$.',
			'formula-chebyshev':
				r'$L_n(x) = 2i^{n} T_{n}(-ix/2)$, where $T_n$ are the '
				+ CHEBYSHEV_T + r'.',
		},
		'Similar tables': [
			{'relation': 'companion sequence',
			 'table': r'HREF{Fibonacci_polynomials}[Fibonacci polynomials]'},
			{'relation': 'related by $L_n(x) = 2i^{n}T_{n}(-ix/2)$',
			 'table': r'HREF{Chebyshev_polynomials_of_the_first_kind}'
			          r'[Chebyshev polynomials of the first kind]'},
			{'relation': 'limit of $L_{n+1}(1)/L_n(1)$',
			 'table': r'HREF{Golden_ratio}[golden ratio]'},
		],
		'Links': {
			'Wiki': {'title': 'Wikipedia: Fibonacci polynomials (Lucas polynomials)',
			         'url': 'https://en.wikipedia.org/wiki/Fibonacci_polynomials'},
			'MathWorld': {'title': 'MathWorld: Lucas Polynomial',
			              'url': 'https://mathworld.wolfram.com/LucasPolynomial.html'},
			'OEIS': {'title': 'OEIS A034807: triangle of coefficients of Lucas polynomials',
			         'url': 'https://oeis.org/A034807'},
		},
	},
}

for tid, sections in TABLES.items():
	table = Table.objects.get(tid=tid)
	tree = dict(tree_of(table.head_revision))
	for name, value in sections.items():
		if name == 'Links':
			merged = dict(value)
			merged.update(SHARED_LINKS)
			tree['Links'] = merged
		else:
			tree[name] = value
	tree['References'] = dict(SHARED_REFERENCES)
	tree['Tags'] = ['polynomial', 'recurrence', 'generating function']

	print('%s  definition %d chars, %d comments, %d formulas, %d similar, '
	      '%d links' % (tid, len(tree['Definition']), len(tree['Comments']),
	                    len(tree['Formulas']), len(tree['Similar tables']),
	                    len(tree['Links'])))
	if APPLY:
		commit_table(
			table, tree, author=AUTHOR, base=table.head_revision,
			produced_by=PRODUCED_BY,
			message='each thing in its own section, and tables in this '
			        'database referenced from here rather than from Wikipedia',
		via='orm')
		print('   committed')

if not APPLY:
	print('\ndry run; set APPLY=1 to commit')
