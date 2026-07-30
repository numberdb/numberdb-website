"""Tests for workers/expression_validator.py.

Pure AST work -- no Sage, no Django, no database. Run with:

    python3 -m unittest discover -s tests -v

The inputs below are written as Sage's preparser emits them (``2^n`` arrives as
``Integer(2)**n``, ``[1..10]`` as ``ellipsis_range(...)``), because that is what
the validator actually sees.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from workers.expression_validator import (  # noqa: E402
    ExpressionRejected,
    validate_expression,
)


# Stand-in for the real evaluation namespace. Values are irrelevant here; only
# the keys matter, since the allow-list is derived from them.
NAMESPACE = {name: None for name in (
    'pi', 'e', 'I', 'infinity',
    'ZZ', 'QQ', 'RR', 'CC', 'RIF', 'CIF', 'RBF', 'CBF',
    'sqrt', 'exp', 'log', 'sin', 'cos', 'gcd', 'lcm',
    'factorial', 'binomial', 'bernoulli', 'zeta',
    'abs', 'len', 'min', 'max', 'sum', 'range',
)}


def accepts(source):
    validate_expression(source, NAMESPACE)


class AcceptsLegitimateInput(unittest.TestCase):
    """The four examples from the advanced-search tips, as preparsed."""

    def test_tuple_of_constants(self):
        accepts('-Integer(2), pi, e')

    def test_dict_comprehension_with_ellipsis_range(self):
        accepts('{n: Integer(2)**n for n in '
                '(ellipsis_range(Integer(1),Ellipsis,Integer(10)))}')

    def test_interval_constructor(self):
        accepts('RIF(Integer(10),Integer(11))')

    def test_nested_comprehension_with_condition(self):
        accepts(
            '{a: {b: a/b for b in (ellipsis_range(Integer(1),Ellipsis,Integer(5))) '
            'if gcd(a,b) == Integer(1)} '
            'for a in (ellipsis_range(-Integer(5),Ellipsis,Integer(5)))}'
        )

    def test_assorted_ordinary_expressions(self):
        for source in [
            'sqrt(Integer(2))',
            'sum([factorial(n) for n in range(Integer(10))])',
            '[binomial(n,k) for n in range(Integer(5)) for k in range(n)]',
            'pi + e * Integer(2)',
            'RBF(Integer(1)) if Integer(1) < Integer(2) else CBF(Integer(0))',
            '{zeta(Integer(2)), zeta(Integer(4))}',
        ]:
            with self.subTest(source=source):
                accepts(source)


class RejectsEscapeAttempts(unittest.TestCase):

    def assertRejected(self, source):
        with self.assertRaises(ExpressionRejected):
            validate_expression(source, NAMESPACE)

    def test_attribute_access_is_refused(self):
        # The classic traversal chain, and the family it belongs to.
        self.assertRejected('().__class__')
        self.assertRejected('().__class__.__bases__[0].__subclasses__()')
        self.assertRejected('pi.numerical_approx()')

    def test_dunder_names_are_refused(self):
        self.assertRejected('__import__')
        self.assertRejected('__builtins__')

    def test_the_regression_that_motivated_this_module(self):
        # The old deny-list concatenated 'compile' and 'delattr' into one
        # string via a missing comma, so neither was blocked. An allow-list
        # cannot fail this way, and this test says so out loud.
        self.assertRejected('compile("1","<s>","eval")')
        self.assertRejected('delattr(pi, "x")')

    def test_other_previously_denied_builtins_stay_out(self):
        for source in ['eval("1")', 'exec("1")', 'open("/etc/passwd")',
                       'getattr(pi, "x")', 'globals()', 'vars()', 'dir()',
                       'input()', 'breakpoint()']:
            with self.subTest(source=source):
                self.assertRejected(source)

    def test_unknown_names_are_refused(self):
        self.assertRejected('os')
        self.assertRejected('some_function_we_never_defined(Integer(1))')

    def test_indirect_and_method_calls_are_refused(self):
        self.assertRejected('sqrt(Integer(2))(Integer(3))')
        self.assertRejected('(sqrt)(Integer(2))(Integer(3))')

    def test_lambda_and_walrus_are_refused(self):
        self.assertRejected('lambda: Integer(1)')
        self.assertRejected('(x := Integer(1))')

    def test_fstrings_are_refused(self):
        # JoinedStr reaches __format__ on arbitrary objects.
        self.assertRejected('f"{pi}"')

    def test_argument_unpacking_is_refused(self):
        self.assertRejected('gcd(*[Integer(1),Integer(2)])')
        self.assertRejected('RIF(**{})')

    def test_statements_are_refused(self):
        for source in ['import os', 'x = Integer(1)', 'del pi',
                       'assert Integer(1)']:
            with self.subTest(source=source):
                self.assertRejected(source)

    def test_subscript_is_refused_for_now(self):
        self.assertRejected('[Integer(1),Integer(2)][Integer(0)]')


class ResourceLimits(unittest.TestCase):

    def test_oversized_source_refused(self):
        with self.assertRaises(ExpressionRejected):
            validate_expression('pi+' * 5000 + 'pi', NAMESPACE)

    def test_too_many_nodes_refused(self):
        with self.assertRaises(ExpressionRejected):
            validate_expression('+'.join(['pi'] * 3000), NAMESPACE,
                                max_length=100000)

    def test_too_deep_refused(self):
        # Note redundant parentheses would NOT work here: `((pi))` parses to a
        # bare Name, so it adds no depth. Nested calls genuinely nest.
        with self.assertRaises(ExpressionRejected):
            validate_expression('sqrt(' * 30 + 'pi' + ')' * 30, NAMESPACE)

    def test_moderately_nested_is_still_accepted(self):
        validate_expression('sqrt(' * 5 + 'pi' + ')' * 5, NAMESPACE)

    def test_null_byte_refused(self):
        with self.assertRaises(ExpressionRejected):
            validate_expression('pi\x00', NAMESPACE)

    def test_syntax_error_is_reported_not_raised(self):
        with self.assertRaises(ExpressionRejected):
            validate_expression('pi +', NAMESPACE)


class ComprehensionScoping(unittest.TestCase):
    """Loop variables must be usable inside, and must not leak outside."""

    def test_loop_variable_usable_in_body_and_condition(self):
        accepts('[n for n in range(Integer(5))]')
        accepts('[n for n in range(Integer(5)) if n > Integer(1)]')

    def test_tuple_targets_bind_all_names(self):
        accepts('[a+b for a,b in range(Integer(5))]')

    def test_later_generators_see_earlier_variables(self):
        accepts('[a+b for a in range(Integer(3)) for b in range(a)]')

    def test_loop_variable_does_not_leak_out(self):
        with self.assertRaises(ExpressionRejected):
            validate_expression('[n for n in range(Integer(5))] + n', NAMESPACE)

    def test_first_iterable_evaluated_in_enclosing_scope(self):
        # `b` is not yet bound where the first iterable is evaluated.
        with self.assertRaises(ExpressionRejected):
            validate_expression('[a for a in range(b) for b in range(Integer(3))]',
                                NAMESPACE)


class NamespaceDrivesAllowList(unittest.TestCase):
    """The namespace is the single source of truth for permitted names."""

    def test_name_absent_from_namespace_is_refused(self):
        with self.assertRaises(ExpressionRejected):
            validate_expression('cosh(Integer(1))', NAMESPACE)

    def test_adding_to_namespace_permits_it(self):
        extended = dict(NAMESPACE, cosh=None)
        validate_expression('cosh(Integer(1))', extended)


if __name__ == '__main__':
    unittest.main()
