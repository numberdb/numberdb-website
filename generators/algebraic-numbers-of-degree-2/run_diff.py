"""Run the port and compare it with what T35 holds. No network needed."""
import sys

from generate import QuadraticAlgebraicNumbers

import diff_against_stored

sys.exit(diff_against_stored.main(QuadraticAlgebraicNumbers()))
