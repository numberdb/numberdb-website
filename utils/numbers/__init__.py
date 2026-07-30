"""Exact number representation for NumberDB.

Plain Python: no Sage, no Django. See docs/design/number-datastructures.md.
Sage conversion lives in a separate adapter, so this layer runs and is tested
on a bare interpreter.
"""

from .real import ExactReal, ParseError, parse_real
from .complex import ExactComplex, parse_complex
from .padic import ExactPAdic, parse_p_adic
from .polynomial import ExactPolynomial, parse_polynomial
from .storage import (KIND_COMPLEX, KIND_P_ADIC, KIND_POLYNOMIAL, KIND_REAL,
                      StoredValue, canonical_text, parse_any)

__all__ = ['ExactReal', 'ExactComplex', 'ExactPAdic', 'ExactPolynomial',
           'ParseError', 'parse_real', 'parse_complex', 'parse_p_adic',
           'parse_polynomial', 'parse_any', 'canonical_text', 'StoredValue',
           'KIND_REAL', 'KIND_COMPLEX', 'KIND_P_ADIC', 'KIND_POLYNOMIAL']
