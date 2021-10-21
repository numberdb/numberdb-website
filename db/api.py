from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.views import generic
from django.http import JsonResponse
from django.contrib import messages
from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector
from django.db.models import F
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings

import numpy as np
from numpy import random as random
import re
from time import time
#import os
import yaml
from cysignals import AlarmInterrupt
from cysignals.alarm import alarm, cancel_alarm
from cysignals.signals import SignalError

import Pyro5.api
import Pyro5.errors

from urllib.parse import quote_plus, unquote_plus

from sage.all import *

from mpmath import pslq

from .models import UserProfile
from .models import Table
from .models import TableData
from .models import TableSearch
from .models import Contributor
from .models import Tag
from .models import Number
from .models import NumberPAdic
from .models import NumberComplex
from .models import Polynomial
from .models import OeisNumber
from .models import OeisSequence
from .models import WikipediaNumber

from utils.utils import pluralize
from utils.utils import number_param_groups_to_string
from utils.utils import to_bytes
from utils.utils import real_interval_to_string_via_endpoints
from utils.utils import factor_with_timeout
from utils.utils import StableContinuedFraction
from utils.utils import parse_integer
from utils.utils import parse_rational_number
from utils.utils import parse_positive_integer
from utils.utils import parse_real_interval
from utils.utils import parse_fractional_part
from utils.utils import parse_p_adic
from utils.utils import parse_complex_interval
from utils.utils import parse_polynomial
from utils.utils import blur_real_interval
from utils.utils import blur_complex_interval
from utils.utils import is_polynomial_ring

from db_builder.utils import normalize_table_data


def advanced_search_results(request, return_type='json'):
	time0 = time()
	
	def wrap_response(results, messages = None):
		context = {
			'results': results,
			'messages': messages,
			'time_request': "{:.3f}s".format(time()-time0),
		}
		'''
		messages_html = render_to_string(
			'includes/messaging.html',
			context = context,
		)
		result_html = render_to_string(
			'includes/advanced-search-results.html', 
			context = context,
		)
		data = {
			'messages_html': messages_html,
			'result_html': result_html,
			'time_request': "{:.3f}s".format(time()-time0),
		}
		#print("data:",data)
		'''
		print('context:',context)
		if return_type == 'json':
			serializable_context = {
				'results': [
						{
							'index': result['param'],
							'number': result['number'].to_serializable_dict(),				
							'table': result['table'].to_serializable_dict(),
						}
						for result in context['results']
					],
				'messages': context['messages'],
				'time_request': context['time_request'],			
			}
			return JsonResponse(serializable_context,safe=True)
		elif return_type == 'dict':
			return context
		else:
			raise ValueError('Unknown return_type "%s".' % (return_type,))
		
	messages = []

	'''
	if not request.user.is_authenticated:	
		print("not authenticated")
		messages.append({
			'tags': 'alert-danger',
			'text': 'You need to be logged in to use advanced search.',
		})
		return wrap_response(None, messages)
	'''

	program = request.GET.get('expression',default=None)
	if program == None:
		return wrap_response(None, messages)
	print('program:',program)
	
	
	try:
		E = Pyro5.api.Proxy("PYRONAME:safe_eval")
		#print("E:",E)
		param_numbers, messages_eval = loads(bytes(E.eval_search_program(program), encoding='cp437'))
		print("messages_eval:",messages_eval)
	
	except (Pyro5.errors.NamingError,Pyro5.errors.CommunicationError) as e:
		print("e:",e, type(e))
		#print("error:",error)
		messages.append({
			'tags': 'alert-danger',
			'text': 'Error: The advanced search server is currently not running and has to be restarted. We apologize.',
		})
		return wrap_response(None, messages)
				

	if param_numbers == None:
		param_numbers = []
	messages += messages_eval

	results = [];
	
	i = 0
	max_results = 100
	query_i = 0 
	query_bulk_size = 1 #Apparently, bulk_size doesn't really matter, and also as is, only query_bulk_size=1 yields correct param.
	query_real_intervals = Number.objects.none()
	query_complex_intervals = NumberComplex.objects.none()
	query_p_adic_numbers = NumberPAdic.objects.none()
	query_polynomials = Polynomial.objects.none()

	def do_query():
		nonlocal i
		nonlocal param
		
		for number in query_real_intervals[:(max_results - i)]:
			results.append({
				'param': param,
				'number': number,
				'table': number.table,		
			})
			i += 1
			if i >= max_results:
				return

		for number in query_complex_intervals[:(max_results - i)]:
			results.append({
				'param': param,
				'number': number,
				'table': number.table,		
			})
			i += 1
			if i >= max_results:
				return

		for number in query_p_adic_numbers[:(max_results - i)]:
			print("result:",number.number_string)
			results.append({
				'param': param,
				'number': number,
				'table': number.table,		
			})
			i += 1
			if i >= max_results:
				return

		for polynomial in query_polynomials[:(max_results - i)]:
			print("result:",polynomial.number_string)
			results.append({
				'param': param,
				'number': polynomial,
				'table': polynomial.table,		
			})
			i += 1
			if i >= max_results:
				return
	
	for param, r in param_numbers:
		
		K = r.parent()
		if K == RIF:
			#Searching for real number up to given precision:
			r_query = blur_real_interval(r)
			print("r_query:",r_query)
			query_real_intervals |= Number.objects.filter(
				lower__range = (float(r_query.lower()),float(r_query.upper())),
				upper__range = (float(r_query.lower()),float(r_query.upper())),							
			) #Request maximum number of results?
			query_i += 1

		elif K == CIF:
			#Searching for complex number up to given precision:
			r_query = blur_complex_interval(r)
			print("r_query:",r_query)
			number = NumberComplex(sage_number = r_query)
			query_complex_intervals |= NumberComplex.objects.filter(
				number_searchstring__startswith = number.number_searchstring,							
			) #Request maximum number of results?
			query_i += 1
		
		elif is_pAdicField(K):
			#Searching for p-adic number up to given precision:
			#Cap precision to around 53 bits: (Numbers in DB might not be as precise as the given r.)
			r_query = r.add_bigoh(r.valuation() + ceil(53*log(K.prime(),2)))
			number = NumberPAdic(sage_number = r_query)
			print("number_string:",number.number_string)
			query_p_adic_numbers |= NumberPAdic.objects.filter(
				number_string__startswith = number.number_string,							
			) #Request maximum number of results?
			query_i += 1

		elif is_polynomial_ring(K):
			r_query = r
			polynomial = Polynomial(sage_polynomial = r_query)
			print("number_string:",polynomial.number_string)
			query_polynomials |= Polynomial.objects.filter(
				number_string_hash = polynomial.number_string_hash,							
				number_string = polynomial.number_string,							
			) #Request maximum number of results?
			query_i += 1

		if query_i >= query_bulk_size:
			do_query()
			query_real_intervals = Number.objects.none()
			query_complex_intervals = NumberComplex.objects.none()
			query_p_adic_numbers = NumberPAdic.objects.none()
			query_polynomials = Polynomial.objects.none()
			query_i = 0
			
		if i >= max_results:
			messages.append({
				'tags': 'alert-warning',
				'text': 'We only show the first %s results.' % (max_results,),
			})
			break
			
	do_query()
	
	return wrap_response(results,messages)
	
def table(request):
	tid = request.GET.get('id',default=None)
	url = request.GET.get('url',default=None)

	if tid != None:
		try:
			tid_int = int(tid.lstrip('tT'))
			table = Table.objects.get(tid_int=tid_int)
		except Table.DoesNotExist:
			return JsonResponse({'error':"Table with id '%s' does not exist." % (tid,)},safe=True)
	elif url != None:
		try:
			table = Table.objects.get(url=url)
		except Table.DoesNotExist:
			return JsonResponse({'error':"Table with url '%s' does not exist." % (url,)},safe=True)
	else:
		return JsonResponse({'error':'No id or url given.'},safe=True)
		
	result = table.data.json

	return JsonResponse(result,safe=True)
    
def tag(request):
	url = request.GET.get('url',default=None)
	if url != None:
		try:
			tag = Tag.from_url(url)
		except Tag.DoesNotExist:
			return JsonResponse({'error':"Tag with url '%s' does not exist." % (url,)},safe=True)
	else:
		return JsonResponse({'error':'No url given.'},safe=True)

	sortby_default = 'number_count'
	sortby = request.GET.get('sort_by',default=sortby_default)
	if sortby == 'number_count':
		order_tables_by = '-number_count'
	elif sortby == 'id':
		order_tables_by = 'tid_int'
	elif sortby == 'title':
		order_tables_by = 'title_lowercase'
	else:
		order_tables_by = sortby_default
	result = tag.to_serializable_dict(order_tables_by=order_tables_by)

	return JsonResponse(result,safe=True)
    
