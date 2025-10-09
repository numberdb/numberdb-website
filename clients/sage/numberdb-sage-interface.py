'''
Attempt to communicate with NumberDB within SageMath.
'''

import requests
import json
from urllib.parse import quote_plus

from sage.all import infinity
from sage.rings.all import ZZ, QQ, RR, CC, RIF, CIF
from sage.rings.all import RealField, RealIntervalField, RealBallField
from sage.rings.all import ComplexField, ComplexIntervalField, ComplexBallField

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
            'sage': loads(bytes(result['number']['sage'], encoding='cp437')),
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
