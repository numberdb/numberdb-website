"""Differential entropies of continuous probability distributions -- numberdb.org/T241

For a real random variable X with density f, this stores

    h(X) = - integral f(x) log(f(x)) dx,

in nats and in bits, for named continuous distributions in their standard
forms.

Run it with SageMath:

    $ sage -pip install numberdb          # once
    $ sage -python generate.py            # check the table against this code
    $ sage -python generate.py --publish  # send it, with NUMBERDB_API_KEY set

Values are computed from closed forms in real and complex ball arithmetic.
The standard forms are the SciPy ones: location 0 and scale 1 unless the
distribution's usual shape parameters say otherwise.
"""

import os
import sys

import numberdb.sage as numberdb
from sage.rings.complex_arb import ComplexBallField
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.real_arb import RealBallField


# Bits of working precision beyond what the written digits need.
#
# Measured by dry_run.py over all 626 entries: the widest returned ball still
# carries more than the 100 decimal digits the table asks for.
WORKING_GUARD = 128

NO_SHAPE_DISTRIBUTIONS = (
    'normal',
    'cauchy',
    'laplace',
    'gumbel',
    'rayleigh',
    'maxwell',
    'half-normal',
    'arcsine',
    'semicircle',
    'levy',
    'triangular',
    'hypsecant-scipy',
    'hypsecant-unit-variance',
)

WEIBULL_SHAPES = (QQ(1) / 2, QQ(3) / 2, QQ(2), QQ(3), QQ(4), QQ(5))


def _key_from_stdin():
    if os.environ.get('NUMBERDB_KEY_FROM_STDIN') != '1':
        return
    token = sys.stdin.read().strip()
    if '=' in token and token.split('=', 1)[0].isupper():
        token = token.split('=', 1)[1].strip().strip("'\"")
    if token:
        os.environ['NUMBERDB_API_KEY'] = token


def _real_field(digits):
    return RealBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _complex_field(digits):
    return ComplexBallField(numberdb.bits(digits, losing=WORKING_GUARD))


def _q(text):
    return QQ(str(text))


def _log_beta(field, a, b):
    return field(a).log_gamma() + field(b).log_gamma() - field(a + b).log_gamma()


def _psi(field, value):
    return field(value).psi()


def _bessel_i(digits, order, argument):
    field = _complex_field(digits)
    value = field(argument).bessel_I(field(order))
    if not (value.real().is_finite() and value.imag().is_finite()):
        raise ArithmeticError('computed a non-finite Bessel ball')
    if not value.imag().contains_zero():
        raise ArithmeticError('expected I_%s(%s) to be real' % (order, argument))
    return value.real()


def _shape_values():
    for value in range(1, 31):
        yield 'student-t', str(value)
    for value in range(1, 31):
        yield 'chi', str(value)
    for value in range(1, 31):
        yield 'chi-square', str(value)
    for numerator in range(1, 31):
        yield 'gamma', str(QQ(numerator) / QQ(2))
    for value in WEIBULL_SHAPES:
        yield 'weibull', str(value)
    for value in range(2, 11):
        yield 'pareto', str(value)
    for value in range(1, 11):
        yield 'von-mises', str(value)
    beta_parameters = [QQ(numerator) / QQ(2) for numerator in range(1, 11)]
    for i, a in enumerate(beta_parameters):
        for b in beta_parameters[i:]:
            yield 'beta', '%s,%s' % (a, b)
    for n1 in range(1, 11):
        for n2 in range(1, 11):
            yield 'f', '%s,%s' % (n1, n2)


def _entropy_nats(distribution, shape, digits):
    field = _real_field(digits)
    one = field(1)
    two = field(2)
    half = field(QQ(1) / QQ(2))
    log2 = two.log()
    pi = field.pi()
    gamma = field.euler_constant()

    if distribution == 'normal':
        return (one + (two * pi).log()) / 2
    if distribution == 'cauchy':
        return (field(4) * pi).log()
    if distribution == 'laplace':
        return one + log2
    if distribution == 'gumbel':
        return one + gamma
    if distribution == 'rayleigh':
        return one - log2 / 2 + gamma / 2
    if distribution == 'maxwell':
        return gamma + (two * pi).log() / 2 - field(QQ(1) / QQ(2))
    if distribution == 'half-normal':
        return (one + (pi / 2).log()) / 2
    if distribution == 'arcsine':
        return pi.log() - two * log2
    if distribution == 'semicircle':
        return pi.log() - half
    if distribution == 'levy':
        return (one + 3 * gamma + (16 * pi).log()) / 2
    if distribution == 'triangular':
        return half - log2
    if distribution == 'hypsecant-scipy':
        return (2 * pi).log()
    if distribution == 'hypsecant-unit-variance':
        return field(4).log()

    if distribution == 'student-t':
        nu = _q(shape)
        a = nu / 2
        b = QQ(1) / 2
        return (field(nu).log() / 2 + _log_beta(field, a, b)
                + (field(nu) + 1) / 2
                * (_psi(field, (nu + 1) / 2) - _psi(field, nu / 2)))

    if distribution == 'chi':
        k = _q(shape)
        a = k / 2
        if k == 1:
            return (one + (pi / 2).log()) / 2
        return (field(a).log_gamma() + field(k) / 2 - log2 / 2
                - (field(k) - 1) * _psi(field, a) / 2)

    if distribution == 'chi-square':
        k = _q(shape)
        a = k / 2
        return (field(k) / 2 + log2 + field(a).log_gamma()
                + (1 - field(a)) * _psi(field, a))

    if distribution == 'gamma':
        a = _q(shape)
        if a == 1:
            return ZZ(1)
        return field(a) + field(a).log_gamma() + (1 - field(a)) * _psi(field, a)

    if distribution == 'weibull':
        k = _q(shape)
        return gamma * (1 - 1 / field(k)) + one - field(k).log()

    if distribution == 'pareto':
        alpha = _q(shape)
        return one + 1 / field(alpha) - field(alpha).log()

    if distribution == 'von-mises':
        kappa = _q(shape)
        i0 = _bessel_i(digits, 0, kappa)
        i1 = _bessel_i(digits, 1, kappa)
        return (2 * pi * i0).log() - field(kappa) * i1 / i0

    if distribution == 'beta':
        a_text, b_text = shape.split(',')
        a = _q(a_text)
        b = _q(b_text)
        if a == 1 and b == 1:
            return ZZ(0)
        return (_log_beta(field, a, b)
                - (field(a) - 1) * _psi(field, a)
                - (field(b) - 1) * _psi(field, b)
                + (field(a + b) - 2) * _psi(field, a + b))

    if distribution == 'f':
        n1_text, n2_text = shape.split(',')
        n1 = _q(n1_text)
        n2 = _q(n2_text)
        a = n1 / 2
        b = n2 / 2
        return ((field(n2) / field(n1)).log() + _log_beta(field, a, b)
                - (field(a) - 1) * _psi(field, a)
                - (field(b) + 1) * _psi(field, b)
                + field(a + b) * _psi(field, a + b))

    raise ValueError('unknown distribution %r' % (distribution,))


def _to_unit(value, unit, digits):
    if unit == 'nats':
        return value
    if unit != 'bits':
        raise ValueError('unknown unit %r' % (unit,))
    if value == 0:
        return ZZ(0)
    field = _real_field(digits)
    return field(value) / field(2).log()


def _equals(distribution, shape, unit):
    if distribution == 'student-t' and shape == '1':
        return 'HREF{#cauchy,-,%s}' % (unit,)
    if distribution == 'chi':
        if shape == '1':
            return 'HREF{#half-normal,-,%s}' % (unit,)
        if shape == '2':
            return 'HREF{#rayleigh,-,%s}' % (unit,)
        if shape == '3':
            return 'HREF{#maxwell,-,%s}' % (unit,)
    if distribution == 'beta' and shape == '1/2,1/2':
        return 'HREF{#arcsine,-,%s}' % (unit,)
    return ''


def _comment(distribution, shape):
    if distribution == 'gamma' and shape == '1':
        return 'This is the standard exponential distribution.'
    if distribution == 'beta' and shape == '1,1':
        return 'This is the uniform distribution on $[0,1]$.'
    return ''


class DifferentialEntropies(numberdb.Generator):

    table = os.environ.get('NUMBERDB_TABLE', 'T241')
    parameters = ('distribution', 'shape', 'unit')
    type = 'R'
    digits = 100
    rigour = 'proven'

    def enumerate(self):
        for distribution in NO_SHAPE_DISTRIBUTIONS:
            for unit in ('nats', 'bits'):
                yield {'distribution': distribution, 'shape': '-', 'unit': unit}
        for distribution, shape in _shape_values():
            for unit in ('nats', 'bits'):
                yield {'distribution': distribution, 'shape': shape, 'unit': unit}

    def value(self, params, digits):
        distribution = str(params['distribution'])
        shape = str(params['shape'])
        unit = str(params['unit'])
        value = _to_unit(_entropy_nats(distribution, shape, digits), unit, digits)
        equals = _equals(distribution, shape, unit)
        comment = _comment(distribution, shape)
        if equals or comment:
            record = {'number': value}
            if equals:
                record['equals'] = equals
            if comment:
                record['comment'] = comment
            return record
        return value


if __name__ == '__main__':
    _key_from_stdin()
    generator = DifferentialEntropies()
    if os.environ.get('NUMBERDB_PUBLISH') == '1' or '--publish' in sys.argv:
        print(generator.publish(message='differential entropy values'))
    else:
        report = generator.verify(sample=None)
        print(report)
        sys.exit(0 if report.ok else 1)
