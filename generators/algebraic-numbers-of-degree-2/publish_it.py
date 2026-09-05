"""Send the regenerated entries to T35.

The key arrives on stdin, which is how `agents/sage.sh` carries one, and is
never written down here.
"""
import os
import sys

from generate import QuadraticAlgebraicNumbers

key = sys.stdin.read().strip()
if key:
	os.environ['NUMBERDB_API_KEY'] = key

generator = QuadraticAlgebraicNumbers()
print(generator.publish(
	message='regenerated from a Generator: a component that is exact is '
	        'written as one, rather than as a decimal long enough to look '
	        'like it'))
