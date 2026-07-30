"""Exact number representation for NumberDB.

Plain Python: no Sage, no Django. See docs/design/number-datastructures.md.
Sage conversion lives in a separate adapter, so this layer runs and is tested
on a bare interpreter.
"""

from .real import ExactReal, ParseError, parse_real

__all__ = ['ExactReal', 'ParseError', 'parse_real']
