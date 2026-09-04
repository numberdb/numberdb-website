import sys
sys.path.insert(0, '/app')
from utils.numbers import ParseError as ExactParseError
from utils.numbers import canonical_text as exact_canonical_text
cases = ['2 + i * -1',
         '3/2 + i * -0.866025403784438646763723170752936',
         '5/65 + i * 5.55555',
         '1/13',
         '1.500000000000000000000000000000 + i * -0.86602540378443864676']
for s in cases:
    try:
        out = exact_canonical_text(s)
        print('%-46s -> %r' % (s[:46], out[:50] if out else out))
    except ExactParseError as e:
        print('%-46s -> ExactParseError (%s)' % (s[:46], str(e)[:40]))
    except Exception as e:
        print('%-46s -> %s: %s' % (s[:46], type(e).__name__, str(e)[:40]))
