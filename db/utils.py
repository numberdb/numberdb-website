from sage import *
from sage.rings.all import *
from sage.misc.flatten import flatten

RIFprec = RealIntervalField(1000)
RBFprec = RealBallField(1000)

def to_bytes(m):
    if isinstance(m,bytes):
        return m
    if isinstance(m,memoryview):
        return m.tobytes()

def my_real_interval_to_string(r):

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

def number_param_groups_to_bytes(param):
    p = ",".join(flatten(param))
    p = bytes(p,encoding='cp437')
    return p

def number_param_groups_to_string(param):
    return number_param_groups_to_bytes(param).decode()
