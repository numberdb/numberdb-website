'''
Attepmt to communicate with NumberDB within SageMath.
'''

import requests
import json

from sage.all import *
from sage.rings.all import *

#domain = 'https://numberdb.org/'
domain = 'http://localhost:8000/'


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
    
    url = _domain + 'advanced-search-results?expression=%s' % (expression,)
    r = requests.get(url, allow_redirects=True)
    context = r.json()
    
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
