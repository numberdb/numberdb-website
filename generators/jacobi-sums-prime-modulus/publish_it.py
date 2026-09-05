import os, sys
sys.path.insert(0, '/work')
from generate import JacobiSums
key = sys.stdin.read().strip()
if key:
	os.environ['NUMBERDB_API_KEY'] = key
print(JacobiSums().publish(
	message='the Jacobi sums that are Gaussian integers now say so, rather '
	        'than being written as a hundred digits of an integer'))
