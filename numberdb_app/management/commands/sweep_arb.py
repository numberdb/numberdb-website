"""Recompute stored values in ball arithmetic and report anything wrong.

This is the expensive check. Every entry it covers is computed again from a
definition written here -- not from the table's own script, which is somebody
else's code and is not run -- at enough precision to decide every digit stored,
and compared against what the table holds. A value outside one unit in the last
place is wrong: that is what the written form promises.

    manage.py sweep_arb                       # everything in the registry
    manage.py sweep_arb --only T9,T14         # some of it
    manage.py sweep_arb --restart             # ignore the checkpoint

**It is resumable.** Each entry's verdict is appended to a checkpoint file and
flushed, so a run that is killed -- a reboot, a deploy, an impatient ^C -- loses
at most the entry in flight, and starting again skips what is already decided.
That matters because the whole sweep is hours of arithmetic: without this it
could only ever be run by somebody willing to sit and watch it.

**It writes nothing to any table.** Findings are for a person to read and act
on. Two of the errors it exists to find -- T93's wrong tails, T32's wrong sign
-- needed a decision about what the right value was, and a program that
corrected them unattended would have made that decision by itself.

Why not simply run each table's generator? For the fifteen tables that have
one, `verify` is the better check and this does not duplicate it. The rest have
no generator, and their `generate.sage` cannot be run here: it is arbitrary
code, from a repository this server has no business executing.
"""

import json
import os
import time

from django.core.management.base import BaseCommand, CommandError


#: How much wider than the stored digits to compute before giving up on an
#: entry. Doubling four times is 16x the starting precision, which is far more
#: than any entry here has needed; the cap exists so that one pathological
#: value cannot spend the night on its own.
ESCALATIONS = 4

#: A stored value is read with the site's own parsers -- `parse_real_interval`
#: and `parse_complex_interval` -- rather than by measuring digits here. They
#: are what the rest of the site means by a written value: `3.14` *is* the
#: interval (3.13, 3.15). A recomputation that misses that interval entirely is
#: a value this database has got wrong; anything else is a difference of
#: opinion about the last digit, which the convention already allows for.
#:
#: The distance is still reported in units of the last place, because "wrong by
#: 386 ulp" says how bad it is and "does not overlap" does not.
TOLERANCE = 1.0


def _recomputations():
	"""Table id -> a function from parameters to a ball, or None to skip.

	Each is written from the table's stated definition. Where an entry is
	exact, or is prose, or is a kind this cannot decide, the function returns
	None and the entry is recorded as skipped rather than silently passed --
	a sweep that quietly checks nothing looks exactly like one that finds
	nothing wrong.
	"""
	from sage.all import CBF, QQ, RBF, ZZ, ComplexBallField, RealBallField

	def gamma_at_rationals(params, field):
		s = QQ(params['s'])
		if s.denominator() == 1 and s <= 0:
			return None                      # a pole; the table says so in prose
		return field(s).gamma()

	def zeta_at_rationals(params, field):
		s = QQ(params['s'])
		if s == 1:
			return None                      # the pole
		#The trivial zeros are exact and are stored as `0`; a ball around zero
		#cannot confirm an exact zero, so they are left to the exact check.
		if s.denominator() == 1 and s < 0 and ZZ(s) % 2 == 0:
			return None
		return field(s).zeta()

	def sphere_volume(params, field):
		#S_d = 2 pi^((d+1)/2) / Gamma((d+1)/2), the surface of the unit ball
		#in R^(d+1). At d = -1 that is 2/Gamma(0) = 0, which the table stores
		#as an exact 0 -- so it is skipped here rather than compared to a ball
		#that merely contains zero.
		d = ZZ(params['d'])
		if d == -1:
			return None
		half = QQ(d + 1) / 2
		return 2 * field.pi() ** half / field(half).gamma()

	def cos_pi_x(params, field):
		x = QQ(params['x'])
		#cos(pi x) is rational exactly when x is a multiple of 1/2 or 1/3;
		#those are stored exactly and are not this check's business.
		if x.denominator() in (1, 2, 3):
			return None
		return (field(x) * field.pi()).cos()

	def root_of_unity(params, field):
		n, k = ZZ(params['n']), ZZ(params['k'])
		if QQ(k) / n * 4 in ZZ:              # 1, i, -1, -i and friends: exact
			return None
		complex_field = ComplexBallField(field.precision())
		return (2 * complex_field.pi() * complex_field(0, 1) * k / n).exp()

	def polygon_area(params, field):
		#The regular n-gon under each of the three normalisations the table
		#lists. Checked at n = 3, side 1: 3/(4 tan(pi/3)) = 0.4330127..., and
		#at n = 4, where the square of side 1 has area exactly 1.
		n = ZZ(params['n'])
		which = params['expression']
		angle = field.pi() / n
		if which == 'unit-s':                # side length 1
			if n == 4:
				return None                  # exactly 1, and stored as such
			return n / (4 * angle.tan())
		if which == 'unit-R':                # circumradius 1
			return n * (2 * angle).sin() / 2
		if which == 'unit-r':                # inradius (apothem) 1
			return n * angle.tan()
		return None

	def _platonic(field):
		"""Edge 1: volume, surface area, and the three radii, per solid.

		Standard formulas, but checked against the table's own `unit-a` and
		`unit-r` columns before being trusted: a wrong radius here would be
		invisible in the edge-1 column and wrong in the other four.
		"""
		two, three, five, six = (field(n).sqrt() for n in (2, 3, 5, 6))
		golden = (1 + five) / 2
		return {
			'tetrahedron': {
				'V': two / 12, 'A': three,
				'r': 1 / (2 * six), 'rho': 1 / (2 * two), 'R': six / 4},
			'cube': {
				'V': field(1), 'A': field(6),
				'r': field(1) / 2, 'rho': two / 2, 'R': three / 2},
			'octahedron': {
				'V': two / 3, 'A': 2 * three,
				'r': 1 / six, 'rho': field(1) / 2, 'R': 1 / two},
			'dodecahedron': {
				'V': (15 + 7 * five) / 4,
				'A': 3 * (25 + 10 * five).sqrt(),
				#r = (a/2) sqrt((25 + 11 sqrt5)/10). Written wrong the first
				#time, as sqrt(5(25+11 sqrt5)/10)/2, which is the same thing
				#multiplied by sqrt5 -- and invisible in four of the five
				#columns, since only `unit-r` divides by it.
				'r': ((25 + 11 * five) / 10).sqrt() / 2,
				'rho': (3 + five) / 4,
				'R': three * (1 + five) / 4},
			'icosahedron': {
				'V': 5 * (3 + five) / 12,
				'A': 5 * three,
				'r': three * (3 + five) / 12,
				'rho': (1 + five) / 4,
				'R': (10 + 2 * five).sqrt() / 4},
		}

	def platonic_volume(params, field):
		solid = _platonic(field).get(params['solid'])
		if solid is None:
			return None
		which = params['expression']
		if which == 'unit-a':
			return solid['V']
		if which == 'unit-A':                # scaled so the surface area is 1
			return solid['V'] / solid['A'] ** (QQ(3) / 2)
		length = {'unit-r': 'r', 'unit-rho': 'rho', 'unit-R': 'R'}.get(which)
		if length is None:
			return None
		return solid['V'] / solid[length] ** 3

	def platonic_area(params, field):
		solid = _platonic(field).get(params['solid'])
		if solid is None:
			return None
		which = params['expression']
		if which == 'unit-a':
			return solid['A']
		if which == 'unit-V':                # scaled so the volume is 1
			return solid['A'] / solid['V'] ** (QQ(2) / 3)
		length = {'unit-r': 'r', 'unit-rho': 'rho', 'unit-R': 'R'}.get(which)
		if length is None:
			return None
		return solid['A'] / solid[length] ** 2

	def sobolev(params, field):
		#The table gives both formulas itself, from Aubin and Talenti for
		#p > 1 and from Federer-Fleming and Maz'ya for p = 1, so this is its
		#own statement recomputed rather than a formula found elsewhere.
		n, exponent = ZZ(params['n']), QQ(params['p'])
		half = field.pi().sqrt()
		if exponent == 1:
			return half * n / (field(1 + QQ(n) / 2).gamma()) ** (QQ(1) / n)
		if exponent >= n:
			return None
		first = field(n) ** (1 / exponent)
		second = (field(QQ(n) - exponent) / (exponent - 1)) ** (1 - 1 / exponent)
		ratio = (field(QQ(n) / exponent).gamma()
		         * field(QQ(n) + 1 - QQ(n) / exponent).gamma()
		         / (field(n).gamma() * field(1 + QQ(n) / 2).gamma()))
		return half * first * second * ratio ** (QQ(1) / n)

	#The completed zeta's Taylor series, built once per table. It costs about
	#a minute and every entry of the table reads a coefficient out of it, so
	#building it per entry would turn a minute into eight hours.
	xi_cache = {}

	def _xi_series(s0, degree, bits):
		"""The Taylor series of xi(s0 + t), in ball arithmetic.

		    xi(s) = (1/2) s(s-1) pi^(-s/2) Gamma(s/2) zeta(s)

		Sage has no zeta of a power series over a ball field, so the series is
		assembled from the pieces arb does have: `zetaderiv(k)` for zeta,
		`psi(k-1)` -- polygamma -- for log Gamma, and the power series
		exponential for both that and pi^(-s/2).

		The precision is high and has to be. At s0 = 1/2 the log Gamma series
		has radius 1/2, so its coefficients grow like 2^k and reach about 1e75
		by k = 250, while the coefficient they combine to give is 1.5e-471.
		Everything in between cancels: some 546 orders of magnitude, which no
		amount of care in the arithmetic avoids and only working precision
		covers. At 1400 bits the answer at k = 250 has no correct digits at
		all; at 2600 it has 232.
		"""
		from sage.all import ComplexBallField, PowerSeriesRing, factorial

		key = (s0, degree, bits)
		if key in xi_cache:
			return xi_cache[key]

		field = ComplexBallField(bits)
		ring = PowerSeriesRing(field, 't', default_prec=degree + 1)
		t = ring.gen()
		s = field(s0) + t

		polynomial = s * (s - 1) / 2
		power = (-s * field.pi().log() / 2).exp()

		#log Gamma(z + u) = log Gamma(z) + sum psi^(k-1)(z) u^k / k!
		z, u = field(s0) / 2, t / 2
		log_gamma = ring(z.log_gamma())
		for k in range(1, degree + 1):
			log_gamma += ring(z.psi(k - 1) / factorial(k)) * u ** k

		zeta = ring(0)
		for k in range(degree + 1):
			zeta += ring(field(s0).zetaderiv(k) / factorial(k)) * t ** k

		series = polynomial * power * log_gamma.exp() * zeta
		xi_cache[key] = series
		return series

	def _xi_coefficient(s0, params):
		from sage.all import factorial

		n = ZZ(params['n'])
		series = _xi_series(s0, 251, 2600)
		coefficient = series[int(n)]
		if not coefficient.imag().contains_zero():
			return None                      # xi is real on the real axis
		value = coefficient.real()
		if params['expression'] == 'a_n':
			return value * factorial(int(n))
		if params['expression'] == 'a_n/n!':
			return value
		return None

	def xi_at_half(params, field):
		return _xi_coefficient(QQ(1) / 2, params)

	def xi_at_two(params, field):
		return _xi_coefficient(QQ(2), params)

	def agm(params, field):
		a, b = QQ(params['a']), QQ(params['b'])
		if a == b:
			return None                      # exact, and stored as such
		return field(a).agm(field(b))

	return {
		'T9': ('real', gamma_at_rationals),
		'T14': ('real', zeta_at_rationals),
		'T15': ('real', xi_at_half),
		'T17': ('real', polygon_area),
		'T33': ('real', xi_at_two),
		'T28': ('real', sphere_volume),
		'T51': ('real', agm),
		'T85': ('real', platonic_volume),
		'T86': ('real', platonic_area),
		'T92': ('real', sobolev),
		'T60': ('real', root_of_unity),
		'T61': ('real', cos_pi_x),
	}


def _p_adic_recomputations():
	"""The p-adic tables, computed from their definitions.

	Deliberately not by calling the same Sage function the original script
	called. `Qp(p, n)(k).log()` checked against `Qp(p, n)(k).log()` establishes
	that the digits were transcribed and truncated correctly -- which is worth
	something, and is exactly the class of error T93 turned out to be -- but it
	cannot notice that the function is wrong. The series and products below are
	the definitions themselves, so they can.

	Each takes the parameters and a working precision in powers of p, and
	returns an element of Qp.
	"""
	from sage.all import QQ, Qp, ZZ

	def teichmuller(params, prec):
		#omega(k) is the unique (p-1)st root of unity congruent to k mod p,
		#and k^(p^n) converges to it: the limit is the definition, so this is
		#not Sage's teichmuller() checking itself.
		p, k = ZZ(params['p']), ZZ(params['k'])
		field = Qp(p, prec + 5)

		#p = 2 is not that limit. The character is on (Z/4)^*, so omega takes
		#the values +/-1 and is fixed by k mod 4 -- and squaring destroys
		#exactly the sign that carries the answer: k^(2^n) tends to 1 whatever
		#k was, which is why omega(-1) came back as 1 rather than -1.
		if p == 2:
			return field(1) if k % 4 == 1 else field(-1)

		x = field(k)
		for _ in range(prec + 2):
			x = x ** p
		return x

	def p_adic_log(params, prec):
		#log(1+u) = sum (-1)^(n+1) u^n/n converges only for v(u) > 0, which
		#covers k = 1 mod p and no more. The table says that is its range --
		#the parameter constraint reads "k = 1 mod p" -- and it is not: 702 of
		#its 856 entries are outside it, p = 3 with k = -49 among them. The
		#logarithm is defined there anyway, by the standard extension: it is
		#the Iwasawa branch, log_p(p) = 0, and on units log(u) is recovered
		#from log(u^(p-1)), whose argument is 1 mod p whatever u was.
		p, k = ZZ(params['p']), ZZ(params['k'])
		if k == 0:
			return None
		field = Qp(p, prec + 30)
		x = field(k)

		#log_p(p) = 0, so only the unit part contributes.
		unit = x / field(p) ** x.valuation()
		raised = unit ** int(p - 1)

		u = raised - 1
		if u.valuation() < 1:
			return None
		total, term_n = field(0), 1
		while term_n < 6 * (prec + 30):
			total += (-1) ** (term_n + 1) * u ** term_n / field(term_n)
			term_n += 1
		return total / field(p - 1)

	def p_adic_exp(params, prec):
		#exp(x) = sum x^n / n!, converging when v(x) > 1/(p-1).
		from sage.functions.other import factorial

		p, k = ZZ(params['p']), ZZ(params['k'])
		field = Qp(p, prec + 20)
		x = field(k)
		if x != 0 and x.valuation() * (p - 1) <= 1:
			return None                      # outside the region of convergence
		total, n = field(1), 1
		while n < 4 * (prec + 20):
			total += x ** n / field(factorial(n))
			n += 1
		return total

	def p_adic_gamma(params, prec):
		#Morita's Gamma_p: for n >= 1 the product of the units below n, with a
		#sign; elsewhere by the functional equation, walked down from
		#Gamma_p(1) = -1.
		p, k = ZZ(params['p']), ZZ(params['k'])
		field = Qp(p, prec + 5)
		if k >= 1:
			product = field(1)
			for j in range(1, int(k)):
				if j % p:
					product *= field(j)
			return (-1) ** int(k) * product
		#Gamma_p(x) = -Gamma_p(x+1)/x when p does not divide x, and
		#-Gamma_p(x+1) when it does.
		value = field(-1)                    # Gamma_p(1)
        # walk from 1 down to k
		x = ZZ(1)
		while x > k:
			x -= 1
			value = -value / field(x) if x % p else -value
		return value

	#The Artin-Hasse series depends only on p and how far it is taken, not on
	#where it is evaluated, so it is built once per table rather than once per
	#entry -- a degree-190 formal exponential a thousand times over is the
	#difference between a minute and an hour.
	series_cache = {}

	def artin_hasse(params, prec):
		#E_p(x) = exp(sum_n x^(p^n)/p^n), as a *formal* power series over Q
		#which is then evaluated.
		#
		#Not by exponentiating the sum in Q_p. That was the first attempt and
		#it was wrong for the reason the Artin-Hasse exponential exists: the
		#p-adic exp converges only for v(x) > 1/(p-1), which at p = 2 means
		#v(x) > 1, and this table's arguments have v(x) = 1. E_p is defined
		#there anyway, because its *coefficients* are p-integral even though
		#the exponential series is not summable. Eleven of twelve trial
		#entries were reported wrong before this was understood; the table
		#was right every time.
		from sage.all import PowerSeriesRing
		from sage.rings.rational_field import QQ as rationals

		p, k = ZZ(params['p']), ZZ(params['k'])
		field = Qp(p, prec + 20)
		x = field(k)
		if x != 0 and x.valuation() < 1:
			return None                      # the table asks for |k|_p < 1

		#v(c_m x^m) >= m since the coefficients are p-integral, so the series
		#is taken a little past the precision asked for and no further.
		degree = int(prec) + 10
		key = (int(p), degree)
		if key not in series_cache:
			ring = PowerSeriesRing(rationals, 't', default_prec=degree + 1)
			t = ring.gen()
			inner = ring(0)
			n = 0
			while p ** n <= degree:
				inner += t ** int(p ** n) / rationals(p) ** n
				n += 1
			series_cache[key] = list(inner.exp(prec=degree + 1))

		total = field(0)
		power = field(1)
		for coefficient in series_cache[key]:
			if coefficient:
				total += field(coefficient) * power
			power *= x
		return total

	def p_adic_agm(params, prec):
		#a_{n+1} = (a_n + g_n)/2, g_{n+1} = sqrt(a_n g_n) -- taking the root
		#nearer to a_{n+1}, the *new* arithmetic mean.
		#
		#Which root is not a detail here. Both lie in Q_p and they lead to
		#different limits, and the table's definition does not say. The rule
		#above is PARI's, established by asking it: the agm is unchanged by one
		#step, so `agm(a,b) == agm((a+b)/2, r)` holds for the root PARI took
		#and not for the other. Measured over six cases at four primes it took
		#the root nearer the new mean every time, and with that rule all 990
		#stored entries reproduce, p = 2 included.
		#
		#The first attempt compared against a_n, the *old* value, which is the
		#natural misreading and gives a different number entirely -- not a sign
		#difference, a different limit. It reported every odd-prime entry as
		#wrong.
		p = ZZ(params['p'])
		field = Qp(p, prec + 25)
		a, g = field(QQ(params['a'])), field(QQ(params['b']))
		for _ in range(prec + 25):
			if (a - g).valuation() >= prec + 8:
				break
			mean = (a + g) / 2
			product = a * g
			if not product.is_square():
				return None
			root = product.sqrt()
			g = max([root, -root], key=lambda t: (t - mean).valuation())
			a = mean
		return a

	return {
		'T44': ('padic', teichmuller),
		'T45': ('padic', p_adic_log),
		'T46': ('padic', p_adic_exp),
		'T47': ('padic', p_adic_gamma),
		'T48': ('padic', artin_hasse),
		'T52': ('padic', p_adic_agm),
		#T52 was left out for a day: its definition does not say which square
		#root the iteration takes, and the wrong reading gives a different limit
		#rather than a near miss. The rule is in `p_adic_agm` above, and the
		#table now states it too.
	}


def _significant(text):
	"""How many significant digits a written value carries."""
	body = text.strip().lstrip('-').split(' ')[0]
	return len(body.replace('.', '').lstrip('0'))


def _decided(ball, digits):
	"""Whether this ball settles that many significant digits."""
	if ball.rad() == 0:
		return True
	from sage.all import RealField
	mid = abs(RealField(64)(ball.mid()))
	if mid == 0:
		return False
	relative = RealField(64)(ball.rad()) / mid
	return relative < RealField(64)(10) ** (-digits - 1)


class Command(BaseCommand):
	help = 'Recompute stored values in ball arithmetic and report differences.'

	def add_arguments(self, parser):
		parser.add_argument('--out', default='/numberdb-data/sweep-arb.jsonl',
		                    help='checkpoint and findings, one JSON per line')
		parser.add_argument('--only', default='',
		                    help='comma-separated table ids')
		parser.add_argument('--restart', action='store_true',
		                    help='ignore the checkpoint and do it all again')
		parser.add_argument('--limit', type=int, default=0,
		                    help='stop after this many entries (for a trial)')

	def handle(self, *args, **options):
		from sage.all import ComplexBallField, RealBallField, RealField

		from numberdb_app.editing import tree_of
		from numberdb_app.models import Table

		path = options['out']
		recomputations = dict(_recomputations())
		recomputations.update(_p_adic_recomputations())

		only = [t.strip() for t in options['only'].split(',') if t.strip()]
		if only:
			unknown = [t for t in only if t not in recomputations]
			if unknown:
				raise CommandError('no recomputation for: %s' % ', '.join(unknown))
			wanted = only
		else:
			wanted = sorted(recomputations, key=lambda t: int(t[1:]))

		done = set()
		if options['restart']:
			if os.path.exists(path):
				os.remove(path)
		elif os.path.exists(path):
			for line in open(path, encoding='utf8'):
				try:
					row = json.loads(line)
				except ValueError:
					continue                 # a line torn in half by a kill
				if 'table' in row and 'identity' in row:
					done.add((row['table'], row['identity']))
			self.stdout.write('resuming: %d entries already decided' % len(done))

		os.makedirs(os.path.dirname(path) or '.', exist_ok=True)
		#A process killed mid-write leaves a line with no newline on it. Append
		#to that and the two records merge into one that parses as neither, so
		#the torn entry takes the next one down with it. One newline costs
		#nothing and confines the damage to the entry that was in flight.
		if os.path.exists(path) and os.path.getsize(path):
			with open(path, 'rb') as tail:
				tail.seek(-1, os.SEEK_END)
				unterminated = tail.read(1) != b'\n'
			if unterminated:
				with open(path, 'a', encoding='utf8') as mend:
					mend.write('\n')
		handle = open(path, 'a', encoding='utf8')

		checked = skipped = wrong = 0
		started = time.time()
		for tid in wanted:
			kind, recompute = recomputations[tid]
			try:
				table = Table.objects.get(tid=tid)
			except Table.DoesNotExist:
				self.stderr.write('%s: no such table' % tid)
				continue

			entries = [e for e in (tree_of(table.head_revision).get('Numbers') or [])
			           if isinstance(e, dict) and e.get('number')]
			self.stdout.write('%s: %d entries' % (tid, len(entries)))

			for entry in entries:
				identity = json.dumps(entry['params'], sort_keys=True)
				if (tid, identity) in done:
					continue
				if options['limit'] and checked + skipped >= options['limit']:
					break

				stored = entry['number']
				exact_looking = (not isinstance(stored, str)
				                 or ('.' not in stored and 'O(' not in stored))
				if exact_looking:
					row = {'table': tid, 'identity': identity, 'verdict': 'exact'}
					skipped += 1
				elif kind == 'padic':
					row = self._check_p_adic(tid, identity, stored,
					                         entry['params'], recompute)
					if row['verdict'] == 'wrong':
						wrong += 1
						self.stdout.write('  WRONG %s %s' % (tid, identity))
					elif row['verdict'] == 'ok':
						checked += 1
					else:
						skipped += 1
				else:
					row = self._check(tid, identity, stored, entry['params'],
					                  recompute)
					if row['verdict'] == 'wrong':
						wrong += 1
						self.stdout.write(
							'  WRONG %s %s: off by %s ulp'
							% (tid, identity, row.get('ulps')))
					elif row['verdict'] == 'ok':
						checked += 1
					else:
						skipped += 1

				handle.write(json.dumps(row, sort_keys=True) + '\n')
				handle.flush()
				os.fsync(handle.fileno())

		handle.close()
		self.stdout.write(
			'%d checked, %d skipped, %d wrong, in %d seconds.'
			% (checked, skipped, wrong, time.time() - started))
		if wrong:
			self.stdout.write('Findings are the "wrong" lines in %s' % path)

	def _check(self, tid, identity, stored, params, recompute):
		"""One entry, at whatever precision it takes to decide it."""
		from sage.all import ComplexIntervalField, RealField, RealIntervalField
		from utils.utils import parse_complex_interval, parse_real_interval

		digits = _significant(stored)
		bits = int(digits * 3.33) + 64
		complex_value = 'i' in stored.lower()

		for attempt in range(ESCALATIONS + 1):
			from sage.all import RealBallField

			field = RealBallField(bits)
			try:
				ball = recompute(params, field)
			except Exception as trouble:      # a definition that does not apply
				return {'table': tid, 'identity': identity,
				        'verdict': 'error', 'detail': str(trouble)[:200]}
			if ball is None:
				return {'table': tid, 'identity': identity, 'verdict': 'skipped'}

			parts = ([ball.real(), ball.imag()] if hasattr(ball, 'imag')
			         else [ball])
			if all(_decided(part, digits) or part.contains_zero()
			       for part in parts):
				break
			bits *= 2
		else:
			return {'table': tid, 'identity': identity, 'verdict': 'undecided',
			        'detail': 'still too wide at %d bits' % bits}

		#Read the stored text the way the site reads it, so this agrees with
		#what a reader is told the value means rather than with a rule
		#reinvented here.
		precision = max(int(digits * 3.33) + 128, bits)
		try:
			if complex_value:
				held = parse_complex_interval(
					stored, CIF=ComplexIntervalField(precision))
				computed = ComplexIntervalField(precision)(
					ball.real().mid(), ball.imag().mid()) \
					if hasattr(ball, 'imag') else \
					ComplexIntervalField(precision)(ball.mid(), 0)
			else:
				held = parse_real_interval(
					stored, RIF=RealIntervalField(precision))
				computed = RealIntervalField(precision)(ball.mid())
		except Exception as trouble:
			return {'table': tid, 'identity': identity, 'verdict': 'unparsed',
			        'detail': str(trouble)[:200]}
		if held is None:
			return {'table': tid, 'identity': identity, 'verdict': 'unparsed'}

		if held.overlaps(computed):
			return {'table': tid, 'identity': identity, 'verdict': 'ok',
			        'digits': digits}

		#Wrong. Say by how much, in the units the value was written in.
		exact = RealField(precision)
		body = stored.split('+')[0].split('-')[0] if complex_value else stored
		places = len(body.split('.')[1].strip()) if '.' in body else 0
		ulp = exact(10) ** (-places) if places else exact(1)
		try:
			off = float(abs(exact(held.center().real() if complex_value
			                      else held.center())
			                - exact(computed.center().real() if complex_value
			                        else computed.center())) / ulp)
		except Exception:
			off = None
		return {'table': tid, 'identity': identity, 'verdict': 'wrong',
		        'ulps': round(off, 3) if off is not None else None,
		        'digits': digits, 'stored': stored[:80],
		        'computed': str(computed.center())[:80]}

	def _check_p_adic(self, tid, identity, stored, params, recompute):
		"""One p-adic entry, to the precision the stored value states.

		A p-adic value says how far it is known -- `... + O(2^167)` -- so there
		is no question of how many digits to compare: the difference must
		vanish to exactly that precision, and this is one of the few checks
		here with no tolerance in it at all.
		"""
		from utils.utils import parse_p_adic

		try:
			held = parse_p_adic(stored)
		except Exception as trouble:
			return {'table': tid, 'identity': identity, 'verdict': 'unparsed',
			        'detail': str(trouble)[:200]}
		if held is None:
			return {'table': tid, 'identity': identity, 'verdict': 'unparsed'}

		precision = held.precision_absolute()
		try:
			computed = recompute(params, int(precision))
		except Exception as trouble:
			return {'table': tid, 'identity': identity, 'verdict': 'error',
			        'detail': str(trouble)[:200]}
		if computed is None:
			return {'table': tid, 'identity': identity, 'verdict': 'skipped'}

		difference = held - computed
		agrees = difference.is_zero() or difference.valuation() >= precision
		if agrees:
			return {'table': tid, 'identity': identity, 'verdict': 'ok',
			        'digits': int(precision)}
		return {'table': tid, 'identity': identity, 'verdict': 'wrong',
		        'digits': int(precision),
		        'agrees_to': int(difference.valuation()),
		        'stored': stored[:80], 'computed': str(computed)[:80]}
