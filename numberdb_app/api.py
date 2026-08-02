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
import json
import yaml
from cysignals import AlarmInterrupt
from cysignals.alarm import alarm, cancel_alarm
from cysignals.signals import SignalError

from urllib.parse import quote_plus, unquote_plus

from sage.all import infinity
from sage.rings.all import ZZ, QQ, RR, CC, RIF, CIF
from sage.rings.all import RealField, RealIntervalField, RealBallField
from sage.rings.all import ComplexField, ComplexIntervalField, ComplexBallField
from utils.utils import is_pAdicField

from .eval_client import evaluate_search_program
from .throttle import batch_cost, charge, rate_limited
from .search import PAGE_SIZE, search_by_term, search_number

#: Numbers in one batched request. Bounded so that one caller cannot make the
#: server do unbounded work in a single round trip.
MAX_BATCH = 100
from .search import (search_complex_numbers, search_p_adic_numbers,
                     search_real_numbers)

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


@rate_limited
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
			#`results` is None on every error path (no expression given,
			#evaluator unreachable, ...). Iterating it raised TypeError, so those
			#paths returned 500 instead of a JSON error carrying `messages`.
			serializable_context = {
				'results': [
						{
							'index': result['param'],
							'number': result['number'].to_serializable_dict(),
							'table': result['table'].to_serializable_dict(),
						}
						for result in (context['results'] or [])
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
	
	
	#Evaluated in the sandboxed evaluator (see docs/design/eval-sandbox.md).
	#Numbers arrive as JSON records and are rebuilt through a fixed dispatch
	#table -- nothing from the evaluator is unpickled here.
	param_numbers, messages_eval = evaluate_search_program(program)

	messages += messages_eval
	if param_numbers == None:
		#Evaluator unreachable, or the expression was rejected/timed out.
		#messages_eval already explains it to the user.
		return wrap_response(None, messages)

	results = [];
	
	i = 0
	max_results = 100
	query_i = 0 
	query_bulk_size = 1 #Apparently, bulk_size doesn't really matter, and also as is, only query_bulk_size=1 yields correct param.
	query_real_intervals = []
	query_complex_intervals = []
	query_p_adic_numbers = []
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

		#Exactly-known values are searched on the real line, as a point
		#interval. They used to arrive as RIF because the wire format had no
		#representation for them and the sandbox coerced them; now that ZZ and
		#QQ survive the crossing, the dispatch below has to recognise them or
		#every integer search silently returns nothing.
		if K == ZZ or K == QQ:
			r = RIF(r)
			K = r.parent()

		if K == RIF:
			#Searching for real number up to given precision.
			#
			#Overlap, not containment: a stored value known to fewer digits
			#than the query can never sit inside it, so containment silently
			#missed exactly the numbers a precise query most wants. Ranked by
			#how much of each stored interval the query accounts for, and
			#short-circuited once a full page scores 1 -- see search.py.
			r_query = blur_real_interval(r)
			print("r_query:",r_query)
			query_real_intervals += search_real_numbers(r_query, max_results)
			query_i += 1

		elif K == CIF:
			#Searching for complex number up to given precision.
			#
			#Box overlap rather than a prefix of the Z-order searchstring. The
			#Z-order index only ever found cells *inside* the query, so a value
			#stored less precisely than the query -- an ancestor cell -- was
			#never returned, and two numbers a thousandth apart could share no
			#prefix at all when they straddled a cell boundary. Overlap is
			#symmetric and has no cells, so both go away.
			#
			#Costs about 0.2ms against 0.04ms for the prefix scan on 1849 rows;
			#a sequential scan, so if this table grows by orders of magnitude
			#it wants a GiST index on a box column.
			r_query = blur_complex_interval(r)
			print("r_query:",r_query)
			query_complex_intervals += search_complex_numbers(r_query, max_results)
			query_i += 1
		
		elif is_pAdicField(K):
			#Searching for a p-adic number.
			#
			#The query's precision is no longer capped. The cap existed because
			#only stored values *inside* the query were found, so a query more
			#precise than the stored value matched nothing and had to be blunted
			#first. It also ran the wrong way -- ceil(53*log(p,2)) grows with p,
			#allowing 123 digits at p=5 to express the 23 digits that 53 bits
			#actually need -- and it called ceil and log, which this module never
			#imported, so this branch raised NameError before it could search.
			#Coarser stored values are now found directly, so the query keeps the
			#precision the user gave it.
			number = NumberPAdic(sage_number = r)
			print("number_string:",number.number_string)
			query_p_adic_numbers += search_p_adic_numbers(
				number.number_string, max_results)
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
			query_real_intervals = []
			query_complex_intervals = []
			query_p_adic_numbers = []
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
	
@rate_limited
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
    
@rate_limited
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
    


@rate_limited
def lookup(request):
	"""Search for a number the caller already has.

	The counterpart to /api/search, which evaluates a Sage expression in the
	sandbox -- forking a process from a Sage-loaded parent, applying rlimits and
	validating an AST -- to compute a number the caller was holding all along.
	This one parses and queries, and is what a client should use unless it
	genuinely wants the server to compute something.

	Two ways to say what you are looking for:

	  ?number=<json>  a number record, as /api/search returns them. The client
	                  builds it from a value it already has.
	  ?text=<term>    the search bar's grammar: "3.14159", "1415", "Q5:1010",
	                  "1 + O(5^20)", "x^2-2".

	The response has the same shape as /api/search, so a client parses one
	format for both.
	"""
	time0 = time()

	def wrap_indexed(indexed, messages):
		"""Results that each say which of the asked numbers they answer."""
		return JsonResponse({
			'results': [
				{
					'index': index,
					'number': number.to_serializable_dict(),
					'table': number.table.to_serializable_dict(),
				}
				for index, number in indexed
			],
			'messages': messages,
			'time_request': '{:.3f}s'.format(time() - time0),
		}, safe=True)

	def wrap(results, messages):
		return JsonResponse({
			'results': [
				{
					'index': number.param_str(),
					'number': number.to_serializable_dict(),
					'table': number.table.to_serializable_dict(),
				}
				for number in results
			],
			'messages': messages,
			'time_request': '{:.3f}s'.format(time() - time0),
		}, safe=True)

	numbers_json = request.GET.get('numbers')
	number_json = request.GET.get('number')
	polynomial = request.GET.get('polynomial')
	polynomial_hash = request.GET.get('polynomial_hash')
	text = request.GET.get('text')

	if numbers_json:
		#A batch. Results are tagged with the index of the number they answer,
		#the same contract advanced search already uses for an expression that
		#produces several numbers -- so a client parses one shape for both.
		try:
			records = json.loads(numbers_json)
		except ValueError:
			return JsonResponse({'error': 'numbers is not valid JSON.'},
			                    safe=True)
		if not isinstance(records, list):
			return JsonResponse(
				{'error': 'numbers must be a list of number records.'},
				safe=True)
		if len(records) > MAX_BATCH:
			return JsonResponse(
				{'error': 'a batch may hold at most %d numbers; %d given.'
				          % (MAX_BATCH, len(records))}, safe=True)

		#Priced once the size is known: one unit for the request and half for
		#each number. The decorator has already taken the first.
		charge(request, batch_cost(len(records)) - 1)

		from utils.number_json import decode_number, UnsupportedNumber
		results, messages = [], []
		for index, record in enumerate(records):
			try:
				found = search_number(decode_number(record))
			except (UnsupportedNumber, TypeError, ValueError,
			        ArithmeticError) as error:
				messages.append({
					'tags': 'alert-warning',
					'text': 'number %d could not be read: %s' % (index, error),
				})
				continue
			results.extend((str(index), number) for number in found)
		return wrap_indexed(results[:PAGE_SIZE], messages)

	if number_json:
		try:
			record = json.loads(number_json)
		except ValueError:
			return JsonResponse({'error': 'number is not valid JSON.'},
			                    safe=True)
		try:
			from utils.number_json import decode_number, UnsupportedNumber
			value = decode_number(record)
		except UnsupportedNumber as error:
			return JsonResponse({'error': str(error)}, safe=True)
		except (TypeError, ValueError, ArithmeticError) as error:
			return JsonResponse({'error': 'could not read that number: %s'
			                              % (error,)}, safe=True)
		try:
			return wrap(search_number(value), [])
		except ValueError as error:
			return JsonResponse({'error': str(error)}, safe=True)

	if polynomial_hash:
		#A polynomial can be tens of thousands of characters -- the longest
		#stored is 58866 -- and nginx rejects a URL past 8k, so the largest
		#entries in the database could not be asked about at all. The client
		#computes the same canonical key and sends a digest of it.
		#
		#Sound only because one canonicalisation defines the key, in plain
		#Python, shipped to both sides. 128 bits, because unlike the server's
		#own query this has no full key to cross-check against.
		from .models import Polynomial
		found = list(Polynomial.objects.filter(
			canonical_hash=polynomial_hash.strip().lower())[:PAGE_SIZE])
		return wrap(found, [])

	if polynomial:
		#Its own parameter rather than going through text=, because the two
		#are asking different questions.
		#
		#A typed search term is ambiguous: it might be a number, a table
		#title, a tag. Since polynomials are canonicalised under renaming of
		#variables, a single-term polynomial would match any word at all --
		#every search for "prime" would return the polynomial x. The search
		#bar therefore ignores polynomials of fewer than two terms, on
		#purpose.
		#
		#Here the caller has said the text *is* a polynomial, so there is no
		#ambiguity to guard against and single terms are searched.
		from utils.utils import parse_polynomial
		try:
			parsed = parse_polynomial(polynomial)
		except Exception:
			parsed = None
		if parsed is None:
			return JsonResponse(
				{'error': 'could not read that polynomial.'}, safe=True)
		return wrap(search_number(parsed), [])

	if text:
		groups = search_by_term(text)
		found = [number for group in groups for number in group['numbers']]
		messages = []
		if len(found) >= PAGE_SIZE:
			messages.append({
				'tags': 'alert-warning',
				'text': 'We only show the first %s results.' % (PAGE_SIZE,),
			})
		return wrap(found[:PAGE_SIZE], messages)

	return JsonResponse(
		{'error': 'Give number=<json record>, numbers=<json list>, '
		          'polynomial=<text>, polynomial_hash=<digest>, or '
		          'text=<search term>.'},
		safe=True)
