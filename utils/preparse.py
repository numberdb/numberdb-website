import os
import re
import six

#from sage.repl.load import load_wrap

from sage.repl.preparse import preparse_generators, strip_prompts, strip_string_literals, preparse_calculus

implicit_mul_level = False
numeric_literal_prefix = '_sage_const_'

def implicit_multiplication(level=None):
    """
    Turns implicit multiplication on or off, optionally setting a
    specific ``level``.  Returns the current ``level`` if no argument
    is given.

    INPUT:

    - ``level`` - an integer (default: None); see :func:`implicit_mul`
      for a list

    EXAMPLES::

      sage: implicit_multiplication(True)
      sage: implicit_multiplication()
      5
      sage: preparse('2x')
      'Integer(2)*x'
      sage: implicit_multiplication(False)
      sage: preparse('2x')
      '2x'
    """
    global implicit_mul_level
    if level is None:
        return implicit_mul_level
    elif level is True:
        implicit_mul_level = 5
    else:
        implicit_mul_level = level

def isalphadigit_(s):
    """
    Return ``True`` if ``s`` is a non-empty string of alphabetic characters
    or a non-empty string of digits or just a single ``_``

    EXAMPLES::

        sage: from sage.repl.preparse import isalphadigit_
        sage: isalphadigit_('abc')
        True
        sage: isalphadigit_('123')
        True
        sage: isalphadigit_('_')
        True
        sage: isalphadigit_('a123')
        False
    """
    return s.isalpha() or s.isdigit() or s == "_"

keywords = """
and       del       from      not       while
as        elif      global    or        with
assert    else      if        pass      yield
break     except    import    print
class     exec      in        raise
continue  finally   is        return
def       for       lambda    try
""".split()

in_single_quote = False
in_double_quote = False
in_triple_quote = False

def in_quote():
    return in_single_quote or in_double_quote or in_triple_quote


def containing_block(code, idx, delimiters=['()','[]','{}'], require_delim=True):
    """
    Find the code block given by balanced delimiters that contains the position ``idx``.

    INPUT:

    - ``code`` - a string

    - ``idx`` - an integer; a starting position

    - ``delimiters`` - a list of strings (default: ['()', '[]',
      '{}']); the delimiters to balance. A delimiter must be a single
      character and no character can at the same time be opening and
      closing delimiter.

    - ``require_delim`` - a boolean (default: True); whether to raise
      a SyntaxError if delimiters are present. If the delimiters are
      unbalanced, an error will be raised in any case.

    OUTPUT:

    - a 2-tuple ``(a,b)`` of integers, such that ``code[a:b]`` is
      delimited by balanced delimiters, ``a<=idx<b``, and ``a``
      is maximal and ``b`` is minimal with that property. If that
      does not exist, a ``SyntaxError`` is raised.

    - If ``require_delim`` is false and ``a,b`` as above can not be
      found, then ``0, len(code)`` is returned.

    EXAMPLES::

        sage: from sage.repl.preparse import containing_block
        sage: s = "factor(next_prime(L[5]+1))"
        sage: s[22]
        '+'
        sage: start, end = containing_block(s, 22)
        sage: start, end
        (17, 25)
        sage: s[start:end]
        '(L[5]+1)'
        sage: s[20]
        '5'
        sage: start, end = containing_block(s, 20); s[start:end]
        '[5]'
        sage: start, end = containing_block(s, 20, delimiters=['()']); s[start:end]
        '(L[5]+1)'
        sage: start, end = containing_block(s, 10); s[start:end]
        '(next_prime(L[5]+1))'

    TESTS::

        sage: containing_block('((a{))',0)
        Traceback (most recent call last):
        ...
        SyntaxError: Unbalanced delimiters
        sage: containing_block('((a{))',1)
        Traceback (most recent call last):
        ...
        SyntaxError: Unbalanced delimiters
        sage: containing_block('((a{))',2)
        Traceback (most recent call last):
        ...
        SyntaxError: Unbalanced delimiters
        sage: containing_block('((a{))',3)
        Traceback (most recent call last):
        ...
        SyntaxError: Unbalanced delimiters
        sage: containing_block('((a{))',4)
        Traceback (most recent call last):
        ...
        SyntaxError: Unbalanced delimiters
        sage: containing_block('((a{))',5)
        Traceback (most recent call last):
        ...
        SyntaxError: Unbalanced delimiters
        sage: containing_block('(()()',1)
        (1, 3)
        sage: containing_block('(()()',3)
        (3, 5)
        sage: containing_block('(()()',4)
        (3, 5)
        sage: containing_block('(()()',0)
        Traceback (most recent call last):
        ...
        SyntaxError: Unbalanced delimiters
        sage: containing_block('(()()',0, require_delim=False)
        (0, 5)
        sage: containing_block('((})()',1, require_delim=False)
        (0, 6)
        sage: containing_block('abc',1, require_delim=False)
        (0, 3)

    """
    openings = "".join([d[0] for d in delimiters])
    closings = "".join([d[-1] for d in delimiters])
    levels = [0] * len(openings)
    p = 0
    start = idx
    while start >= 0:
        if code[start] in openings:
            p = openings.index(code[start])
            levels[p] -= 1
            if levels[p] == -1:
                break
        elif code[start] in closings and start < idx:
            p = closings.index(code[start])
            levels[p] += 1
        start -= 1
    if start == -1:
        if require_delim:
            raise SyntaxError("Unbalanced or missing delimiters")
        else:
            return 0, len(code)
    if levels.count(0) != len(levels)-1:
        if require_delim:
            raise SyntaxError("Unbalanced delimiters")
        else:
            return 0, len(code)
    p0 = p
    # We now have levels[p0]==-1. We go to the right hand side
    # till we find a closing delimiter of type p0 that makes
    # levels[p0]==0.
    end = idx
    while end < len(code):
        if code[end] in closings:
            p = closings.index(code[end])
            levels[p] += 1
            if p==p0 and levels[p] == 0:
                break
        elif code[end] in openings and end > idx:
            p = openings.index(code[end])
            levels[p] -= 1
        end += 1
    if levels.count(0) != len(levels):
        # This also occurs when end==len(code) without finding a closing delimiter
        if require_delim:
            raise SyntaxError("Unbalanced delimiters")
        else:
            return 0, len(code)
    return start, end+1


def parse_ellipsis(code, preparse_step=True):
    """
    Preparses [0,2,..,n] notation.

    INPUT:

    - ``code`` - a string

    - ``preparse_step`` - a boolean (default: True)

    OUTPUT:

    - a string

    EXAMPLES::

        sage: from sage.repl.preparse import parse_ellipsis
        sage: parse_ellipsis("[1,2,..,n]")
        '(ellipsis_range(1,2,Ellipsis,n))'
        sage: parse_ellipsis("for i in (f(x) .. L[10]):")
        'for i in (ellipsis_iter(f(x) ,Ellipsis, L[10])):'
        sage: [1.0..2.0]
        [1.00000000000000, 2.00000000000000]

    TESTS:

    Check that nested ellipsis is processed correctly (:trac:`17378`)::

        sage: preparse('[1,..,2,..,len([1..3])]')
        '(ellipsis_range(Integer(1),Ellipsis,Integer(2),Ellipsis,len((ellipsis_range(Integer(1),Ellipsis,Integer(3))))))'

    """
    ix = code.find('..')
    while ix != -1:
        if ix == 0:
            raise SyntaxError("Cannot start line with ellipsis.")
        elif code[ix-1]=='.':
            # '...' be valid Python in index slices
            code = code[:ix-1] + "Ellipsis" + code[ix+2:]
        elif len(code) >= ix+3 and code[ix+2]=='.':
            # '...' be valid Python in index slices
            code = code[:ix] + "Ellipsis" + code[ix+3:]
        else:
            start_list, end_list = containing_block(code, ix, ['()','[]'])

            #search the current containing block for other '..' occurrences that may
            #be contained in proper subblocks. Those need to be processed before
            #we can deal with the present level of ellipses.
            ix = code.find('..',ix+2,end_list)
            while ix != -1:
                if code[ix-1]!='.' and code[ix+2]!='.':
                    start_list,end_list = containing_block(code,ix,['()','[]'])
                ix = code.find('..',ix+2,end_list)

            arguments = code[start_list+1:end_list-1].replace('...', ',Ellipsis,').replace('..', ',Ellipsis,')
            arguments = re.sub(r',\s*,', ',', arguments)
            if preparse_step:
                arguments = arguments.replace(';', ', step=')
            range_or_iter = 'range' if code[start_list]=='[' else 'iter'
            code = "%s(ellipsis_%s(%s))%s" %  (code[:start_list],
                                               range_or_iter,
                                               arguments,
                                               code[end_list:])
        ix = code.find('..')
    return code

def extract_numeric_literals(code):
    """
    Pulls out numeric literals and assigns them to global variables.
    This eliminates the need to re-parse and create the literals,
    e.g., during every iteration of a loop.

    INPUT:

    - ``code`` - a string; a block of code

    OUTPUT:

    - a (string, string:string dictionary) 2-tuple; the block with
      literals replaced by variable names and a mapping from names to
      the new variables

    EXAMPLES::

        sage: from sage.repl.preparse import extract_numeric_literals
        sage: code, nums = extract_numeric_literals("1.2 + 5")
        sage: print(code)
        _sage_const_1p2  + _sage_const_5
        sage: print(nums)
        {'_sage_const_1p2': "RealNumber('1.2')", '_sage_const_5': 'Integer(5)'}

        sage: extract_numeric_literals("[1, 1.1, 1e1, -1e-1, 1.]")[0]
        '[_sage_const_1 , _sage_const_1p1 , _sage_const_1e1 , -_sage_const_1en1 , _sage_const_1p ]'

        sage: extract_numeric_literals("[1.sqrt(), 1.2.sqrt(), 1r, 1.2r, R.1, R0.1, (1..5)]")[0]
        '[_sage_const_1 .sqrt(), _sage_const_1p2 .sqrt(), 1 , 1.2 , R.1, R0.1, (_sage_const_1 .._sage_const_5 )]'
    """
    return preparse_numeric_literals(code, True)

all_num_regex = None

def preparse_numeric_literals(code, extract=False):
    """
    This preparses numerical literals into their Sage counterparts,
    e.g. Integer, RealNumber, and ComplexNumber.

    INPUT:

    - ``code`` - a string; a code block to preparse

    - ``extract`` - a boolean (default: False); whether to create
      names for the literals and return a dictionary of
      name-construction pairs

    OUTPUT:

    - a string or (string, string:string dictionary) 2-tuple; the
      preparsed block and, if ``extract`` is True, the
      name-construction mapping

    EXAMPLES::

        sage: from sage.repl.preparse import preparse_numeric_literals
        sage: preparse_numeric_literals("5")
        'Integer(5)'
        sage: preparse_numeric_literals("5j")
        "ComplexNumber(0, '5')"
        sage: preparse_numeric_literals("5jr")
        '5J'
        sage: preparse_numeric_literals("5l")
        '5l'
        sage: preparse_numeric_literals("5L")
        '5L'
        sage: preparse_numeric_literals("1.5")
        "RealNumber('1.5')"
        sage: preparse_numeric_literals("1.5j")
        "ComplexNumber(0, '1.5')"
        sage: preparse_numeric_literals(".5j")
        "ComplexNumber(0, '.5')"
        sage: preparse_numeric_literals("5e9j")
        "ComplexNumber(0, '5e9')"
        sage: preparse_numeric_literals("5.")
        "RealNumber('5.')"
        sage: preparse_numeric_literals("5.j")
        "ComplexNumber(0, '5.')"
        sage: preparse_numeric_literals("5.foo()")
        'Integer(5).foo()'
        sage: preparse_numeric_literals("5.5.foo()")
        "RealNumber('5.5').foo()"
        sage: preparse_numeric_literals("5.5j.foo()")
        "ComplexNumber(0, '5.5').foo()"
        sage: preparse_numeric_literals("5j.foo()")
        "ComplexNumber(0, '5').foo()"
        sage: preparse_numeric_literals("1.exp()")
        'Integer(1).exp()'
        sage: preparse_numeric_literals("1e+10")
        "RealNumber('1e+10')"
        sage: preparse_numeric_literals("0x0af")
        'Integer(0x0af)'
        sage: preparse_numeric_literals("0x10.sqrt()")
        'Integer(0x10).sqrt()'
        sage: preparse_numeric_literals('0o100')
        'Integer(0o100)'
        sage: preparse_numeric_literals('0b111001')
        'Integer(0b111001)'
        sage: preparse_numeric_literals('0xe')
        'Integer(0xe)'
        sage: preparse_numeric_literals('0xEAR')
        '0xEA'
        sage: preparse_numeric_literals('0x1012Fae')
        'Integer(0x1012Fae)'
    """
    literals = {}
    last = 0
    new_code = []

    global all_num_regex
    if all_num_regex is None:
        dec_num = r"\b\d+"
        hex_num = r"\b0x[0-9a-f]+"
        oct_num = r"\b0o[0-7]+"
        bin_num = r"\b0b[01]+"
        # This is slightly annoying as floating point numbers may start
        # with a decimal point, but if they do the \b will not match.
        float_num = r"((\b\d+([.]\d*)?)|([.]\d+))(e[-+]?\d+)?"
        all_num = r"((%s)|(%s)|(%s)|(%s)|(%s))(rj|rL|jr|Lr|j|L|r|)\b" % (hex_num, oct_num, bin_num, float_num, dec_num)
        all_num_regex = re.compile(all_num, re.I)

    for m in all_num_regex.finditer(code):
        start, end = m.start(), m.end()
        num = m.group(1)
        postfix = m.groups()[-1].upper()

        if 'R' in postfix:
            if not six.PY2:
                postfix = postfix.replace('L', '')
            num_name = num_make = num + postfix.replace('R', '')
        elif 'L' in postfix:
            if six.PY2:
                continue
            else:
                num_name = num_make = num + postfix.replace('L', '')
        else:

            # The Sage preparser does extra things with numbers, which we need to handle here.
            if '.' in num:
                if start > 0 and num[0] == '.':
                    if code[start-1] == '.':
                        # handle Ellipsis
                        start += 1
                        num = num[1:]
                    elif re.match(r'[a-zA-Z0-9_\])]', code[start-1]):
                        # handle R.0
                        continue
                elif end < len(code) and num[-1] == '.':
                    if re.match('[a-zA-Z_]', code[end]):
                        # handle 4.sqrt()
                        end -= 1
                        num = num[:-1]
            elif end < len(code) and code[end] == '.' and not postfix and re.match(r'\d+$', num):
                # \b does not match after the . for floating point
                # two dots in a row would be an ellipsis
                if end+1 == len(code) or code[end+1] != '.':
                    end += 1
                    num += '.'

            num_name = numeric_literal_prefix + num.replace('.', 'p').replace('-', 'n').replace('+', '')

            if 'J' in postfix:
                num_make = "ComplexNumber(0, '%s')" % num
                num_name += 'j'
            elif len(num) < 2 or num[1] in 'oObBxX':
                num_make = "Integer(%s)" % num
            elif '.' in num or 'e' in num or 'E' in num:
                num_make = "RealNumber('%s')" % num
            elif num[0] == "0":
                num_make = "Integer('%s')" % num
            else:
                num_make = "Integer(%s)" % num

            literals[num_name] = num_make

        new_code.append(code[last:start])
        if extract:
            new_code.append(num_name+' ')
        else:
            new_code.append(num_make)
        last = end

    new_code.append(code[last:])
    code = ''.join(new_code)
    if extract:
        return code, literals
    else:
        return code


quote_state = None

def preparse(line, reset=True, do_time=False, ignore_prompts=False,
             numeric_literals=True):
    r"""
    Preparses a line of input.
    The code is taken from sage.repl.preparse and modified to increase
    numerical stability.

    INPUT:

    - ``line`` - a string

    - ``reset`` - a boolean (default: True)

    - ``do_time`` - a boolean (default: False)

    - ``ignore_prompts`` - a boolean (default: False)

    - ``numeric_literals`` - a boolean (default: True)

    OUTPUT:

    - a string
    """
    global quote_state
    if reset:
        quote_state = None

    L = line.lstrip()
    if len(L) > 0 and L[0] in ['#', '!']:
        return line

    if L.startswith('...'):
        i = line.find('...')
        return line[:i+3] + preparse(line[i+3:], reset=reset, do_time=do_time, ignore_prompts=ignore_prompts)

    if ignore_prompts:
        # Get rid of leading sage: and >>> so that pasting of examples from
        # the documentation works.
        line = strip_prompts(line)

    # This part handles lines with semi-colons all at once
    # Then can also handle multiple lines more efficiently, but
    # that optimization can be done later.
    L, literals, quote_state = strip_string_literals(line, quote_state)

    # Ellipsis Range
    # [1..n]
    try:
        L = parse_ellipsis(L, preparse_step=False)
    except SyntaxError:
        pass

    if implicit_mul_level:
        # Implicit Multiplication
        # 2x -> 2*x
        L = implicit_mul(L, level = implicit_mul_level)

    if numeric_literals:
        # Wrapping
        # 1 + 0.5 -> Integer(1) + RealNumber('0.5')
        L = preparse_numeric_literals(L)

    # Generators
    # R.0 -> R.gen(0)
    L = re.sub(r'([_a-zA-Z]\w*|[)\]])\.(\d+)', r'\1.gen(\2)', L)

    # Use ^ for exponentiation and ^^ for xor
    # (A side effect is that **** becomes xor as well.)
    L = L.replace('^', '**').replace('****', '^')

    # Make it easy to match statement ends
    L = ';%s;' % L.replace('\n', ';\n;')

    if do_time:
        # Separate time statement
        L = re.sub(r';(\s*)time +(\w)', r';time;\1\2', L)

    # Construction with generators
    # R.<...> = obj()
    # R.<...> = R[]
    L = preparse_generators(L)

    # Calculus functions
    # f(x,y) = x^3 - sin(y)
    L = preparse_calculus(L)

    # Backslash
    L = re.sub(r'''\\\s*([^\t ;#])''', r' * BackslashOperator() * \1', L)

    if do_time:
        # Time keyword
        L = re.sub(r';time;(\s*)(\S[^;]*)',
                   r';\1__time__=misc.cputime(); __wall__=misc.walltime(); \2; print(' +
                        '"Time: CPU %%.2f s, Wall: %%.2f s"%%(misc.cputime(__time__), misc.walltime(__wall__)))',
                   L)

    # Remove extra ;'s
    L = L.replace(';\n;', '\n')[1:-1]

    line = L % literals

    return line

