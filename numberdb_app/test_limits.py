"""Tests for how big a table may get.

The cases worth pinning down are the ones where the limit must *not* fire: a
complete table, a table that says why it is over, and every table already in
the corpus. A size limit that fires on ordinary content trains everybody to
ignore it, which is worse than having none.
"""

from django.contrib.auth.models import User
from django.test import SimpleTestCase, TestCase

from . import limits
from .editing import commit_table
from .models import Table


def _entries(n, digits=10):
	return {str(i): '0.' + ('1234567890' * ((digits // 10) + 1))[:digits]
	        for i in range(n)}


class Measuring(SimpleTestCase):

	def test_a_table_with_no_entries_measures_zero(self):
		self.assertEqual(limits.measure({'Title': 'x'}),
		                 {'entries': 0, 'digits': 0, 'bytes': 0})

	def test_entries_are_counted_through_nested_parameters(self):
		tree = {'Numbers': {'1': {'2': '3.14', '3': '2.71'}, '4': {'5': '1.61'}}}
		self.assertEqual(limits.measure(tree)['entries'], 3)

	def test_a_numbers_container_is_not_an_entry(self):
		"""The shape that has already collapsed three tables to two entries."""
		tree = {'Numbers': {'a_n': {'param-latex': 'a_n',
		                            'numbers': {'0': '1.1', '1': '2.2',
		                                        '2': '3.3'}}}}
		self.assertEqual(limits.measure(tree)['entries'], 3)

	def test_digits_are_counted_inside_an_entry_mapping(self):
		tree = {'Numbers': {'1': {'number': '3.' + '1' * 200,
		                          'comment': 'x'}}}
		self.assertEqual(limits.measure(tree)['digits'], 201)

	def test_a_comment_full_of_digits_is_not_a_value(self):
		"""Otherwise prose citing a year or an OEIS id inflates the count."""
		tree = {'Numbers': {'1': {'number': '3.14',
		                          'comment': '9' * 900}}}
		self.assertEqual(limits.measure(tree)['digits'], 3)


class SoftLimits(SimpleTestCase):

	def test_an_ordinary_table_is_within_everything(self):
		self.assertEqual(limits.check({'Numbers': _entries(50)}), [])

	def test_a_table_at_the_house_style_does_not_fire(self):
		"""1000 entries of 100 digits is what a typical table looks like."""
		self.assertEqual(
			limits.check({'Numbers': _entries(1000, digits=100)}), [])

	def test_too_many_entries_is_flagged(self):
		breaches = limits.check({'Numbers': _entries(limits.SOFT_ENTRY_COUNT + 1)})
		self.assertEqual([b.kind for b in breaches], ['entries'])
		self.assertFalse(breaches[0].hard)

	def test_too_many_digits_is_flagged(self):
		tree = {'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}}
		self.assertEqual([b.kind for b in limits.check(tree)], ['digits'])

	def test_the_block_limit_catches_what_the_other_two_miss(self):
		"""Under both counts, over the total: the balance the third limit is for."""
		tree = {'Numbers': _entries(1100, digits=400)}
		kinds = [b.kind for b in limits.check(tree)]
		self.assertEqual(kinds, ['bytes'])


class CompletenessExemptsTheCount(SimpleTestCase):
	"""Truncating a complete table does not make it smaller, it makes it wrong."""

	def tree(self, complete):
		return {'Data properties': {'complete': complete},
		        'Numbers': _entries(limits.SOFT_ENTRY_COUNT + 500)}

	def test_a_complete_table_may_hold_as_many_as_it_has(self):
		self.assertEqual(limits.check(self.tree('yes')), [])

	def test_an_incomplete_one_of_the_same_size_is_flagged(self):
		self.assertEqual([b.kind for b in limits.check(self.tree('no'))],
		                 ['entries'])

	def test_the_word_no_is_read_as_a_word(self):
		"""YAML 1.1 would make this a boolean; the corpus reads with BaseLoader."""
		self.assertFalse(limits.claims_completeness(
			{'Data properties': {'complete': 'no'}}))

	def test_completeness_does_not_excuse_the_hard_ceiling(self):
		tree = {'Data properties': {'complete': 'yes'},
		        'Numbers': _entries(limits.HARD_ENTRY_COUNT + 1)}
		entries = [b for b in limits.check(tree) if b.kind == 'entries']
		self.assertEqual(len(entries), 1)
		self.assertTrue(entries[0].hard)

	def test_completeness_excuses_the_count_but_not_the_writing(self):
		"""Which rows exist is mathematics; how much is written per row is not.

		So a complete table that is also very large still has to say why, and
		the sentence is a cheap one to write.
		"""
		tree = {'Data properties': {'complete': 'yes'},
		        'Numbers': _entries(2000, digits=400)}
		self.assertEqual([b.kind for b in limits.check(tree)], ['bytes'])


class StatedReasons(SimpleTestCase):

	def over(self):
		return {'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}}

	def test_without_a_reason_the_breach_is_reported(self):
		self.assertEqual(len(limits.enforce(self.over())), 1)

	def test_a_reason_settles_it(self):
		tree = self.over()
		tree['Data properties'] = {
			limits.EXCEPTION_KEY: 'these 2000 digits took three CPU-months'}
		self.assertEqual(limits.enforce(tree), [])

	def test_an_empty_reason_is_not_a_reason(self):
		tree = self.over()
		tree['Data properties'] = {limits.EXCEPTION_KEY: '   '}
		self.assertEqual(len(limits.enforce(tree)), 1)

	def test_a_reason_does_not_excuse_a_hard_limit(self):
		tree = {'Data properties': {limits.EXCEPTION_KEY: 'I really want to'},
		        'Numbers': {'1': '0.' + '1' * (limits.HARD_DIGITS + 1)}}
		with self.assertRaises(limits.TooBig):
			limits.enforce(tree)


class StrictWritersMustExplainThemselves(SimpleTestCase):
	"""A warning shown to nobody is not a limit.

	A person editing on the site is told and their edit is saved, because they
	have judgement to exercise. A script has none, so it has to put the reason
	in the document before it is allowed over.
	"""

	def test_a_script_is_refused_where_a_person_would_be_warned(self):
		tree = {'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}}
		self.assertEqual(len(limits.enforce(tree, strict=False)), 1)
		with self.assertRaises(limits.TooBig):
			limits.enforce(tree, strict=True)

	def test_a_script_that_explains_itself_is_allowed(self):
		tree = {'Data properties': {limits.EXCEPTION_KEY: 'expensive to compute'},
		        'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}}
		self.assertEqual(limits.enforce(tree, strict=True), [])


class ThroughCommitTable(TestCase):

	def setUp(self):
		self.table = Table.objects.create(tid='T930', tid_int=930,
		                                  title='Limit probe', url='Limit930')
		self.alice = User.objects.create_user('alice_l', password='pw-123456')

	def test_a_soft_breach_is_saved_and_reported(self):
		out = commit_table(
			self.table,
			{'Title': 'Limit probe',
			 'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}},
			author=self.alice,
		via='orm')
		self.assertIsNotNone(out.revision)
		self.assertEqual([b.kind for b in out.breaches], ['digits'])
		self.table.refresh_from_db()
		self.assertIsNotNone(self.table.head_revision)

	def test_a_hard_breach_writes_nothing(self):
		with self.assertRaises(limits.TooBig):
			commit_table(
				self.table,
				{'Title': 'Limit probe',
				 'Numbers': {'1': '0.' + '1' * (limits.HARD_DIGITS + 1)}},
				author=self.alice,
		via='orm')
		self.table.refresh_from_db()
		self.assertIsNone(self.table.head_revision)

	def test_strict_refuses_a_soft_breach_and_writes_nothing(self):
		with self.assertRaises(limits.TooBig):
			commit_table(
				self.table,
				{'Title': 'Limit probe',
				 'Numbers': {'1': '0.' + '1' * (limits.SOFT_DIGITS + 1)}},
				author=self.alice, strict=True,
		via='orm')
		self.table.refresh_from_db()
		self.assertIsNone(self.table.head_revision)


class TheCorpusPasses(TestCase):
	"""The limits describe what is already here, so they must not fire on it.

	Skipped when no tables are loaded, which is the case on a bare test
	database; it earns its keep when run against a populated one.
	"""

	def test_every_loaded_table_is_within_the_hard_limits(self):
		import yaml

		from .models import TableData

		data = list(TableData.objects.all()[:200])
		if not data:
			self.skipTest('no tables loaded')
		for td in data:
			tree = yaml.load(td.full_yaml, Loader=yaml.BaseLoader) or {}
			hard = [b for b in limits.check(tree) if b.hard]
			self.assertEqual(hard, [], '%s exceeds a hard limit' % (td.table,))


class ExactValuesHaveNoPrecisionToLimit(SimpleTestCase):
	"""T96 is the case: 12 modular polynomials, one of 54342 digits.

	Those digits are the polynomial's coefficients. Writing fewer would not
	round the value, it would give a different polynomial.
	"""

	def polynomial_table(self, declared_type):
		return {'Data properties': {'type': declared_type, 'complete': 'no'},
		        'Numbers': {'1': 'x^2 + ' + '9' * 60000 + '*y'}}

	def test_a_polynomial_table_is_not_judged_on_digits(self):
		self.assertEqual(
			[b.kind for b in limits.check(self.polynomial_table('Z[]'))], [])

	def test_the_same_content_declared_real_is_flagged(self):
		self.assertEqual(
			[b.kind for b in limits.check(self.polynomial_table('R'))],
			['digits'])

	def test_integers_and_rationals_are_exact_too(self):
		for declared in ('Z', 'Q', 'Z[]', 'Q[]'):
			self.assertTrue(limits.stores_exact_values(
				{'Data properties': {'type': declared}}), declared)

	def test_p_adics_are_not_exact_since_they_carry_a_precision(self):
		self.assertFalse(limits.stores_exact_values(
			{'Data properties': {'type': 'Qp'}}))

	def test_an_undeclared_type_is_treated_as_approximate(self):
		"""The cautious way round: it warns, and a warning is cheap to answer."""
		self.assertFalse(limits.stores_exact_values({'Numbers': {}}))

	def test_the_block_limit_still_applies_to_exact_tables(self):
		"""What stops an exact table being unboundedly large."""
		tree = {'Data properties': {'type': 'Z[]'},
		        'Numbers': {str(i): '9' * 400 for i in range(1000)}}
		self.assertEqual([b.kind for b in limits.check(tree)], ['bytes'])


class TheUserFacingRulesOfThumb(SimpleTestCase):
	"""The sizes people actually reach for must not need an excuse.

	1024 entries is what a table parametrised in powers of two comes to, and
	128 digits is a natural precision to stop at. Both are over the recommended
	figures and under the enforced ones, which is exactly the gap the two
	levels exist to create.
	"""

	def test_1024_entries_needs_no_explanation(self):
		self.assertEqual(limits.check({'Numbers': _entries(1024)}), [])

	def test_128_digits_needs_no_explanation(self):
		tree = {'Numbers': {str(i): '0.' + '1' * 128 for i in range(500)}}
		self.assertEqual(limits.check(tree), [])


class EitherNameForTheEntriesSection(SimpleTestCase):
	"""Ten tables still call it `Data`. Looking only for `Numbers` scores
	them empty, so they would pass every limit without being checked."""

	def test_data_is_measured_like_numbers(self):
		for name in ('Numbers', 'Data'):
			tree = {name: _entries(limits.SOFT_ENTRY_COUNT + 1)}
			self.assertEqual([b.kind for b in limits.check(tree)], ['entries'],
			                 name)


class TheBlockLimitFollowsTheSerialisation(SimpleTestCase):
	"""Records cost about 27% more than nesting for identical content.

	A limit measured in bytes of a particular encoding has to move when the
	encoding changes, or converting a table -- which alters not one value --
	makes it look as though the table grew.
	"""

	def test_the_largest_real_table_fits_in_either_form(self):
		#T69 flattened measures 271 KB; the limit must clear it.
		self.assertGreater(limits.SOFT_BLOCK_BYTES, 271 * 1024)

	def test_the_limit_still_refuses_many_entries_at_high_precision(self):
		"""What the block limit is actually for."""
		tree = {'Numbers': _entries(1100, digits=400)}
		self.assertEqual([b.kind for b in limits.check(tree)], ['bytes'])


class CompletenessMayBeQualified(SimpleTestCase):
	"""Two tables answer with a condition attached, and the condition matters.

	`yes, assuming GRH` is a statement about the mathematics. Read as a whole
	string it matched nothing, so a table asserting conditional completeness
	looked like one asserting nothing and would have been asked to justify its
	size.
	"""

	def tree(self, value):
		return {'Data properties': {'complete': value}, 'Numbers': {}}

	def test_a_plain_yes_still_counts(self):
		self.assertTrue(limits.claims_completeness(self.tree('yes')))

	def test_a_qualified_yes_counts(self):
		self.assertTrue(limits.claims_completeness(
			self.tree('yes, assuming GRH')))

	def test_a_qualified_unknown_does_not(self):
		self.assertFalse(limits.claims_completeness(
			self.tree('unknown (presumably not)')))

	def test_no_still_does_not(self):
		self.assertFalse(limits.claims_completeness(self.tree('no')))

	def test_the_condition_is_kept_and_can_be_read(self):
		self.assertEqual(
			limits.completeness_qualifier(self.tree('yes, assuming GRH')),
			'assuming GRH')

	def test_an_unqualified_answer_has_no_condition(self):
		self.assertEqual(limits.completeness_qualifier(self.tree('yes')), '')
