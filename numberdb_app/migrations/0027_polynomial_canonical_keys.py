"""Rewrite the polynomial search key with the one canonicalisation.

The key was built by Sage's ``polynomial_modulo_variable_names``. It worked,
but only Sage could reproduce it, and a client needs to: the longest stored
polynomial is 58866 characters, nginx rejects a URL past 8k, so a lookup has
to send a hash of the key rather than the polynomial, and both sides must
produce the same bytes.

Safe because the two group identically. Measured across the whole corpus
before writing this: 1038 polynomials, none unparsed by the plain Python
parser, 1035 distinct keys under each scheme, and the equivalence classes are
the same set. So this changes how the key is spelled, not which polynomials
find each other. ``manage.py check_polynomial_keys`` re-checks that against the
real database, which the unit test cannot -- it skips, the test database being
empty.

Also stores a 128-bit digest of the key. The 64-bit column stays for the
server's own lookups, which filter on the full key as well; a client sending
only a hash has nothing to cross-check against, so its hash has to be wide
enough that a collision is infeasible to construct rather than merely unlikely.
"""

import hashlib

from django.db import migrations

BATCH = 500


def _keys(exact_text):
    from utils.numbers.polynomial import parse_polynomial
    key = parse_polynomial(exact_text).canonical_text()
    short = hashlib.blake2s(key.encode('cp437', 'replace'), digest_size=8)
    return (key,
            int.from_bytes(short.digest(), byteorder='big', signed=True),
            hashlib.blake2s(key.encode('utf8'), digest_size=16).hexdigest())


def rewrite(apps, schema_editor):
    Polynomial = apps.get_model('db', 'Polynomial')
    pending, failed = [], 0
    for row in Polynomial.objects.all().only(
            'id', 'exact_text').iterator(chunk_size=BATCH):
        try:
            row.number_string, row.number_string_hash, row.canonical_hash = \
                _keys(row.exact_text)
        except Exception:
            #Left as it was rather than guessed at: a polynomial the parser
            #cannot read keeps its old key and stays findable by the old route
            #until someone looks at it.
            failed += 1
            continue
        pending.append(row)
        if len(pending) >= BATCH:
            Polynomial.objects.bulk_update(
                pending, ['number_string', 'number_string_hash',
                          'canonical_hash'])
            pending = []
    if pending:
        Polynomial.objects.bulk_update(
            pending, ['number_string', 'number_string_hash', 'canonical_hash'])
    if failed:
        print('  %d polynomials could not be re-keyed and keep the old key'
              % (failed,))


def clear(apps, schema_editor):
    #The old key cannot be rebuilt without Sage, so this only drops the new
    #digest. Restoring the previous spelling means rebuilding from the data
    #repository.
    Polynomial = apps.get_model('db', 'Polynomial')
    Polynomial.objects.update(canonical_hash='')


class Migration(migrations.Migration):

    dependencies = [
        ('db', '0026_polynomial_canonical_hash'),
    ]

    operations = [
        migrations.RunPython(rewrite, clear),
    ]
