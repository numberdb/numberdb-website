import os, sys
sys.path.insert(0, '/work')
from generate import GaussSums
key = sys.stdin.read().strip()
if key:
	os.environ['NUMBERDB_API_KEY'] = key
print(GaussSums().publish(
	message="the part Gauss's theorem makes zero is now said to be zero, "
	        'rather than written as a ball that happens to be narrow'))
