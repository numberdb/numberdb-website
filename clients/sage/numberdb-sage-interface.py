'''
Communicate with NumberDB from within SageMath.
'''

import requests
import json
from urllib.parse import quote_plus

from sage.all import infinity
from sage.rings.all import ZZ, QQ, RR, CC, RIF, CIF, Qp, RBF, PolynomialRing
from sage.rings.all import RealField, RealIntervalField, RealBallField
from sage.rings.all import ComplexField, ComplexIntervalField, ComplexBallField


class UnsupportedNumber(Exception):
    '''Raised for a number this client has no rule for.'''


def _rational(text):
    '''Interval endpoints travel as exact p/q, so they do not drift.'''
    try:
        return QQ(text)
    except (TypeError, ValueError):
        return RIF(text).lower()


def _decode_RIF(record):
    return RIF(_rational(record['lower']), _rational(record['upper']))


def _decode_CIF(record):
    return CIF(RIF(_rational(record['re_lower']), _rational(record['re_upper'])),
               RIF(_rational(record['im_lower']), _rational(record['im_upper'])))


def _decode_ZZ(record):
    return ZZ(record['value'])


def _decode_QQ(record):
    return QQ(record['value'])


def _decode_RBF(record):
    return RBF(RIF(_rational(record['lower']), _rational(record['upper'])))


def _decode_Qp(record):
    precision = int(record['precision'])
    return Qp(int(record['prime']), prec=max(precision, 1))(ZZ(record['lift']))


def _decode_polynomial(record):
    ring = PolynomialRing(QQ, max(int(record['variables']), 1), 'x')
    return ring(record['value'])


#: Fixed table. Decoding dispatches on a tag this file knows, never on a name
#: taken from the response, so a reply can only produce one of these types.
_DECODERS = {
    'RIF': _decode_RIF,
    'CIF': _decode_CIF,
    'ZZ': _decode_ZZ,
    'QQ': _decode_QQ,
    'RBF': _decode_RBF,
    'Qp': _decode_Qp,
    'polynomial': _decode_polynomial,
}


def decode_number(record):
    '''Rebuild a Sage number from the server's JSON.

    This replaces ``loads(...)`` on a Sage pickle. Unpickling runs whatever the
    bytes say, so the old client executed code chosen by whoever answered the
    request -- the server, anyone who had compromised it, or anyone able to
    reply in its place. Nothing here can do more than construct one of the
    number types above.
    '''
    if not isinstance(record, dict):
        raise UnsupportedNumber('number record must be an object')
    decoder = _DECODERS.get(record.get('kind'))
    if decoder is None:
        raise UnsupportedNumber('unknown number kind %r' % (record.get('kind'),))
    return decoder(record)

_domain = 'https://numberdb.org/'
#_domain = 'http://localhost:8000/' #only for development


def search(expression):
    '''
    Perform an advanced search on numberdb.org for the given expression.
    
    INPUT:
    expression - A string as accepted by numberdb.org/advanced-search.
    
    OUTPUT: 
    results - a list of search results, each of which is a dict that
               includes a sage object ('sage'),
               the exact value as text ('exact_text'),
               a short form ('str_short'),
               some table meta data ('table'),
               and the parameter of this entry in the table ('param').
    messages - a list of messages, each of which is a dict that
               includes a message text ('text') and 
               css classes ('tags').
    
    '''
    
    url = _domain + 'api/search?expression=%s' % (
        quote_plus(expression),
    )
    response = requests.get(url, allow_redirects=True)
    #print('response.text:',response.text)
    context = response.json()
    
    results = context['results']
    messages = context['messages']
    time_request = context['time_request']
    
    results = [
		{
            'index': result['index'],
            'sage': decode_number(result['number']['number']),
            'exact_text': result['number'].get('exact_text', ''),
            'type': result['number']['type'],
            'str_short': result['number']['str_short'],
            'param_in_table': result['number']['param'],				
			'table': result['table'],
        }
        for result in results
    ]
    
    return results, messages

def table(table_id):
    '''
    Returns NumberDB's table (in essentially raw format) with given table_id.
    
    INPUT:
    table_id - either a non-negative integer, or a string of the form
                'Tx', where x is this non-negative integer
                
    OUTPUT:
    the table as a dictionary 
    '''
    
    url = _domain + 'api/table?id=%s' % (table_id,)
    response = requests.get(url, allow_redirects=True)
    #print('response.text:',response.text)
    result = response.json()
    
    return result

def tag(name):
    '''
    Returns NumberDB's tag information for given tag name.
    
    INPUT:
    name - name of the tag (string)
                
    OUTPUT:
    the list of tables tagged by the tag 
    '''
    
    url = _domain + 'api/tag?url=%s' % (
        quote_plus(name),
    )
    response = requests.get(url, allow_redirects=True)
    #print('response.text:',response.text)
    result = response.json()
    
    return result
