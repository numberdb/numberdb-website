import timeout_decorator
import multiprocessing
import func_timeout
from cysignals import AlarmInterrupt
from cysignals.alarm import alarm, cancel_alarm
import re

from sage import *
from sage.rings.all import *
from sage.misc.flatten import flatten

RIFprec = RealIntervalField(1000)
RBFprec = RealBallField(1000)

def parse_integer(s):
	cZZ = re.compile(r'^([+-]?)(\d+)$')
	matchZZ = cZZ.match(s)
	if matchZZ == None:
		return None
	return ZZ(int(s)) #int takes care of leading zeros

def parse_positive_integer(s):
	cZZplus = re.compile(r'^\d+$')
	matchZZplus = cZZplus.match(s)
	if matchZZplus == None:
		return None
	return ZZ(int(s)) #int takes care of leading zeros

def parse_rational_number(s):
    ab = s.split('/', maxsplit=1)
    
    if len(ab) == 1:
        return parse_integer(s)
    
    elif len(ab) == 2:
        a = parse_integer(ab[0])
        if a != None:
            b = parse_integer(ab[1])
            if b != None:
                return a/b
    
    return None;        

def parse_real_interval(s, RIF=RIF):
    #First sage's RIF notation:
    cRIF = re.compile(r'^([+-]?)(\d*\??)((?:\.\d*\??)?)((?:[eE]-?\d+)?)$')
    matchRIF = cRIF.match(s)
    if matchRIF != None:
        #Given searchterm is a real interval:
        #if '?' in s:
        #	return RIF(s)

        #If no '?' in s, we will treat last given digit as possibly off by 1:
        sign, a, b, e = matchRIF.groups()
        if a[-1] == "?" and b != '':
            return None #Invalid format
        a = a.rstrip('?')
        b = b.rstrip('?')
        if sign != '-':
            sign = ''
        if b != '':
            b = b[1:]
        exp = ZZ(e[1:]) if e != '' else 0 
        exp -= len(b)
        ab = (a + b).lstrip('0')
        
        #Don't crop here during parsing:
        #ab_cropped = ab[:SearchTerm.MAX_LENGTH_TERM_FOR_REAL_FRAC]
        #print("ab,ab_cropped:",ab,ab_cropped)
        #exp += len(ab) - len(ab_cropped)
        
        f = ZZ(int(sign + ab)) if ab != '' else 0			
        r = RIF(f-1,f+1) * RIF(10)**exp
        return r
        
    #Next try numberdb's p-notation:
    cRIF_P = re.compile(r'^([+-]?)(\d*)[pP]([+-]?)([1-9]\d*)$')
    matchRIF_P = cRIF_P.match(s)
    if matchRIF_P != None:
        #Given searchterm is a real interval in "p-notation":
        signExp, exp, signFrac, frac = matchRIF_P.groups()
        #print("signExp, exp, signFrac, frac:",signExp, exp, signFrac, frac)
        if signExp != '-':
            signExp = ''
        if signFrac != '-':
            signFrac = ''
        exp = ZZ(int(signExp + exp)) if exp != '' else 0 
        
        #Don't crop here during parsing:
        #frac_cropped = frac[:SearchTerm.MAX_LENGTH_TERM_FOR_REAL_FRAC]
        
        exp -= len(frac)
        f = ZZ(int(signFrac + frac))
        r = RIF(f-1,f+1) * RIF(10)**exp
        return r

    #print("s:",s)	
    if (s[0] == '[' and s[-1] == ']') or \
        (s[0] == '(' and s[-1] == ')'):
        l_u = s[1:-1].split(',')
        #print("l_u:",l_u)
        if len(l_u) == 2:
            l, u = l_u
            l = l.strip()
            u = u.strip()
            try:
                l = RIF(l)
                u = RIF(u)
                r = l.union(u)
                return r
            except TypeError:
                pass                
                
            '''
            lower = parse_real_interval(l)
            if lower != None:
                upper = parse_real_interval(u)
                if upper != None:
                    r = lower.union(upper)
                    return r
            '''
    return None

def parse_fractional_part(s):
	f = parse_integer(s)
	if f == None:
		return None
	r = RIF(f-1,f+1) * RIF(10)**(-len(s.lstrip('-+')))
	if r < 0:
		r += 1
	return r
	
def blur_real_interval(r, blur_bits = 2):
    #print("r:",r)
    #print("r.lower(), r.upper():",r.lower(),r.upper())
    #print("r.prec():",r.prec())
    e = r.prec() - blur_bits
    blur = RIF(1 - 2**(-e), 1 + 2**(-e))
    return r * blur	


def to_bytes(m):
    if isinstance(m,bytes):
        return m
    if isinstance(m,memoryview):
        return m.tobytes()

def real_interval_to_pretty_string(r):

    if r.contains_zero():
        #Relative diameter won't make sense, 
        #so just print it normally:
        return r.__str__()

    if r.relative_diameter() < 0.001:
        #Enough relative precision,
        #thus print the number normally:
        return r.__str__()

    else:
        #Not enough relative precision, 
        #thus rather print the number as an interval:
        Rup = RealField(15,rnd='RNDU')
        Rdown = RealField(15,rnd='RNDD')
        return '[%s,%s]' % (Rdown(r.lower()),Rup(r.upper()))
        
def real_interval_to_string_via_endpoints(r):
    return '[%s,%s]' % (r.lower(),r.upper(),)

def pluralize(string, count, singular_ending="", plural_ending="s"):

    if count == 1:
        return string + singular_ending
    else:
        return string + plural_ending

css_grid_classes = None #unique global such dictionary

def get_css_grid_classes():
    r"""
    Returns a dictionary with CSS classes that are used in 
    responsive html design via grids with 12 columns.
    If an html container has class "grid12", 
    then an item in that container might want to have class
    css_grid_classes()["default"].
    """
    
    global css_grid_classes
    if css_grid_classes is not None:
        return css_grid_classes
    css_grid_classes = {
        #horizontal spacing:
        'tiny': "col-l-1, col-m-2, col-s-3, col-xs-4",
        'small': "col-xxl-1 col-l-2, col-m-3, col-s-4, col-xs-6",
        'normal': "col-xxxxl-1 col-xl-2 col-l-3 col-m-4 col-s-6",
        'wide_next_to_normal': "col-xxxl-2 col-xxl-3 col-xl-4 col-l-6 col-m-8", #good if used next to 'normal's
        'wide_next_to_wide': "col-xxxl-2 col-xxl-3 col-xl-4 col-l-6", #good wrapping if used next to same kind
        'wider_next_to_normal': "col-xxxxl-2 col-xxxl-3 col-xxl-4 col-xl-6 col-l-9", #good if used next to 'normal'
        'full_row': "col-all",
         #vertical spacing:
        'row_span_2': "row-span-2",
        'row_span_3': "row-span-3",
        'row_span_4': "row-span-4"
    }
    css_grid_classes['default'] = css_grid_classes['normal']
    return css_grid_classes

def number_param_groups_to_bytes(param, separator=','):
    p = separator.join(flatten(param))
    p = bytes(p,encoding='cp437')
    return p

def number_param_groups_to_string(param, separator=','):
    return number_param_groups_to_bytes(param, separator).decode()

'''
#Doesn't work in multithreaded processes:
@timeout_decorator.timeout(1)
def factor_with_timeout(n):
    return n.factor()
'''

'''
#Doesn't work, doesn't kill timed-out processes:
def factor_with_timeout(n):
    @timeout_decorator.timeout(1,use_signals=False)
    def factor_n(n):
        return n.factor()

    try:
        return factor_n(n)
    except timeout_decorator.TimeoutError:
        return None
'''

'''
#Doesn't work, doesn't hear alarm signal:
def factor_with_timeout(n):
    try:
        alarm(1)
        result = n.factor()
        cancel_alarm()
        return result
    except AlarmError:
        return None
'''

'''
#Doesn't work, doesn't kill timed-out processes:
def factor_with_timeout(n):
    def factor_n(n,return_dict):
        return_dict[n] = n.factor()
        return 0
        
    manager = multiprocessing.Manager()
    return_dict = manager.dict()
    p = multiprocessing.Process(target=factor_n, name='factor_n', args=(n,return_dict))
    p.start()
    p.join(timeout=1)
    p.terminate()
    
    #if p.exitcode is None:
    #   print(f'Oops, {p1} timeouts!')
    if p.exitcode == 0:
        return return_dict[n]

    return None
'''

'''
#Doesn't work, doesn't hear the timeout:
def factor_with_timeout(n):
    
    @func_timeout.func_set_timeout(1)
    def factor_n(n):
        return n.factor()
    
    try:
        return factor_n(n)
    except func_timeout.FunctionTimedOut:
        return None
'''

#Work-around: (TODO: Need proper time-out)
def factor_with_timeout(n):
    if n.abs() <= 10**50:
        return n.factor()
    else:
        return None

class StableContinuedFraction:
    
    def __init__(self, r):
        '''
        INPUT: An element of RealIntervalField.        
        '''
        
        self._coefficients = []
        q = r
        while True:
            try:
                a = q.unique_floor()
            except ValueError:
                self._coefficients.append('?')
                break
            self._coefficients.append(a)
            f = q-a
            if f == 0:
                if self._coefficients == []:
                    self._coefficients = [ZZ(0)]
                break
            q = 1/f

    def list(self):
        '''
        OUTPUT: 
        Coefficients of the continued fraction.
        If the represented number is not rational, the last entry will be '?'.        
        '''
        
        return self._coefficients
        
    def sage(self):
        '''
        OUTPUT:
        The corresponding ContinuedFraction_periodic instance of sage.

        Warnings: 
        - A possible last entry '?' that signifies numerical uncertainty
          will be omitted.
        - Sage's datastructure simplifies [..., n, 1] to [..., n+1].
        '''
        
        coeffs = self._coefficients
        if len(coeffs) == 0:
            result = coeffs
        else:
            result = coeffs[:-1]
            if coeffs[-1] != '?':
                result.append(coeffs[-1])
        return continued_fraction(result)

    def latex(self, ellipsis='\\ldots'):
        '''
        OUTPUT: Latex code that represents self, without enclosing '$'.        
        '''

        #Don't recurse in case cf is very long...
        coeffs = self._coefficients
        if len(coeffs) == 0:
            return '0'
        result = ''
        for a in coeffs[:-1]:
            result += '%s + \\frac{\\displaystyle 1}{\\displaystyle ' % (a,)
        result += str(coeffs[-1] if coeffs[-1] != '?' else ellipsis)
        result += ''.join('}' for a in range(len(coeffs)-1))
        #print("cf latex:",result)
        return result
        
    def __str__(self, ellipsis='...'):
        result = '[%s]' % (
            ', '.join(str(x) if x != '?' else ellipsis for x in self._coefficients),
        )
        return result
        
    def __repr__(self):
        return self.__str__()

