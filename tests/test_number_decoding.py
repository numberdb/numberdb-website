"""Golden test: plain-Python decoding must match Sage exactly.

Runs on a plain interpreter -- no Sage, no Django, no database:

    python3 -m unittest discover -s tests -v

``tests/golden/number_decoding.json`` was captured from real production rows
using the Sage implementation (see ``generate_golden.py``). It is the contract
for phase A of moving the web container off Sage: the replacement is correct
exactly when it reproduces these strings byte-for-byte.

The suite is deliberately arranged so that *not yet implemented* and *silently
wrong* cannot be confused:

* Types listed in ``SUPPORTED_TYPES`` must match every golden value exactly.
* Types not listed must raise ``UnsupportedType`` -- so a half-finished
  renderer cannot quietly return something plausible.
* A coverage test reports how much of the fixture is covered, so progress is
  visible rather than asserted.
"""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.number_decode import (  # noqa: E402
    SUPPORTED_TYPES,
    UnsupportedType,
    decode_integer,
    decode_rational,
    decode_to_text,
)

GOLDEN_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           'golden', 'number_decoding.json')


def load_golden():
    with open(GOLDEN_PATH) as handle:
        return json.load(handle)


GOLDEN = load_golden()
NUMBER_CASES = [c for c in GOLDEN['cases'] if c['model'] == 'Number']


def _type_bytes(case):
    return bytes.fromhex(case['number_type'])


class FixtureSanity(unittest.TestCase):

    def test_fixture_is_populated(self):
        self.assertGreater(len(NUMBER_CASES), 0)
        self.assertIn('sage', GOLDEN['generated_with'])

    def test_fixture_covers_every_stored_type(self):
        seen = {_type_bytes(c) for c in NUMBER_CASES}
        self.assertEqual(seen, {b'z', b'q', b'r', b'b'},
                         'fixture no longer covers all four stored types')

    def test_expected_values_were_captured_successfully(self):
        # If Sage itself failed to render a row, that is worth knowing before
        # treating the row as a contract.
        broken = [c for c in NUMBER_CASES if not c['str'].get('ok')]
        self.assertEqual(broken, [], 'fixture contains rows Sage could not render')


class SupportedTypesMatchSageExactly(unittest.TestCase):

    def test_all_supported_cases_match(self):
        checked = 0
        for case in NUMBER_CASES:
            stored_type = _type_bytes(case)
            if stored_type not in SUPPORTED_TYPES:
                continue
            expected = case['str']['value']
            actual = decode_to_text(stored_type, bytes.fromhex(case['number_blob']))
            self.assertEqual(
                actual, expected,
                'type %r blob %s: plain Python produced %r, Sage produced %r'
                % (stored_type, case['number_blob'], actual, expected))
            checked += 1
        self.assertGreater(checked, 0, 'no supported cases were exercised')

    def test_integers_round_trip_through_the_stored_encoding(self):
        for case in NUMBER_CASES:
            if _type_bytes(case) != b'z':
                continue
            blob = bytes.fromhex(case['number_blob'])
            value = decode_integer(blob)
            self.assertEqual(
                value.to_bytes(len(blob), byteorder='big', signed=True), blob,
                're-encoding %d did not reproduce the stored bytes' % (value,))

    def test_rational_denominator_is_read_unsigned(self):
        # Numerator signed, denominator unsigned. Reading the denominator as
        # signed corrupts any fraction whose top bit is set, so assert the
        # decoder never yields a negative denominator.
        for case in NUMBER_CASES:
            if _type_bytes(case) != b'q':
                continue
            value = decode_rational(bytes.fromhex(case['number_blob']))
            self.assertGreater(value.denominator, 0)


class UnsupportedTypesFailLoudly(unittest.TestCase):

    def test_interval_types_raise_rather_than_guess(self):
        interval_cases = [c for c in NUMBER_CASES
                          if _type_bytes(c) not in SUPPORTED_TYPES]
        self.assertGreater(len(interval_cases), 0)
        for case in interval_cases[:20]:
            with self.assertRaises(UnsupportedType):
                decode_to_text(_type_bytes(case),
                               bytes.fromhex(case['number_blob']))


class MigrationCoverage(unittest.TestCase):
    """Visible scoreboard for the migration rather than a hidden percentage."""

    def test_report_coverage(self):
        total = len(NUMBER_CASES)
        covered = sum(1 for c in NUMBER_CASES
                      if _type_bytes(c) in SUPPORTED_TYPES)
        by_type = {}
        for case in NUMBER_CASES:
            stored = _type_bytes(case).decode('latin-1')
            by_type.setdefault(stored, [0, 0])
            by_type[stored][0] += 1
            if _type_bytes(case) in SUPPORTED_TYPES:
                by_type[stored][1] += 1

        report = ', '.join('%s %d/%d' % (t, done, n)
                           for t, (n, done) in sorted(by_type.items()))
        print('\n  Number decoding without Sage: %d/%d cases (%s)'
              % (covered, total, report))
        self.assertGreater(covered, 0)


if __name__ == '__main__':
    unittest.main()
