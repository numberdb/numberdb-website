"""https://numberdb.org/T246
Generate T246, the values of the logarithmic derivative zeta'(s)/zeta(s) of
the Riemann zeta function at rational arguments.

Run it with SageMath:

    $ sage -pip install numberdb
    $ sage -python generate.py
    $ sage -python generate.py --publish

Under the repository's agent runner, pipe the API key on stdin:

    $ cat "$NUMBERDB_KEY_FILE" | NUMBERDB_KEY_FROM_STDIN=1 \
        agents/sage.sh generators/zeta-logderivative-rational-values/generate.py

Set NUMBERDB_PUBLISH=preview to preview the write, or NUMBERDB_PUBLISH=1 to
send the entries and attach this file.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.rational_field import QQ


WORKING_GUARD = 96


def configure_key_from_stdin():
    if os.environ.get('NUMBERDB_KEY_FROM_STDIN') != '1':
        return
    token = sys.stdin.read().strip()
    if '=' in token and token.split('=', 1)[0].isupper():
        token = token.split('=', 1)[1].strip().strip('\'"')
    if token:
        numberdb.configure(api_key=token)


def rational_arguments(denominator=4, lower=-20, upper=20):
    for b in range(1, denominator + 1):
        for n in range(0, upper * b + 1):
            numerators = [n] if n == 0 else [n, -n]
            for a in numerators:
                s = QQ(a) / QQ(b)
                if s.denominator() != b or s < lower or s > upper or s == 1:
                    continue
                yield s


def is_trivial_zero(s):
    return s.denominator() == 1 and s < 0 and int(s) % 2 == 0


def finite_real(value, label):
    if not value.real().is_finite() or not value.imag().is_finite():
        raise ArithmeticError('computed a non-finite ball for %s' % (label,))
    if not value.imag().contains_zero():
        raise ArithmeticError('expected a real value for %s' % (label,))
    return value.real()


def logderivative_comment(s):
    text = str(s)
    if text == '1/2':
        return '$\\frac12(\\frac\\pi2+\\gamma+\\log(8\\pi))$.'
    if text == '2':
        return (
            '$\\gamma+\\log(2\\pi)-12\\log A$, where $A$ is the '
            'Glaisher-Kinkelin constant.'
        )
    if text == '0':
        return '$\\log(2\\pi)$.'
    return ''


class RiemannZetaLogDerivativeAtRationals(numberdb.Generator):
    table = 'T246'
    parameters = ('s',)
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self):
        for s in rational_arguments():
            if not is_trivial_zero(s):
                yield {'s': str(s)}

    def value(self, params, digits):
        field = ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))
        rational_s = QQ(params['s'])
        s = field(rational_s)
        number = finite_real(
            s.zetaderiv(1) / s.zeta(),
            "zeta'(%s)/zeta(%s)" % (rational_s, rational_s),
        )
        comment = logderivative_comment(rational_s)
        if comment:
            return {'number': number, 'comment': comment}
        return number


def main():
    configure_key_from_stdin()
    generator = RiemannZetaLogDerivativeAtRationals()
    mode = os.environ.get('NUMBERDB_PUBLISH')
    if '--publish' in sys.argv or mode == '1':
        print(generator.publish(message='split T228 logarithmic derivative entries'))
        return
    if '--preview' in sys.argv or mode == 'preview':
        print(generator.preview())
        return
    report = generator.verify(sample=None)
    print(report)
    sys.exit(0 if report.ok else 1)


if __name__ == '__main__':
    main()
