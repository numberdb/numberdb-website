"""A few chosen entries, old spelling against new."""
import json

from generate import QuadraticAlgebraicNumbers
from numberdb._write import to_text

WANTED = ['1,-4,5/1', '1,0,1/1', '1,-3,3/1', '1,-1,1/1', '1,-5,-4/2', '1,-1,-1/1']

with open('/work/T35.json', encoding='utf8') as handle:
	document = json.load(handle)

flat = {}


def walk(node, prefix):
	if isinstance(node, dict) and not {'number', 'equals'} & set(node):
		for key, value in node.items():
			walk(value, prefix + [str(key)])
		return
	flat['/'.join(prefix)] = str(node.get('number') if isinstance(node, dict)
	                             else node)


walk(document['Numbers'], [])

generator = QuadraticAlgebraicNumbers()
for params in generator.enumerate():
	key = '%s,%s,%s/%s' % (params['a2'], params['a1'], params['a0'],
	                       params['n'])
	if key not in WANTED:
		continue
	entry = generator.value(params, generator.digits)
	number = entry['number'] if isinstance(entry, dict) else entry
	now = to_text(number, generator.digits)
	was = flat.get(key, '(absent)')
	print('%-12s %s' % (key, 'SAME' if was == now else 'DIFFERS'))
	print('    was: %s' % (was[:78],))
	print('    now: %s' % (now[:78],))
