import timeout_decorator
import multiprocessing
#import func_timeout
from cysignals import AlarmInterrupt
from cysignals.alarm import alarm, cancel_alarm
import re


#from sage import *
from sage.all import infinity, SR, SymmetricGroup, I, continued_fraction, Integer
from sage.rings.all import ZZ, QQ, RR, CC, RIF, CIF, RBF, CBF, Qp
from sage.rings.all import RealField, RealIntervalField, RealBallField
from sage.rings.all import ComplexField, ComplexIntervalField, ComplexBallField
from sage.rings.all import PolynomialRing
from sage.misc.flatten import flatten
from sage.repl.preparse import preparse

RIFprec = RealIntervalField(1000)
RBFprec = RealBallField(1000)
CIFprec = ComplexIntervalField(1000)
CBFprec = ComplexBallField(1000)

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

def _interval_endpoint(text, RIF=RIF):
    """One endpoint of an explicit interval, or None.

    A decimal or an integer, which `RIF` reads itself, or an exact rational,
    which it does not: `RIF('3/2')` raises, so `[3/2, 3/2]` was refused
    outright. The exact layer accepts that spelling and stores it faithfully,
    so a value written that way was kept and never indexed -- present on its
    page and unfindable by its digits, which is the shape of fault that once
    hid 101 numbers.
    """
    try:
        return RIF(text)
    except (TypeError, ValueError, ArithmeticError):
        pass
    try:
        rational = parse_rational_number(text)
    except ArithmeticError:
        #`[1/0, 2]` divides in the parser rather than returning None.
        return None
    if rational is None:
        return None
    try:
        return RIF(rational)
    except (TypeError, ValueError, ArithmeticError):
        return None


def parse_real_interval(s, RIF=RIF, allow_rationals=True):

    #First try _exact_ rational numbers:
    if allow_rationals:
        result = parse_rational_number(s)
        if result != None:
            return RIF(result)

    #Next sage's RIF notation:
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
            l = _interval_endpoint(l, RIF)
            u = _interval_endpoint(u, RIF)
            if l is not None and u is not None:
                return l.union(u)
                
            '''
            lower = parse_real_interval(l)
            if lower != None:
                upper = parse_real_interval(u)
                if upper != None:
                    r = lower.union(upper)
                    return r
            '''

    #Real balls, e.g. "3.14 +/- 2e-2", which help.html documents as a supported
    #format and which numberdb-data actually uses -- the Riemann zeta zeros and
    #the physical constants are all stored this way.
    #
    #Arb parses this natively once wrapped in brackets. Deliberately the same
    #route data_pipeline/build.py takes when importing, so that a value which
    #imports cleanly is also searchable; before this, the two paths disagreed
    #and the search side returned None, leaving callers to fail on
    #'NoneType' has no attribute 'lower'.
    if '+/-' in s:
        try:
            return RIF(RBFprec('[%s]' % (s,)))
        except (TypeError, ValueError):
            pass

    return None

def parse_fractional_part(s):
	f = parse_integer(s)
	if f == None:
		return None
	r = RIF(f-1,f+1) * RIF(10)**(-len(s.lstrip('-+')))
	if r < 0:
		r += 1
	return r
	
def parse_p_adic(s):
	s = s.strip().replace(' ','')
	
	#Try to read p-adic number as:
	#<expression of rational number> + O(p^e)
	cQp = re.compile(r'^([\+\-\*/\^\d]*)\+O\((\d+)\^(\-?\d+)\)$')
	matchQp = cQp.match(s)
	if matchQp != None:
		#Given searchterm is a p-adic number:
		a, p, e = matchQp.groups()
		p = ZZ(p)
		e = ZZ(e)
		#print("a,p,e:",a,p,e)
		#print("preparse(a):",preparse(a))
		A = eval(preparse(a))
		#print("A:",A)
		prec = e + min(0,-A.valuation(p))
		Q_p = Qp(p,prec=prec)
		result = Q_p(A).add_bigoh(e)
		return result

	#Try to read p-adic number as:
	#O(p^e)
	cQp = re.compile(r'^O\((\d+)\^(\-?\d+)\)$')
	matchQp = cQp.match(s)
	if matchQp != None:
		#Given searchterm is a p-adic number:
		p, e = matchQp.groups()
		p = ZZ(p)
		e = ZZ(e)
		prec = e
		Q_p = Qp(p,prec=prec)
		result = Q_p(0).add_bigoh(e)
		return result
	
	#Try to read p-adic number as:
	#Qp:digits	
	cQp2 = re.compile(r'^[qQzZ](\d+)[: ](\-?)((?:\d*\.)?)(\d*)$')
	matchQp2 = cQp2.match(s)
	if matchQp2 != None:
		p, sign, digits0, digits1 = matchQp2.groups()
		#The group is (?:\d*\.)? so it captures the separator as well. Leaving
		#it in counts '.' as a digit, and the loop below then evaluates ZZ('.')
		#-- which is why the documented "Q2:1.1010" raised
		#TypeError: unable to convert '.' to an integer.
		if digits0.endswith('.'):
			digits0 = digits0[:-1]
		lenp = ZZ(len(p))
		p = ZZ(p)
		lend0 = ZZ(len(digits0))
		lend1 = ZZ(len(digits1))
		if lend0 % lenp == 0 and lend1 % lenp == 0:
			num_digits0 = ZZ(lend0/lenp)
			num_digits1 = ZZ(lend1/lenp)
			prec = num_digits0 + num_digits1
			Q_p = Qp(p, prec = prec)
			result = Q_p(0)
			for i in range(num_digits0):
				result += Q_p(ZZ(digits0[lenp*i:lenp*(i+1)]) * p**(i-num_digits0))
			for i in range(num_digits1):
				result += Q_p(ZZ(digits1[lenp*i:lenp*(i+1)]) * p**i)
			result = result.add_bigoh(num_digits1)
			if sign == '-':
				result = -result
			return result
		
	return None	
    
    
def parse_polynomial(s):
	#s = s.strip().replace(' ','')
    
    if '.' in s:
        #Only exact coefficients are implemented.
        #In the future, we might accept coefficients in RIF/CIF/RBF/CBF,
        #but we will need to parse them as such.
        #At the moment, floats would be transformed into rational numbers
        #when computing SR(s).polynomial(QQ)!
        return None
    
    try:
        symbolic_expression = SR(s)
    except TypeError:
        return None
    
    #vars = symbolic_expression.variables()
	
    try:
        p = symbolic_expression.polynomial(QQ)
    except TypeError:
        return None

    R = p.parent()
    variables = R.variable_names()
    R2 = PolynomialRing(QQ,variables)
    if R != R2:
        return None
        
    p2 = R2(p)
    return p2

def polynomial_modulo_variable_names(p):
    '''
    We consider two polynomials equivalent if they are the same up
    to a (1-to-1) relabeling of the variables.
    The method returns a unique polynomial in the equivalence class of p.        
    '''
    
    R = p.parent()
    variables = p.variables()
    n = len(variables)

    #Change variable names to x0, x1, ...:
    R_std = PolynomialRing(QQ,n,'x',order='degrevlex')
    im_gens = []
    for i, g in enumerate(R.gens()):
        try:
            i_var = variables.index(g)
        except ValueError:
            i_var = -1
        if i_var >= 0:
            im_gens.append(R_std.gen(i_var))
        else:
            im_gens.append(R_std(0))
    hom_R_to_R_std = R.hom(codomain = R_std, im_gens = im_gens)
    p_std = hom_R_to_R_std(p)
    if n == 0:
        return p_std

    p, R, variables = p_std, R_std, R_std.gens()

    #coeffs = {exp: coeff for exp,coeff in zip(p2.exponents(),p2.coefficients())}

    Sn = SymmetricGroup(range(n))
    
    #Find equivalent polynomials with minimal exponent vector list:
    p_mins = []
    exp_min = None
        
    for sigma in Sn:
        hom_sigma = R.hom(im_gens = [R.gen(sigma(i)) for i in range(n)])
        p_sigma = hom_sigma(p)
        exp_sigma = p_sigma.exponents()
        if len(p_mins) == 0:
            p_mins.append(p_sigma)
            exp_min = exp_sigma
        elif exp_min > exp_sigma:
            p_mins = [p_sigma]
        elif exp_min == exp_sigma:
            p_mins.append(p_sigma)
        else:
            continue
    
    #Among all equivalent polynomials with minimal exponent vector list,
    #take the polynomial with minimal coefficint list:        
    p_mins.sort(key = lambda p_sigma: p_sigma.coefficients())
    p_min = p_mins[0]
    
    return p_min

def _split_complex_terms(s):
    '''
    Split a complex expression into (sign, term) pairs at top-level '+'/'-'.

    Separators inside brackets are ignored, so a component may itself be an
    interval: "[0.833,0.834]+[5.399,5.601]*i" splits into two terms, not five.
    The previous regex split on (digit)(+|-), which meant a '+' following a ']'
    was not a separator at all -- so bracket components parsed in the imaginary
    position but not the real one.

    Requiring a digit or a closing bracket before the sign is what keeps
    exponents intact: the '-' in "1e-5" follows 'e' and is not a separator.
    '''

    terms = []
    depth = 0
    start = 0
    sign = 1
    for index, character in enumerate(s):
        if character in '[(':
            depth += 1
        elif character in '])':
            depth -= 1
        elif (character in '+-' and depth == 0 and index > 0
              and (s[index - 1].isdigit() or s[index - 1] in ')].')):
            terms.append((sign, s[start:index]))
            sign = 1 if character == '+' else -1
            start = index + 1
    terms.append((sign, s[start:]))
    return terms


def parse_complex_interval(s, CIF=CIF, allow_rationals=True):
    RIF = RealIntervalField(CIF.prec())
    s = s.strip().lower().replace(' ','').replace('j','i')
    result = CIF(0)
    for term_sign, summand in _split_complex_terms(s):
        coeff = term_sign

        if summand == '':
            continue
        elif summand == 'i':
            result += coeff * I
            continue
        elif summand == '-i':
            result += coeff * (-I)
            continue
        
        if summand.startswith('i*'):
            coeff *= I
            summand = summand[2:]
        elif summand.startswith('-i*'):
            coeff *= -I
            summand = summand[3:]
        
        if summand.endswith('*i'):
            coeff *= I
            summand = summand[:-2]
        elif summand.endswith('i'):
            #"5.5i" as well as "5.5*i". No real-number format ends in 'i', so
            #this is unambiguous, and it is what people actually type.
            coeff *= I
            summand = summand[:-1]

        r = parse_real_interval(summand,RIF=RIF,allow_rationals=allow_rationals)
        if r == None:
            return None
        result += coeff * r
    return result
        
    
def blur_real_interval(r, blur_bits = 2):
    #print("r:",r)
    #print("r.lower(), r.upper():",r.lower(),r.upper())
    #print("r.prec():",r.prec())
    e = r.prec() - blur_bits
    blur = r.parent()(1 - 2**(-e), 1 + 2**(-e))
    return r * blur	

def blur_complex_interval(c, blur_bits = 2):
    return c.parent()(
        blur_real_interval(c.real(), blur_bits),
        blur_real_interval(c.imag(), blur_bits),
    )

def to_bytes(m):
    if isinstance(m,bytes):
        return m
    if isinstance(m,memoryview):
        return m.tobytes()

def real_interval_to_pretty_string(r):
    '''
    Render a real interval in one of the formats documented to users
    (help.html "Number types and displayed accuracy", and the front-page tips
    in templates/includes/search-tips.html).

    Sage's '?' notation is deliberately removed. The documented convention
    already carries that information positionally: a value containing '.' or
    'e' *is* an interval whose last digit may be off by one, and a value with
    neither is an exact integer. So "3.14" already means [3.13, 3.15], and
    "3.14?" would say the same thing twice -- in a notation that appears in
    neither user-facing document, leaving a reader to guess.

    A useful consequence: every string produced here is valid input. A number
    can be copied out of a result and pasted straight back into the search bar,
    which was not true while '?' was attached.

    Soundness is preserved in the direction that matters. Dropping '?' never
    narrows the interval a reader would infer: "1.0000001?e21" becomes
    "1.0000001e21", which denotes [1.0000000e21, 1.0000002e21] and still
    contains the original. Displayed intervals may be wider than stored ones,
    never narrower -- see docs/design/number-representation.md.
    '''

    def as_bracketed_interval(r):
        #Endpoints rounded outward, so the shown interval always contains the
        #stored one.
        Rup = RealField(15,rnd='RNDU')
        Rdown = RealField(15,rnd='RNDD')
        return '[%s,%s]' % (Rdown(r.lower()),Rup(r.upper()))

    if r.lower() == r.upper():
        #Exact. Renders without '.' or 'e', which is precisely what marks it as
        #exact rather than as an interval.
        return r.__str__().replace('?', '')

    if r.contains_zero():
        #Relative diameter is meaningless here, and the decimal form degrades
        #badly: [-0.1, 0.1] used to print as "0.", which denotes [-1, 1] --
        #sound, but a decimal digit poorer for no reason. The bracket form
        #keeps the endpoints.
        return as_bracketed_interval(r)

    if r.relative_diameter() < 0.001:
        #Enough relative precision,
        #thus print the number normally:
        return r.__str__().replace('?', '')

    else:
        #Not enough relative precision,
        #thus rather print the number as an interval:
        return as_bracketed_interval(r)


def complex_interval_to_pretty_string(c):
    '''
    Render a complex interval as "A + B*I" / "A - B*I", where each component is
    rendered by real_interval_to_pretty_string -- so both parts use the formats
    documented on the front page for entering complex numbers.

    Complex numbers previously had no pretty-printer at all: NumberComplex
    rendered straight from str(CIF), which bypassed the real printer's bracket
    fallback and so threw away a digit whenever relative precision was poor.
    An imaginary part of [5.4, 5.6] -- what "5.5" denotes -- displayed as "6.",
    which means [5, 7]. Sound, in that it still contains the value, but a
    reader who typed 5.5 saw 6.

    The tight decimal form is genuinely unreachable here, and it is worth
    recording why. "5.5" denotes exactly [5.4, 5.6], which would be perfect --
    but the stored interval is [5.39999999999999, 5.60000000000001], very
    slightly wider because converting exact decimal bounds to binary must round
    outward. So "5.5" no longer contains what is stored, and rendering it would
    claim precision that is not there. The bracket form "[5.399,5.601]" is the
    honest tight answer. See docs/design/number-representation.md.
    '''

    real_part = real_interval_to_pretty_string(c.real())
    imaginary = c.imag()

    #Fold a wholly negative imaginary part into the joining sign, so results
    #read "a - b*I" rather than "a + -b*I".
    if imaginary.upper() < 0:
        joiner = ' - '
        imaginary_part = real_interval_to_pretty_string(-imaginary)
    else:
        joiner = ' + '
        imaginary_part = real_interval_to_pretty_string(imaginary)

    return '%s%s%s*I' % (real_part, joiner, imaginary_part)
        
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

def number_param_groups_to_bytes(params, separator=','):
    params = flatten(params)
    #normalize separator in parameter groups:
    params = (separator.join(p.strip(' ') for p in param.split(',')) for param in params) 
    result = separator.join(params)
    result = bytes(result, encoding='cp437')
    return result

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
    if (n not in QQ) or n.abs() <= 10**50:
        #Do computation locally:
        return n.factor()
    else:
        #Larger values are not factored here; the sandboxed evaluator
        #(docs/design/eval-sandbox.md) is the place for expensive work.
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
        
    def determined_coefficients(self):
        '''
        OUTPUT:
        The coefficients that are actually pinned down by the interval, i.e.
        without a trailing '?'.

        This is empty when the interval is too wide to determine even the first
        partial quotient -- e.g. "12e2" denotes [1100, 1300], which contains
        many integers, so no floor is unique and nothing at all is known about
        the continued fraction. Callers should check this before calling
        sage().
        '''

        return [a for a in self._coefficients if a != '?']

    def sage(self):
        '''
        OUTPUT:
        The corresponding ContinuedFraction_periodic instance of sage.

        Warnings:
        - A possible last entry '?' that signifies numerical uncertainty
          will be omitted.
        - Sage's datastructure simplifies [..., n, 1] to [..., n+1].

        Raises ValueError if no coefficient is determined, because Sage cannot
        represent the empty continued fraction -- it reports it as "continued
        fraction can not represent infinity", which is accurate but says
        nothing useful about the input. Use determined_coefficients() to check
        first.
        '''

        coeffs = self._coefficients
        if len(coeffs) == 0:
            result = coeffs
        else:
            result = coeffs[:-1]
            if coeffs[-1] != '?':
                result.append(coeffs[-1])
        if len(result) == 0:
            raise ValueError(
                'interval is too wide to determine any partial quotient'
            )
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

def number_with_uncertainty_to_real_ball(N, standard_deviations = 5):
    #Number with uncertainty:
    cNU = re.compile(r'^([+-]?)(\d*)((?:\.\d*))((?:\(\d+\)))((?:[eE]-?\d+)?)$')

    #Determine type of search term:

    match = cNU.match(N)
    if match == None:
        return None
    #print('match:', match)
    #print('groups:',match.groups())
    sign,uA,B,U,E = match.groups()
    A = sign + uA
    if B == '':
        B == '.'
    if U == '':
        U = '(0)'
    if E == '':
        e = 0
    else:
        e = ZZ(E[1:])
    p = len(B)-1
    ab = ZZ(int(A + B[1:])) #first calling int strips trailing zeros
    u = ZZ(int(U[1:-1]))
    radius = u * standard_deviations
    #N_center = str(ab) + E
    #N_radius = str(radius) + E
    #print('N_center:',N_center)
    #print('N_radius:',N_radius)
    r = RBF(ab,radius) * ZZ(10)**(e-p)
    return r

def is_polynomial_ring(R):
    return str(R).startswith('Multivariate Polynomial Ring') or \
			str(R).startswith('Univariate Polynomial Ring')

def is_pAdicField(K):
    """Best-effort check for p-adic fields across Sage versions.

    Tries method presence first, then falls back to string heuristics.
    """
    try:
        method = getattr(K, 'is_pAdicField', None)
        if callable(method):
            return bool(method())
    except Exception:
        pass
    try:
        s = str(K)
    except Exception:
        return False
    s_lower = s.lower()
    # Sage typically formats as "p-adic Field ..." or "<p>-adic Field ...".
    is_adic = ('p-adic' in s_lower) or (re.search(r"\b\d+-adic\b", s_lower) is not None)
    return is_adic and ('field' in s_lower)
