"""Tests for utils/numbers/storage.py.

Two parts. The unit tests run anywhere. The corpus test needs numberdb-data
checked out beside this repository and is skipped without it -- it reads every
stored number and asserts the properties the schema will depend on, which is
worth doing at full scale rather than on a handful of samples.

    python3 -m unittest discover -s tests -v
"""

import math
import os
import re
import sys
import unittest
from fractions import Fraction

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.numbers import (  # noqa: E402
    KIND_COMPLEX,
    KIND_P_ADIC,
    KIND_POLYNOMIAL,
    KIND_REAL,
    ParseError,
    canonical_text,
    parse_any,
)
from utils.numbers import storage  # noqa: E402


def _data_directory():
    for candidate in (os.environ.get('NUMBERDB_DATA'),
                      os.path.expanduser('~/Melodi/numberdb-data/data'),
                      os.path.join(os.path.dirname(os.path.dirname(
                          os.path.dirname(os.path.abspath(__file__)))),
                          'numberdb-data', 'data')):
        if candidate and os.path.isdir(candidate):
            return candidate
    return None


DATA = _data_directory()


class KindDispatch(unittest.TestCase):
    """Order matters, because the grammars overlap."""

    def test_obvious_kinds(self):
        for text, kind in [('42', KIND_REAL), ('3.14', KIND_REAL),
                           ('5/6', KIND_REAL), ('1.89115(13)', KIND_REAL),
                           ('3 + O(2^5)', KIND_P_ADIC),
                           ('Q2:1010', KIND_P_ADIC),
                           ('x^2+1', KIND_POLYNOMIAL),
                           ('2*a*x', KIND_POLYNOMIAL)]:
            with self.subTest(text=text):
                self.assertEqual(parse_any(text).kind, kind)

    def test_a_bare_integer_is_a_number_not_a_constant_polynomial(self):
        #"1" parses as both; it should be stored as a number.
        self.assertEqual(parse_any('1').kind, KIND_REAL)

    def test_the_imaginary_unit_is_not_a_variable(self):
        #Without complex before polynomial, "i" and "1*I" would parse as
        #polynomials in a variable named i.
        for text in ['i', '1*I', '-i', '3.14-2.71*I']:
            with self.subTest(text=text):
                self.assertEqual(parse_any(text).kind, KIND_COMPLEX)

    def test_polynomials_in_a_variable_named_i_still_work(self):
        #"i^2" ends in a digit, so it is not read as an imaginary term.
        self.assertEqual(parse_any('i^2').kind, KIND_POLYNOMIAL)

    def test_unparseable_text_is_refused_not_guessed(self):
        for text in ['', 'Elkies 2006', '(n: 1/n for n in NN)', 'yes']:
            with self.subTest(text=text):
                with self.assertRaises(ParseError):
                    parse_any(text)


class SearchBounds(unittest.TestCase):

    def test_ordered_kinds_have_bounds(self):
        self.assertEqual(len(parse_any('3.14').search_bounds()), 2)
        self.assertEqual(len(parse_any('1+2*I').search_bounds()), 4)

    def test_unordered_kinds_have_none(self):
        #p-adics and polynomials are not ordered, so an interval would be
        #meaningless; they are indexed by other means.
        self.assertIsNone(parse_any('3 + O(2^5)').search_bounds())
        self.assertIsNone(parse_any('x^2+1').search_bounds())


class Canonicalisation(unittest.TestCase):

    def test_idempotent(self):
        for text in ['3.14', '5/6', '1p31415', '[2, 2.3728596]', '1*I',
                     '2^0+2^1+O(2^5)', 'x^2+1']:
            with self.subTest(text=text):
                once = canonical_text(text)
                self.assertEqual(canonical_text(once), once)

    def test_equal_values_share_a_canonical_text(self):
        self.assertEqual(canonical_text('1p31415'), canonical_text('3.1415'))
        self.assertEqual(canonical_text('2^0+2^1+O(2^5)'),
                         canonical_text('3 + O(2^5)'))

    def test_round_trip_through_storage(self):
        for text in ['3.14', '5/6', '1*I', '3 + O(2^5)', 'x^2+1']:
            with self.subTest(text=text):
                stored = parse_any(text)
                reloaded = storage.load(stored.kind, stored.text)
                self.assertEqual(reloaded, stored.value)
                self.assertEqual(storage.kind_of(reloaded), stored.kind)


@unittest.skipUnless(DATA, 'numberdb-data not found')
class TheWholeCorpus(unittest.TestCase):
    """Every stored number, checked for the properties the schema relies on.

    Worth doing at full scale: running the parsers over the corpus is what
    turned up the undocumented uncertainty notation, the bare "-i", and the
    fact that polynomial tables use a "Data:" section.
    """

    @classmethod
    def setUpClass(cls):
        import yaml
        cls.entries = []
        for root, _, files in os.walk(DATA):
            for name in files:
                if not name.endswith('.yaml') or name in ('id.yaml', 'next_ids.yaml'):
                    continue
                path = os.path.join(root, name)
                try:
                    with open(path, errors='ignore') as handle:
                        document = yaml.load(handle, Loader=yaml.BaseLoader)
                except Exception:
                    continue
                if document is None:
                    continue
                if name in ('numbers.yaml', 'polynomials.yaml'):
                    section = document
                elif isinstance(document, dict):
                    section = document.get('Numbers', document.get('Data'))
                else:
                    continue
                if section is None:
                    continue
                cls.entries.extend(cls._values(section))

    @staticmethod
    def _values(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in ('equals', 'param-latex', 'comment', 'reference'):
                    continue
                yield from TheWholeCorpus._values(value)
        elif isinstance(node, list):
            for value in node:
                yield from TheWholeCorpus._values(value)
        elif isinstance(node, (str, int, float)):
            text = str(node).strip()
            if text and not text.startswith(('INPUT{', 'HREF{', 'CITE{', 'http')):
                yield text

    def test_corpus_is_not_empty(self):
        self.assertGreater(len(self.entries), 50000)

    #Entries that are genuinely not numbers, and so are expected to be
    #refused. Asserting their *nature* rather than a count: a bare tally would
    #have to be retuned whenever the corpus grows, and would not notice a real
    #number starting to fail while a prose entry started to parse.
    NOT_NUMBERS = re.compile(r"""^(
          yes | no                       # completeness flags
        | Elkies\ \d+                    # an attribution in a numbers section
        | \(n:\ .*\ for\ n\ in\ NN\)      # hyperreals, which have no storage type
    )$""", re.VERBOSE)

    def test_canonicalisation_is_idempotent_everywhere(self):
        #Dedup depends on this: if two spellings canonicalise differently, or
        #canonicalising twice moves, equal values stop comparing equal.
        checked = 0
        refused = []
        for text in self.entries:
            try:
                once = canonical_text(text)
            except ParseError:
                refused.append(text)
                continue
            self.assertEqual(canonical_text(once), once,
                             'canonicalisation moved on %r' % (text,))
            checked += 1
        self.assertGreater(checked, 50000)

        unexpected = [t for t in refused if not self.NOT_NUMBERS.match(t)]
        self.assertEqual(unexpected, [],
                         'entries that look like numbers were refused')

    def test_search_bounds_contain_exact_bounds_everywhere(self):
        for text in self.entries:
            try:
                stored = parse_any(text)
            except ParseError:
                continue
            if stored.kind == KIND_REAL:
                low, high = stored.value.bounds()
                float_low, float_high = stored.search_bounds()
                self._assert_below(float_low, low, text)
                self._assert_above(float_high, high, text)
            elif stored.kind == KIND_COMPLEX:
                (re_low, re_high), (im_low, im_high) = stored.value.bounds()
                box = stored.search_bounds()
                self._assert_below(box[0], re_low, text)
                self._assert_above(box[1], re_high, text)
                self._assert_below(box[2], im_low, text)
                self._assert_above(box[3], im_high, text)

    def _assert_below(self, bound, exact, text):
        #Infinity is a valid, if useless, outward bound: values beyond the
        #float range saturate, which the corpus does contain.
        if math.isinf(bound):
            self.assertLess(bound, 0, 'lower bound saturated upward on %r' % (text,))
            return
        self.assertLessEqual(Fraction(bound), exact,
                             'lower bound moved inward on %r' % (text,))

    def _assert_above(self, bound, exact, text):
        if math.isinf(bound):
            self.assertGreater(bound, 0, 'upper bound saturated downward on %r' % (text,))
            return
        self.assertGreaterEqual(Fraction(bound), exact,
                                'upper bound moved inward on %r' % (text,))

    def test_every_value_reloads_from_its_stored_form(self):
        for text in self.entries:
            try:
                stored = parse_any(text)
            except ParseError:
                continue
            reloaded = storage.load(stored.kind, stored.text)
            self.assertEqual(reloaded, stored.value,
                             'reload changed the value of %r' % (text,))


if __name__ == '__main__':
    unittest.main()
