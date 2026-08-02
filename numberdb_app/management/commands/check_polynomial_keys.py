"""Check the polynomial search key against the real database.

The equivalent unit test skips when the test database is empty, which it
always is, so it guards nothing. This runs against the data that matters:

    manage.py check_polynomial_keys

Two things are checked. That every stored polynomial can be read by the plain
Python parser -- a client will use it, and one it cannot read is a number
nobody can look up. And that the key groups polynomials exactly as the stored
one does, since a key that grouped differently would silently change which
polynomials find each other.
"""

from collections import defaultdict

from django.core.management.base import BaseCommand

from numberdb_app.models import Polynomial


class Command(BaseCommand):
    help = 'Verify the polynomial canonical key against the stored data.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--against', default='',
            help='A column holding a previous key, to compare groupings with.')

    def handle(self, *args, **options):
        from utils.numbers.polynomial import parse_polynomial

        previous = options['against']
        by_previous, by_current = defaultdict(set), defaultdict(set)
        unparsed, mismatched = [], []

        for row in Polynomial.objects.all().iterator(chunk_size=300):
            try:
                polynomial = parse_polynomial(row.exact_text)
                key = polynomial.canonical_text()
            except Exception as error:
                unparsed.append((row.pk, type(error).__name__, str(error)[:60]))
                continue
            if row.number_string and row.number_string != key:
                mismatched.append((row.pk, row.number_string[:40], key[:40]))
            by_current[key].add(row.pk)
            if previous:
                by_previous[getattr(row, previous)].add(row.pk)

        total = Polynomial.objects.count()
        self.stdout.write('polynomials:        %d' % (total,))
        self.stdout.write('unparsed:           %d' % (len(unparsed),))
        self.stdout.write('distinct keys:      %d' % (len(by_current),))
        self.stdout.write('stored key differs: %d' % (len(mismatched),))

        for pk, kind, detail in unparsed[:5]:
            self.stdout.write('  unparsed %s: %s %s' % (pk, kind, detail))
        for pk, was, now in mismatched[:5]:
            self.stdout.write('  %s stored %r now %r' % (pk, was, now))

        if previous:
            same = ({frozenset(v) for v in by_previous.values()}
                    == {frozenset(v) for v in by_current.values()})
            self.stdout.write('same grouping as %s: %s' % (previous, same))
            if not same:
                raise SystemExit(1)

        if unparsed:
            raise SystemExit(1)
