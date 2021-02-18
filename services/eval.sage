'''
How to run service:
1. Run name server:
  sage -python -m Pyro5.nameserver
2. Run eval service:
  sage eval.sage
3. From separate project (running via sage or sage -python):
  import Pyro5.api
  E = Pyro5.api.Proxy("PYRONAME:eval")
  response = E.eval("24")
  result = loads(bytes(response,encoding='cp437'))
'''

import Pyro5.api
from sage.all import *
#from sage.rings.all import *
import json

@Pyro5.api.expose
class SafeEval(object):
	def eval(self, source_sage):
		source_python = preparse(source_sage)
		e = eval(source_python)
		b = dumps(e) #of type bytes
		#s = b.hex() #long but should be fine
		#s = str(b,'utf-8','backslashreplace') #works but lot of backslashes
		s = str(b,'cp437') #good old Code Page 437
		return s

	def _parse_numbers(self, nested, parent_key = '', separator=', '):
		'''
			Returns a list of pairs (key, value), possibly with repeating keys.
			Returns also a list of parameters whose numbers could not be turned into a real interval.
		'''
		
		result = []
		params_error = []

		if isinstance(nested, dict):
			
			result = []
			params_error = []
			if parent_key != '':
				parent_key = parent_key + separator
			for key, value in nested.items():
				result_i, params_error_i = self._parse_numbers(
					value, 
					parent_key = parent_key + str(key),
					separator = separator,
				)
				result += result_i
				params_error += params_error_i

		elif is_iterator(nested) or \
			isinstance(nested,list) or \
			isinstance(nested,range):
			
			for value in nested:
				result_i, params_error_i = self._parse_numbers(
					value, 
					parent_key = parent_key,
					separator = separator,
				)
				result += result_i
				params_error += params_error_i
			
		else:
			
			try:
				value = RIF(nested)
				result.append((parent_key, value))
			except ValueError:
				params_error.append(parent_key)

		return result, params_error

	def eval_search_program(self, program, max_numbers = 1000):

		messages = []
		
		def wrap_result(param_numbers, messages):
			cancel_alarm()
			result_bytes = dumps((param_numbers, messages))
			result = str(result_bytes,'cp437')
			return result

		try:
			alarm(1)
		
			try:
				program_python = preparse(program)
				print("program_python:", program_python)
				program_evaluated = eval(program_python, globals())
				#print("program_evaluated:", program_evaluated, type(program_evaluated))
			except Exception as e:
				messages.append({
					'tags': 'alert-danger',
					'text': 'Parsing error: %s' % (e,),
				})
				return wrap_result(None, messages)
				
			param_numbers, params_error = self._parse_numbers(program_evaluated)
			
			if len(param_numbers) > max_numbers:
				param_numbers = param_numbers[:max_numbers]
				messages.append({
					'tags': 'alert-warning',
					'text': 'We only check the first %s given numbers.' % (max_numbers,),
				})
			
			if len(params_error) > 0:
				if len(params_error) <= 100 and \
					all(param != '' for param in params_error):
					
					text = 'The %s numbers with the following parameters could not be converted into real intervals: %s.' % \
							(len(param_errors), '; '.join(params_error))
				else:
					text = '%s numbers could not be converted into real intervals.' % \
							(len(param_errors),)
				messages.append({
					'tags': 'alert-danger',
					'text': text,
				})
				
			cancel_alarm()
			
		except AlarmInterrupt:
			messages = []
			messages.append({
				'tags': 'alert-danger',
				'text': 'Timed out (1 second).',
			})
			return wrap_result(None, messages)

		return wrap_result(param_numbers, messages)

daemon = Pyro5.server.Daemon()         # make a Pyro daemon
ns = Pyro5.api.locate_ns()             # find the name server
uri = daemon.register(SafeEval)   # register the greeting maker as a Pyro object
ns.register("save_eval", uri)   # register the object with a name in the name server

print("Ready.")
daemon.requestLoop()
