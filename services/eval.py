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
import ast

def pluralize(string, count, singular_ending="", plural_ending="s"):

    if count == 1:
        return string + singular_ending
    else:
        return string + plural_ending

@Pyro5.api.expose
class SafeEval(object):
	
	def ping(self, send_back):
		return send_back
	
	def eval(self, source_sage):
		source_python = preparse(source_sage)
		e = eval(source_python)
		b = dumps(e) #of type bytes
		#s = b.hex() #long but should be fine
		#s = str(b,'utf-8','backslashreplace') #works but lot of backslashes
		s = str(b,'cp437') #good old Code Page 437
		return s

	def _parse_key(self, key):
		return str(key) #TODO: Might give away information about server!

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
					parent_key = parent_key + self._parse_key(key),
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
			except (ValueError, TypeError):
				params_error.append(parent_key)

		return result, params_error

	def check_Expr(self,e):
		if isinstance(e, ast.Expr):
			v = e.value
		else:
			v = e
		#print('dump e:', ast.dump(e))

		if isinstance(v, ast.BoolOp):
			#ignore v.op
			return all(self.check_Expr(val) for val in v.values)

		#Doesn't seem to exist anymore:
		#elif isinstance(v, ast.NamedExpr):
		#	return self.check_Expr(v.target) and \
		#			self.check_Expr(v.value)

		elif isinstance(v, ast.BinOp):
			#ignore v.op
			return self.check_Expr(v.left) and \
					self.check_Expr(v.right)

		elif isinstance(v, ast.UnaryOp):
			#ignore v.op
			return self.check_Expr(v.operand)

		elif isinstance(v, ast.Lambda):
			return self.check_Arguments(v.args) and \
					self.check_Expr(v.body)

		elif isinstance(v, ast.IfExp):
			return self.check_Expr(v.test) and \
					self.check_Expr(v.body) and \
					self.check_Expr(v.orelse)

		elif isinstance(v, ast.Dict):
			return all(self.check_Expr(key) for key in v.keys) and \
					all(self.check_Expr(val) for val in v.values)

		elif isinstance(v, ast.Set):
			return all(self.check_Expr(el) for el in v.elts)

		elif isinstance(v, ast.ListComp) or \
			isinstance(v, ast.SetComp) or \
			isinstance(v, ast.GeneratorExp):
			return self.check_Expr(v.element) and \
					all(self.check_Comprehension(gen) for gen in v.generators)

		elif isinstance(v, ast.DictComp):
			#print("DictComp")
			return self.check_Expr(v.key) and \
					self.check_Expr(v.value) and \
					all(self.check_Comprehension(gen) for gen in v.generators)

		elif isinstance(v, ast.Await):
			raise ValueError('No async code allowed.')

		elif isinstance(v, ast.Yield):
			return v.value == None or \
					self.check_Expr(v.value)

		elif isinstance(v, ast.YieldFrom):
			return self.check_Expr(v.value)

		elif isinstance(v, ast.Compare):
			#ignore v.ops
			return self.check_Expr(v.left) and \
					all(self.check_Expr(c) for c in v.comparators)

		elif isinstance(v, ast.Call):
			#TODO
			
			return self.check_Expr(v.func) and \
					all(self.check_Expr(arg) for arg in v.args) and \
					all(self.check_Keyword(keyword) for keyword in v.keywords)

		elif isinstance(v, ast.FormattedValue):
			#ignore v.conversion
			return self.check_Expr(v.value) and \
					(v.format_spec == None or \
					 self.check_Expr(v.format_spec))

		elif isinstance(v, ast.JoinedStr):
			return all(self.check_Expr(val) for val in v.values)

		elif isinstance(v, ast.Constant):
			#ignore v.kind
			return self.check_Constant(v.value)

		elif isinstance(v, ast.Attribute):
			return self.check_Expr(v.value) and \
					(v.attr == None or \
					 self.check_Identifier(v.attr)) and \
					(v.ctx == None or \
					 self.check_Expr_Context(v.ctx))

		elif isinstance(v, ast.Subscript):
			return self.check_Expr(v.value) and \
					self.check_Expr(v.slice) and \
					self.check_Expr_Context(v.ctx)

		elif isinstance(v, ast.Starred):
			return self.check_Expr(v.value) and \
					self.check_Expr_Context(v.ctx)

		elif isinstance(v, ast.Name):
			return self.check_Identifier(v.id) and \
					self.check_Expr_Context(v.ctx)

		elif isinstance(v, ast.List) or \
			isinstance(v, ast.Tuple):
			return all(self.check_Expr(e) for e in v.elts) and \
					self.check_Expr_Context(v.ctx)

		elif isinstance(v, ast.Slice):
			return (v.lower == None or \
					self.check_Expr(v.lower)) and \
					(v.upper == None or \
					 self.check_Expr(v.upper)) and \
					(v.step == None or \
					 self.check_Expr(v.step))
		#Python 3.7:
		
		elif isinstance(v, ast.Num) or \
			isinstance(v, ast.Ellipsis) or \
			isinstance(v, ast.NameConstant):
			#ignore
			return True

		elif isinstance(v, Str):
			return check_Identifier(v.s)
		
		else:
			raise ValueError('Unknown expression type')
		


	def check_Expr_Context(self,ctx):
		#Disallow ast.Del
		if isinstance(ctx, ast.Load) or \
			isinstance(ctx, ast.Store):
			return True
		else:
			raise ValueError('Store and Del not allowed.')

	def check_Comprehension(self,gen):
		if gen.is_async != 0:
			raise ValueError('No async code allowed.')
		return self.check_Expr(gen.target) and \
				self.check_Expr(gen.iter) and \
				all(self.check_Expr(i) for i in gen.ifs)

	def check_Arguments(self,arg):
		return all(self.check_Arg(a) for a in arg.posonlyargs) and \
				all(self.check_Arg(a) for a in arg.args) and \
				(a.vararg == None or \
				 self.check_Arg(a.vararg)) and \
				all(self.check_Arg(a) for a in arg.kwonlyargs) and \
				all(self.check_Expr(e) for e in arg.kw_defaults) and \
				(a.kwarg == None or \
				 self.check_Arg(a.kwarg)) and \
				all(self.check_Expr(e) for e in arg.defaults)
				
	def check_Arg(self,arg):
		#ignore arg.type_comment
		return self.check_Identifier(arg.arg) and \
				(arg.annotation == None or \
				 self.check_Expr(arg.annotation))
		
	def check_Keyword(self,keyword):
		return (keyword.arg == None or
				self.check_Identifier(keyword.arg)) and \
				self.check_Expr(keyword.value)
		
	def check_Identifier(self,id):
		if id.startswith('_') or \
			id.startswith('sage') or \
			id.startswith('SAGE_') or \
			id.endswith('_DIR') or \
			id.endswith('PATH') or \
			id.endswith('_DOCS') or \
			id in ('exit','quit','get_ipython', 
				'eval', 'parse', 'preparse',
				'localvars','locals','globals','In',
				'load', 'load_attach_mode', 'load_attach_path', 'load_session',
				'import', 'lazy_import', 'kernel',
				'interact', 'interacts',
				'install_scripts',
				'get_memory_usage',
				'get_display_manager',
				'get_remote_file',
				'getattr_debug',
				'fork',
				'loads','dumps',
				'attach','detach','attached_files',
				'alarm',
				'save', 'save_session', 
				'self',	'super', 'parallel', 'os',
				'HOSTNAME', 'LOCAL_IDENTIFIER', 'DOT_SAGE',
				'MTXLIB', 'MAXIMA_FAS', 'SINGULAR_SO', 'GAP_SO',
			):
			raise ValueError("Please don't hack the server.")
		
		return True
		
	def check_Constant(self,c):
		return True
			
	def check_python_expression(self,expression_python):
		module = ast.parse(expression_python)
		body = module.body
		if len(body) != 1:
			raise ValueError('Please enter exactly one expression.')
		e = body[0]
		if not isinstance(e, ast.Expr):
			raise ValueError('Please enter a SageMath expression.')
		return self.check_Expr(e)

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
				if not self.check_python_expression(program_python):
					raise ValueError("Please don't hack the server.")				
				program_evaluated = eval(program_python, globals())
				#print("program_evaluated:", program_evaluated, type(program_evaluated))
			except ValueError as e:
				messages.append({
					'tags': 'alert-danger',
					'text': '%s' % (e,),
				})
				return wrap_result(None, messages)
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
					
					text = '%s %s with the following parameters could not be converted into real intervals: %s.' % (
						len(params_error), 
						pluralize('number',len(params_error)),
						'; '.join(params_error),
					)
				else:
					text = '%s %s could not be converted into real intervals.' % (
						len(params_error),
						pluralize('number',len(params_error)),
					)
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

		except Exception as e:
			#messages = []
			messages.append({
				'tags': 'alert-danger',
				'text': 'Error: %s' % (e,),
			})
			return wrap_result(None, messages)

		return wrap_result(param_numbers, messages)

daemon = Pyro5.server.Daemon()         # make a Pyro daemon
ns = Pyro5.api.locate_ns()             # find the name server
uri = daemon.register(SafeEval)   # register the greeting maker as a Pyro object
ns.register("save_eval", uri)   # register the object with a name in the name server

print("Ready.")
daemon.requestLoop()
