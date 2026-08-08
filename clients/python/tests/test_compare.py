"""Tests for deciding whether two written values disagree.

This is what stands between "the code no longer produces the table" and "the
table was built at twenty digits and is being checked at a hundred". Getting it
wrong in one direction reports a sound table as broken and offers to rewrite
it; getting it wrong in the other lets a generator quietly overwrite a table
with different numbers.
"""

import sys

import pytest

sys.path.insert(0, '.')

from numberdb._compare import (AGREES, COARSENS, CONTRADICTS, REFINES, SAME,
                               UNREADABLE, compare, digits_of)


class TestPrecisionIsNotDisagreement:
    """The bug this module exists to fix: `stored == recomputed` on text."""

    def test_more_digits_of_the_same_number_refines_it(self):
        assert compare('3.14159', '3.141592653589793') == REFINES

    def test_fewer_digits_of_the_same_number_coarsens_it(self):
        assert compare('3.141592653589793', '3.14159') == COARSENS

    def test_identical_text_is_the_same(self):
        assert compare('3.14159', '3.14159') == SAME

    def test_a_different_number_contradicts(self):
        assert compare('3670.48296788', '3670.48296700') == CONTRADICTS


class TestTheFormsTheCorpusActuallyUses:
    """All four appear in the database, and a generator may produce any."""

    def test_a_bracketed_uncertainty_is_read(self):
        #3670.48296788(13): the 13 is uncertainty in the last digits written.
        assert compare('3670.48296788(13)', '3670.482967881') == REFINES

    def test_a_bracketed_uncertainty_still_catches_a_real_difference(self):
        assert compare('3670.48296788(13)', '3670.48296700') == CONTRADICTS

    def test_a_ball_is_read(self):
        assert compare('14.134725141734693 +/- 1e-15',
                       '14.1347251417346937904572519835625') == REFINES

    def test_a_ball_that_excludes_the_value_contradicts(self):
        #Not 14.2: written to three digits that claims +/- 0.1, which does
        #cover 14.1347251. A value has to fall outside what was claimed.
        assert compare('14.1347251 +/- 1e-9', '15.9') == CONTRADICTS

    def test_sages_question_mark_is_read(self):
        assert compare('3.14159?', '3.1415926?') == REFINES

    def test_a_plain_decimal_is_precise_to_what_is_written(self):
        assert compare('0.88153', '0.881534567') == REFINES


class TestExactValues:
    """A rational has no precision to differ in."""

    def test_the_same_rational_is_the_same(self):
        assert compare('1/6', '1/6') == SAME

    def test_a_different_rational_contradicts(self):
        assert compare('1/3', '1/4') == CONTRADICTS

    def test_an_unreduced_form_is_the_same_number(self):
        assert compare('1/2', '2/4') == SAME

    def test_replacing_an_exact_value_with_decimals_loses_precision(self):
        """Even when the decimals are consistent with it. `1/3` states every
        digit there is; `0.3334` states four."""
        assert compare('1/3', '0.3334') == COARSENS

    def test_a_decimal_that_excludes_the_rational_contradicts(self):
        assert compare('1/3', '0.5000') == CONTRADICTS


class TestComplexValues:
    """Written `a + i * b`, so a reader knows which part they are reading
    before wading through a hundred digits of it."""

    def test_both_parts_must_agree(self):
        assert compare('1 + i * 2.0000', '1.000 + i * 2.00000001') == REFINES

    def test_a_contradiction_in_either_part_contradicts(self):
        assert compare('1 + i * 2.0000', '1.000 + i * 2.5') == CONTRADICTS

    def test_a_part_written_exactly_and_then_as_decimals_loses_nothing(self):
        """`0` and `0.0000` are the same number, and parts written as 0 or 1
        are everywhere in a table of complex values."""
        assert compare('1 + i * 2.5', '1.000 + i * 2.5') == AGREES

    def test_precision_is_that_of_the_weaker_part(self):
        assert digits_of('1.23456789 + i * 2.00') == 3


class TestPAdicValues:
    """They carry their own precision in an O-term."""

    def test_a_longer_expansion_refines(self):
        assert compare('1 + 2*3 + O(3^20)', '1 + 2*3 + O(3^40)') == REFINES

    def test_a_shorter_one_coarsens(self):
        assert compare('1 + 2*3 + O(3^40)', '1 + 2*3 + O(3^20)') == COARSENS

    def test_a_differing_term_contradicts(self):
        assert compare('1 + 2*3 + O(3^20)', '1 + 1*3 + O(3^40)') == CONTRADICTS


class TestWhatItWillNotGuessAbout:
    """Calling two things it cannot read a contradiction would stop runs over
    a spelling."""

    def test_two_unreadable_values_are_unreadable(self):
        assert compare('x^2 + 1', 'y^3 - 7') == UNREADABLE

    def test_a_truncation_is_still_recognisable(self):
        assert compare('x^2 + 1', 'x^2 + 1 + 3*x^7') == REFINES


class TestDigitsOf:

    @pytest.mark.parametrize('text,expected', [
        ('3.14159', 6),
        ('0.00123', 3),            # leading zeros place, they do not inform
        ('3670.48296788(13)', 11),
        ('14.13 +/- 1e-9', 11),    # a ball claims what its radius allows
        ('3.14159?', 6),
    ])
    def test_it_counts_what_is_claimed(self, text, expected):
        assert digits_of(text) == expected

    def test_an_exact_value_states_every_digit_there_is(self):
        assert digits_of('1/3') > 1000
