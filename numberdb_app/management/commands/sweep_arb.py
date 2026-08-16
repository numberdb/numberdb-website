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

	def agm(params, field):
		a, b = QQ(params['a']), QQ(params['b'])
		if a == b:
			return None                      # exact, and stored as such
		return field(a).agm(field(b))

	return {
		'T9': gamma_at_rationals,
		'T14': zeta_at_rationals,
		'T28': sphere_volume,
		'T51': agm,
		'T60': root_of_unity,
		'T61': cos_pi_x,
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
		recomputations = _recomputations()

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
			recompute = recomputations[tid]
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
				if not isinstance(stored, str) or '.' not in stored:
					row = {'table': tid, 'identity': identity, 'verdict': 'exact'}
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
