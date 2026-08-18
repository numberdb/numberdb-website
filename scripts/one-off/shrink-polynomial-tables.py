"""Shrink T108 and T109 to n = 0..100, deleting what the run does not produce.

    sage -python scripts/one-off/shrink-polynomial-tables.py

The tables were first filled to n = 150. A hundred is where the other
polynomial tables stop and where an entry stops being something anybody reads:
F_150 is 2248 characters against F_100's 1107.

`removing=True` is what deletes 101..150 -- it sends the whole table and drops
whatever this run did not produce. It is not a flag on the generators
themselves, deliberately: a generator that can delete its table's entries with
one word on the command line is one typo from doing it.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'generators', 'fibonacci-polynomials'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..',
                                'generators', 'lucas-polynomials'))

import importlib.util


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


here = os.path.dirname(os.path.abspath(__file__))
root = os.path.join(here, '..', '..', 'generators')

for folder, class_name in (('fibonacci-polynomials', 'FibonacciPolynomials'),
                           ('lucas-polynomials', 'LucasPolynomials')):
    module = load(folder.replace('-', '_'),
                  os.path.join(root, folder, 'generate.py'))
    generator = getattr(module, class_name)()
    outcome = generator.publish(
        removing=True,
        message='shortened to n = 0..%d; the longer polynomials are past '
                'what anybody reads' % (module.UP_TO,))
    print('%-24s %s' % (folder, outcome))
