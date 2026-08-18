from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.views import generic
from django.http import JsonResponse
from django.contrib import messages
from django.db.models import F
from django.template.loader import render_to_string
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.conf import settings
#Key-authenticated writes carry no cookie, so there is no session for a
#third-party page to ride on; the CSRF check has nothing to protect here
#and would only reject every program that is doing the right thing.
from django.db import connection, transaction
from django.db.utils import OperationalError
from django.views.decorators.csrf import csrf_exempt

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
from .search import PAGE_SIZE, search_by_term, search_metadata, search_number

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

from data_pipeline.utils import normalize_table_data


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
	
def _may_see_draft(request, table):
	"""Whether the key on this request belongs to somebody who may see a draft.

	Read-only, and deliberately narrow: it answers the same question the site
	answers for a signed-in person, and it answers `False` for a request with
	no key at all rather than raising, so an ordinary public read is unchanged.
	"""
	from .models import ApiKey
	from .throttle import _bearer_token

	token = _bearer_token(request)
	if not token:
		return False
	key = ApiKey.authenticate(token)
	if key is None or not getattr(key, 'user', None):
		return False
	from .editing import may_see

	return may_see(table, key.user)


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
		
	#A draft answers nothing here either: the API is as public as the site,
	#and as private. The site lets a draft's author and the board see it, so a
	#request carrying their key sees it too -- otherwise a generator can
	#create a draft through this API and then be unable to fill it, which is
	#exactly the workflow drafts exist for.
	if not table.published and not _may_see_draft(request, table):
		return JsonResponse(
			{'error': "Table with id '%s' does not exist." % (table.tid,)},
			safe=True)

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

	def wrap(results, messages, tags=(), tables=()):
		#Tags and tables are described briefly rather than serialised whole: a
		#search result is a signpost, and a client that wants the contents can
		#ask /api/table or /api/tag for them.
		return JsonResponse({
			'results': [
				{
					'index': number.param_str(),
					'number': number.to_serializable_dict(),
					'table': number.table.to_serializable_dict(),
				}
				for number in results
			],
			'tags': [
				{
					'name': tag.name,
					'url': tag.url(),
					'table_count': tag.table_count,
					'number_count': tag.number_count,
				}
				for tag in tags
			],
			'tables': [
				{
					'tid': table.tid,
					'title': table.title,
					'url': table.url,
					'number_count': table.number_count,
				}
				for table in tables
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
		#Words as well as digits, which is what the search bar has always done
		#and this endpoint did not: a term naming a subject found nothing here
		#while the dropdown over the same box found the table.
		tags, tables = search_metadata(text)
		return wrap(found[:PAGE_SIZE], messages, tags, tables)

	return JsonResponse(
		{'error': 'Give number=<json record>, numbers=<json list>, '
		          'polynomial=<text>, polynomial_hash=<digest>, or '
		          'text=<search term>.'},
		safe=True)


#: How long a write waits for another write to the *same table* before giving
#: up and telling the caller to try again.
#:
#: It covers the write, never a caller's computation: a generator that spends
#: three hours on one entry holds nothing during those hours and takes the lock
#: only to store the result. What it has to cover is one rebuild of the table's
#: rows -- 1.8s for a table of 723 entries, 3.0s for one of 1124 -- and that
#: grows with the table, so it is a setting rather than a number in the code.
LOCK_WAIT = getattr(settings, 'NUMBERDB_WRITE_LOCK_WAIT', '15s')


#-- Writing ------------------------------------------------------------------
#
#Editing through a program is deliberately harder than editing through the
#site. A person editing a table exercises judgement about that table; a script
#exercises none, and writes faster than any reviewer can follow. So a caller
#needs a key, the key's owner needs a track record of edits people have
#actually confirmed, and the size limits are enforced rather than warned about.

def _writer_of(request):
	"""The account behind this request, or a JsonResponse explaining why not.

	Keys only. A session cookie would make every write endpoint reachable from
	any page a logged-in user visits, which is what CSRF is; a key is sent
	deliberately by a program that means to write.
	"""
	from .models import ApiKey
	from .permissions import (TRUSTED_AFTER, accepted_edit_count,
	                          may_write_through_api)
	from .throttle import _bearer_token

	token = _bearer_token(request)
	if not token:
		return None, JsonResponse(
			{'error': 'Writing needs an API key.',
			 'help': '/help#section-api'}, status=401)

	key = ApiKey.authenticate(token)
	if key is None:
		return None, JsonResponse({'error': 'Invalid API key.'}, status=403)

	user = key.user
	if not may_write_through_api(user):
		return None, JsonResponse(
			{'error': 'This account may not write through the API yet.',
			 'detail': ('Writing opens after %d edits have been reviewed and '
			            'accepted; this account has %d. Edits made on the site '
			            'count towards it.'
			            % (TRUSTED_AFTER, accepted_edit_count(user))),
			 'help': '/help#section-api'}, status=403)
	return user, None


def _document_of(request, allow_empty=False):
	"""The table document a write request carries, or an error response.

	YAML or JSON, since JSON is a subset and a caller that has one is spared
	acquiring the other. Read with BaseLoader like everything else here: YAML
	1.1 turns `no` into False, and this corpus writes `complete: no` meaning
	the word.
	"""
	body = request.body.decode('utf8', 'replace')
	if not body.strip():
		return None, JsonResponse({'error': 'No document sent.'}, status=400)
	try:
		tree = yaml.load(body, Loader=yaml.BaseLoader)
	except yaml.YAMLError as e:
		return None, JsonResponse(
			{'error': 'Could not parse the document.',
			 'detail': str(e).replace(' in "<unicode string>"', '')},
			status=400)
	if not isinstance(tree, dict):
		return None, JsonResponse(
			{'error': 'A table must be a mapping of sections.'}, status=400)
	if 'Title' not in tree:
		return None, JsonResponse({'error': 'The table has no Title.'},
		                          status=400)

	from .editing import has_entries
	if not allow_empty and not has_entries(tree):
		return None, JsonResponse(
			{'error': 'A table needs at least one entry.',
			 'detail': ('A published table with no numbers holds a permanent '
			            'T-number, appears in every listing and answers '
			            'nothing, which is indistinguishable from one '
			            'somebody abandoned. Send X-Draft: yes to propose it '
			            'instead, and fill it before publishing.')}, status=400)
	return tree, None


def _produced_by(request, user):
	"""What to record as the maker of this revision.

	Readers are entitled to know that a revision came out of a program, which
	is why Wikipedia flags bot edits; a caller may name the program, and gets
	a truthful default if it does not.
	"""
	named = (request.headers.get('X-Produced-By')
	         or request.GET.get('produced_by') or '').strip()
	return (named or 'api')[:100]


@csrf_exempt
@rate_limited
def write_table(request, tid):
	"""Replace a table's document. POST or PUT, key required."""
	from .editing import (InvalidDocument, ParametersChanged, StaleEdit,
	                      commit_table, without_managed_keys)
	from .limits import TooBig
	from .permissions import edits_are_reviewed

	if request.method not in ('POST', 'PUT'):
		return JsonResponse({'error': 'Use POST or PUT.'}, status=405)

	user, refusal = _writer_of(request)
	if refusal is not None:
		return refusal
	tree, refusal = _document_of(request)
	if refusal is not None:
		return refusal

	try:
		table = Table.objects.get(tid_int=int(str(tid).lstrip('tT')))
	except (Table.DoesNotExist, ValueError):
		return JsonResponse({'error': "No table '%s'." % (tid,)}, status=404)

	#The revision the caller says they edited from, so a concurrent change is
	#refused rather than silently overwritten. Absent means "from whatever is
	#current", which is the honest reading of a caller that did not look.
	base = table.head_revision
	wanted = (request.headers.get('X-Base-Revision')
	          or request.GET.get('base') or '').strip()
	if wanted:
		base = table.revisions.filter(digest=wanted).first()
		if base is None:
			return JsonResponse(
				{'error': 'Unknown base revision.', 'base': wanted},
				status=409)

	try:
		outcome = commit_table(
			table, without_managed_keys(tree),
			author=user, base=base, strict=True,
			produced_by=_produced_by(request, user),
			message=(request.headers.get('X-Edit-Message') or '')[:300])
	except TooBig as big:
		return JsonResponse(
			{'error': 'The table is over a size limit.',
			 'detail': [b.message for b in big.breaches],
			 'help': ('State the reason in a "Size exception" line under Data '
			          'properties if it is deliberate.')}, status=413)
	except ParametersChanged as changed:
		return JsonResponse(
			{'error': 'This edit changes the table parameters.',
			 'detail': ('Every entry is identified by its parameter values, so '
			            'changing them reassigns every identity in the table: '
			            'existing citations would still resolve and point at '
			            'different numbers.'),
			 'before': list(changed.before), 'after': list(changed.after)},
			status=409)
	except InvalidDocument as bad:
		return JsonResponse(
			{'error': 'A value in this document cannot be read as a number.',
			 'detail': str(bad)}, status=400)
	except StaleEdit as stale:
		return JsonResponse(
			{'error': 'Somebody changed this table while you were writing.',
			 'conflicts': [str(c) for c in stale.conflicts],
			 'head': stale.head.digest if stale.head else None}, status=409)

	if outcome.revision and edits_are_reviewed(user):
		table.reviewed_at_revision = outcome.revision
		#The author, by virtue of being trusted: this path publishes their
		#edits as already reviewed. Recording it is what lets the trust ladder
		#tell a self-review from somebody else's.
		table.reviewed_by = user
		table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])
		from .review import sync_review_flags
		sync_review_flags(table)

	return JsonResponse({
		'tid': table.tid,
		'url': table.url,
		'revision': outcome.revision.digest if outcome.revision else None,
		'unchanged': outcome.unchanged,
		'merged': outcome.merged,
		'reviewed': edits_are_reviewed(user),
	})


@csrf_exempt
@rate_limited
def create_table(request):
	"""Add a table. POST, key required.

	Published tables are board-only. Drafts are open to any account that may
	write through the API, up to a few in flight at once -- send
	`X-Draft: yes`, or `draft=1`. A draft is invisible, answers no search and
	can be abandoned, so proposing one is not the irreversible act that
	publishing one is.
	"""
	from .editing import create_table as make_table
	from .limits import TooBig
	from .permissions import (draft_allowance, edits_are_reviewed,
	                          may_create_drafts_through_api,
	                          may_create_tables_through_api)

	if request.method != 'POST':
		return JsonResponse({'error': 'Use POST.'}, status=405)

	user, refusal = _writer_of(request)
	if refusal is not None:
		return refusal

	#Higher than writing to a table, because it is unbounded in a way writing
	#is not: a loop that means to make three tables and makes three hundred
	#leaves three hundred permanent T-numbers, and reverting a table's
	#existence is not something the history model does.
	#`X-Draft: yes` asks for an unpublished table. Explicit rather than
	#inferred: creating a table and creating a draft are different acts with
	#different consequences, and a caller should have to say which it means.
	wants_draft = ((request.headers.get('X-Draft') or
	                request.GET.get('draft') or '').strip().lower()
	               in ('1', 'yes', 'true', 'draft'))

	if wants_draft and not may_create_tables_through_api(user):
		if not may_create_drafts_through_api(user):
			remaining, held = draft_allowance(user)
			if remaining == 0:
				return JsonResponse(
					{'error': 'This account already holds %d unpublished '
					          'drafts.' % (held,),
					 'detail': ('Publish one, or abandon it, and then this '
					            'will go through. The limit is on drafts in '
					            'flight rather than on drafts made: it is '
					            'here so that a loop which meant to create '
					            'three tables and creates three hundred is '
					            'stopped after a handful, in a place where '
					            'nobody can see them and somebody can clear '
					            'them up.')},
					status=429)
			return JsonResponse(
				{'error': 'Writing through the API is not open to this '
				          'account yet.',
				 'detail': ('Drafts may be created by any account that may '
				            'write with a program. That opens once some of '
				            'your edits have been reviewed.')},
				status=403)

	if not wants_draft and not may_create_tables_through_api(user):
		return JsonResponse(
			{'error': 'Creating tables with a program is not open to this '
			          'account.',
			 'detail': 'A table is a permanent number, a title in every '
			           'listing, and a parameter order that can never change '
			           'because citations resolve on it. Create it on the '
			           'site, where that is one deliberate act, and then a '
			           'program may fill it with numbers. A *draft* may be '
			           'created here -- send X-Draft: yes -- and published '
			           'afterwards by somebody who has looked at it.'},
			status=403)
	#A draft is exactly the thing that may not have numbers in it yet: the
	#prose is written first and a generator fills it. Publishing still
	#requires entries, which is where that rule belongs.
	tree, refusal = _document_of(request, allow_empty=wants_draft)
	if refusal is not None:
		return refusal

	try:
		table = make_table(
			tree, author=user,
			produced_by=_produced_by(request, user),
			message=(request.headers.get('X-Edit-Message') or '')[:300],
			published=not wants_draft, strict=True)
	except TooBig as big:
		return JsonResponse(
			{'error': 'The table is over a size limit.',
			 'detail': [b.message for b in big.breaches]}, status=413)
	except ValueError as e:
		return JsonResponse({'error': str(e)}, status=400)

	#A trusted account's edits are published as already reviewed, which is what
	#keeps a queue from filling with work its own reviewer would have to
	#approve. A *draft* is the exception: reviewing it is what publishing it
	#means, so marking it reviewed on arrival would skip the only look anybody
	#gets at a new table. It waits in the queue instead.
	if table.head_revision and not wants_draft and edits_are_reviewed(user):
		table.reviewed_at_revision = table.head_revision
		table.reviewed_by = user
		table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])
		from .review import sync_review_flags
		sync_review_flags(table)

	remaining, held = draft_allowance(user)
	return JsonResponse({
		'tid': table.tid,
		'url': table.url,
		'revision': table.head_revision.digest if table.head_revision else None,
		'reviewed': edits_are_reviewed(user),
		'published': table.published,
		#So a caller filling several drafts knows where it stands without
		#having to be refused first.
		'drafts_held': held,
		'drafts_remaining': remaining,
	}, status=201)


@csrf_exempt
@rate_limited
def write_entries(request, tid):
	"""Replace only a table's entries, leaving everything else untouched.

	This is the seam that `numbers.yaml` used to be. A generator computes
	values; it does not have opinions about the definition, the references or
	the tags, and under the old arrangement it could not touch them because it
	wrote its own file. Sending a whole document through `write_table` throws
	that away: a script that assembles a document from what it knows -- title,
	parameters, numbers -- deletes every section it does not know about, and
	nothing about the result looks wrong afterwards.

	So the entries arrive alone and are set into the current document here. The
	script cannot express "change the definition", which is a stronger
	guarantee than asking it not to.
	"""
	from .editing import InvalidDocument, commit_table, tree_of
	from .limits import TooBig
	from .permissions import edits_are_reviewed

	if request.method not in ('POST', 'PUT'):
		return JsonResponse({'error': 'Use POST or PUT.'}, status=405)

	user, refusal = _writer_of(request)
	if refusal is not None:
		return refusal

	try:
		table = Table.objects.get(tid_int=int(str(tid).lstrip('tT')))
	except (Table.DoesNotExist, ValueError):
		return JsonResponse({'error': "No table '%s'." % (tid,)}, status=404)
	if table.head_revision is None:
		return JsonResponse(
			{'error': 'This table has no revisions to add entries to.'},
			status=409)

	body = request.body.decode('utf8', 'replace')
	if not body.strip():
		return JsonResponse({'error': 'No entries sent.'}, status=400)
	try:
		entries = yaml.load(body, Loader=yaml.BaseLoader)
	except yaml.YAMLError as e:
		return JsonResponse(
			{'error': 'Could not parse the entries.',
			 'detail': str(e).replace(' in "<unicode string>"', '')},
			status=400)
	#A mapping is the nested form and a list is records; both are read, since
	#the two forms coexist by design.
	if not isinstance(entries, (list, dict)):
		return JsonResponse(
			{'error': 'Entries must be a list of records or a mapping.'},
			status=400)

	run_for_lease = (request.headers.get('X-Run-Id')
	                 or request.GET.get('run') or '')[:64]
	refused = _lease_allows(table, user, run_for_lease)
	if refused is not None:
		return refused

	#Read, merge and write under one lock.
	#
	#Two submissions of the same run arrive from one script in quick
	#succession. Each reads the document, adds its entry and writes the
	#result -- and adding entry 2 and entry 3 is not a conflict, but the
	#document merge compares the entries list whole, so concurrently it looks
	#like one: the second submission is refused and the generator has to work
	#out that its value was not stored.
	#
	#Worse, a request whose merge read the document at one moment and passed a
	#base from another simply overwrote the first entry, silently.
	#
	#So they serialise instead. Writes to a table are rare and a run's
	#submissions come from one script, so waiting costs nothing and the
	#alternative is either a lost value or a 409 that means "try again".
	#With a deadline. An unbounded wait is worse than the collision it avoids:
	#rebuilding a table's rows takes seconds, so a queue of blocked writers
	#occupies workers that have nothing to do but wait, and a client learns
	#nothing until it eventually succeeds or the connection dies.
	#
	#Waiting a few seconds and then saying so is the honest answer. A run
	#resending one entry costs nothing, and a caller that is told to come back
	#can decide for itself.
	try:
		with transaction.atomic():
			with connection.cursor() as cursor:
				cursor.execute("SET LOCAL lock_timeout = %s", [LOCK_WAIT])
			table = Table.objects.select_for_update().get(pk=table.pk)
			return _write_entries_locked(request, table, entries, user)
	except OperationalError:
		response = JsonResponse(
			{'error': 'Somebody else is writing this table just now.',
			 'detail': ('Waited %s and gave up rather than holding the '
			            'connection open. Nothing was written; send it again.'
			            % (LOCK_WAIT,)),
			 'retry_after': 2}, status=429)
		response['Retry-After'] = '2'
		return response


def _write_entries_locked(request, table, entries, user):
	from .editing import commit_table, tree_of
	from .limits import TooBig
	from .permissions import edits_are_reviewed
	from .editing import InvalidDocument

	#Re-read inside the lock: whatever another submission wrote a moment ago is
	#what this one must add to.
	tree = tree_of(table.head_revision)
	#Whichever name this table's entries section already goes by, so replacing
	#them does not quietly rename the section as a side effect.
	section = 'Data' if 'Data' in tree and 'Numbers' not in tree else 'Numbers'
	tree = dict(tree)

	#Upsert is what a generator computing expensive values needs: it sends each
	#as it is found, so a crash at entry 900 costs one entry rather than 900.
	#Replacing is what a regeneration needs. Neither is a sensible default for
	#the other, so it is asked for.
	mode = (request.headers.get('X-Entries-Mode')
	        or request.GET.get('mode') or 'replace').strip().lower()
	if mode == 'upsert':
		merged, added, updated = _upsert_entries(tree.get(section), entries,
		                                         tree)
		tree[section] = merged
	else:
		added = updated = None
		tree[section] = entries

	#How well these digits are known, as the generator declares it. Recorded on
	#the table rather than on every entry: it is a property of the method, and
	#a reader wants one line, not a word repeated a thousand times.
	#
	#The one piece of table metadata a generator may set, and the exception is
	#deliberate. Everything else under Data properties is somebody's prose and
	#a program has no opinion about it; this is a fact about the computation
	#that produced these numbers, which is the one thing the program knows and
	#the person cannot check. See docs/design/rigour.md.
	refused = _apply_rigour(request, tree)
	if refused is not None:
		return refused

	#A run's submissions grow one revision instead of adding one each, so
	#sending a thousand values one at a time leaves one entry in the history
	#rather than a thousand -- and one stored document rather than a thousand
	#copies of the whole table.
	run = (request.headers.get('X-Run-Id') or request.GET.get('run') or '')[:64]

	try:
		outcome = commit_table(
			table, tree, author=user, base=table.head_revision, strict=True,
			produced_by=_produced_by(request, user), run=run,
			message=(request.headers.get('X-Edit-Message')
			         or ('regenerated the entries' if mode != 'upsert'
			             else 'added entries as they were computed'))[:300])
	except InvalidDocument as bad:
		return JsonResponse(
			{'error': 'A value in these entries cannot be read as a number.',
			 'detail': str(bad)}, status=400)
	except TooBig as big:
		return JsonResponse(
			{'error': 'The entries are over a size limit.',
			 'detail': [b.message for b in big.breaches]}, status=413)

	if outcome.revision and edits_are_reviewed(user):
		table.reviewed_at_revision = outcome.revision
		#The author, by virtue of being trusted: this path publishes their
		#edits as already reviewed. Recording it is what lets the trust ladder
		#tell a self-review from somebody else's.
		table.reviewed_by = user
		table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])
		from .review import sync_review_flags
		sync_review_flags(table)

	#A submission is proof the run is alive, so it refreshes the lease. A
	#generator whose entries take less than the lease to compute therefore
	#needs no heartbeat at all.
	_refresh_lease(table, user, run)

	answer = {
		'tid': table.tid,
		'url': table.url,
		'revision': outcome.revision.digest if outcome.revision else None,
		'unchanged': outcome.unchanged,
		'reviewed': edits_are_reviewed(user),
		'amended': outcome.amended,
		'entries': len(tree.get(section) or []),
	}
	if added is not None:
		answer['added'] = added
		answer['updated'] = updated
	return JsonResponse(answer)


def _upsert_entries(existing, arriving, tree):
	"""Merge arriving entries into the ones already stored, by identity.

	An entry's identity is its parameter values, so that is what decides
	whether this is the same entry arriving again or a new one. Anything not
	mentioned is left exactly as it was, which is the whole point: a generator
	sends what it has computed and does not have to hold the rest.
	"""
	from .flatten import identity_of, parameter_groups

	groups = parameter_groups(tree)
	if isinstance(existing, dict) or isinstance(arriving, dict):
		#The nested form has no records to key on. Replacing is the honest
		#answer rather than guessing at a merge.
		return arriving, None, None

	kept = [dict(record) for record in (existing or [])
	        if isinstance(record, dict)]
	index = {identity_of(record, groups): position
	         for position, record in enumerate(kept)}

	added = updated = 0
	for record in (arriving or []):
		if not isinstance(record, dict):
			continue
		identity = identity_of(record, groups)
		if identity in index:
			kept[index[identity]] = record
			updated += 1
		else:
			index[identity] = len(kept)
			kept.append(record)
			added += 1
	return kept, added, updated


#: What one attached file may weigh, and what a table's files may weigh
#: together.
#:
#: A table holds the code that produced its numbers and the notes that explain
#: them. The largest thing in the corpus is a 477 KB Sage object; anything much
#: past that is a dataset, and a dataset wants to be a table rather than an
#: attachment on one.
MAX_ATTACHMENT_BYTES = getattr(settings, 'NUMBERDB_MAX_ATTACHMENT_BYTES',
                               2 * 1024 * 1024)
MAX_ATTACHMENTS_BYTES = getattr(settings, 'NUMBERDB_MAX_ATTACHMENTS_BYTES',
                                8 * 1024 * 1024)

#: How long a lease lasts before it must be refreshed. Long enough that a
#: single expensive entry does not cost a generator its claim, short enough
#: that a table is not held by a dead process for an afternoon.
LEASE_MINUTES = getattr(settings, 'NUMBERDB_LEASE_MINUTES', 20)


@csrf_exempt
@rate_limited
def table_lease(request, tid):
	"""Claim a table for the length of a run, refresh the claim, or drop it.

	POST to take or refresh, DELETE to drop. A generator takes one before
	computing anything, refreshes it as it goes, and drops it at the end.

	The point is not to stop other people writing -- they can, once it expires,
	and a person's edit is never refused -- but to let a second generator find
	out in its first second that this table is already being generated, rather
	than after the hours it takes to discover the collision by colliding.
	"""
	from datetime import timedelta

	from django.utils import timezone

	from .models import TableLease

	user, refusal = _writer_of(request)
	if refusal is not None:
		return refusal

	try:
		table = Table.objects.get(tid_int=int(str(tid).lstrip('tT')))
	except (Table.DoesNotExist, ValueError):
		return JsonResponse({'error': "No table '%s'." % (tid,)}, status=404)

	run = (request.headers.get('X-Run-Id') or request.GET.get('run') or '')[:64]

	if request.method == 'DELETE':
		lease = TableLease.objects.filter(table=table).first()
		if lease is not None and lease.held_by(user, run):
			lease.delete()
		return JsonResponse({'held': False})

	if request.method != 'POST':
		return JsonResponse({'error': 'Use POST to take a lease, DELETE to '
		                              'drop it.'}, status=405)

	minutes = LEASE_MINUTES
	until = timezone.now() + timedelta(minutes=minutes)

	with transaction.atomic():
		lease = (TableLease.objects.select_for_update()
		         .filter(table=table).first())
		if lease is not None and not lease.held_by(user, run):
			return JsonResponse({
				'error': 'This table is being generated by somebody else.',
				'detail': ('%s holds it until %s%s. Nothing was written; a '
				           'lease is dropped when its run finishes and expires '
				           'by itself if the run dies.'
				           % (lease.owner.username if lease.owner else 'a run',
				              lease.expires.strftime('%Y-%m-%d %H:%M'),
				              ', doing: %s' % (lease.note,) if lease.note else '')),
				'expires': lease.expires.isoformat(),
			}, status=409)

		if lease is None:
			lease = TableLease(table=table)
		lease.owner = user
		lease.run = run
		lease.note = (request.headers.get('X-Lease-Note') or '')[:200]
		lease.expires = until
		lease.save()

	return JsonResponse({
		'held': True,
		'run': lease.run,
		'expires': lease.expires.isoformat(),
		'minutes': minutes,
	})


def _lease_allows(table, user, run):
	"""Whether this writer may write, given any lease on the table.

	A lease held by somebody else refuses a *program*. It never refuses a
	person editing on the site: a generator's claim on a table is a claim
	against other generators, and somebody correcting a digit by hand is not
	what it is for.
	"""
	from .models import TableLease

	lease = TableLease.objects.filter(table=table).first()
	if lease is None or lease.held_by(user, run):
		return None
	return JsonResponse({
		'error': 'This table is being generated by somebody else.',
		'detail': ('%s holds it until %s. Nothing was written.'
		           % (lease.owner.username if lease.owner else 'a run',
		              lease.expires.strftime('%Y-%m-%d %H:%M'))),
		'expires': lease.expires.isoformat(),
	}, status=409)


def _refresh_lease(table, user, run):
	"""Push a live lease's expiry out, when the writer holds it."""
	from datetime import timedelta

	from django.utils import timezone

	from .models import TableLease

	lease = TableLease.objects.filter(table=table).first()
	if lease is None or not lease.held_by(user, run):
		return
	lease.expires = timezone.now() + timedelta(minutes=LEASE_MINUTES)
	lease.save(update_fields=['expires'])


def _apply_rigour(request, tree):
	"""Set Data properties: rigour from the X-Rigour header, if it is there.

	Shared by the two endpoints a generator writes through. A run that changes
	no number still sends its source, and that is exactly the run whose point
	may be to state how well the numbers are known -- so the declaration cannot
	ride only with the entries.

	Returns an error response, or None.
	"""
	from .validate import RIGOUR_LEVELS

	rigour = (request.headers.get('X-Rigour') or '').strip()[:60]
	if not rigour:
		return None
	if rigour not in RIGOUR_LEVELS:
		return JsonResponse(
			{'error': "Unknown rigour %r." % (rigour,),
			 'detail': 'One of: %s.' % (', '.join(RIGOUR_LEVELS),)},
			status=400)
	properties = dict(tree.get('Data properties') or {})
	properties['rigour'] = rigour
	tree['Data properties'] = properties
	return None


@csrf_exempt
@rate_limited
def write_file(request, tid, name):
	"""Attach a file to a table, in the same revision as the run's entries.

	The code that produced a set of numbers belongs with them, and until now a
	program could send its results but not itself: `generate.sage` had to be
	put in the data repository by hand, where it drifted from whatever actually
	ran.

	Carrying the same run as the entries puts it on the same revision, so a
	reader looking at where a number came from finds the code that made it
	rather than the code that happens to be there now.
	"""
	from .editing import commit_table, tree_of
	from .limits import TooBig

	if request.method not in ('POST', 'PUT'):
		return JsonResponse({'error': 'Use POST or PUT.'}, status=405)

	user, refusal = _writer_of(request)
	if refusal is not None:
		return refusal

	try:
		table = Table.objects.get(tid_int=int(str(tid).lstrip('tT')))
	except (Table.DoesNotExist, ValueError):
		return JsonResponse({'error': "No table '%s'." % (tid,)}, status=404)
	if table.head_revision is None:
		return JsonResponse({'error': 'This table has no revisions.'},
		                    status=409)

	run = (request.headers.get('X-Run-Id') or request.GET.get('run') or '')[:64]
	refused = _lease_allows(table, user, run)
	if refused is not None:
		return refused

	wrong = _bad_attachment_name(name)
	if wrong is not None:
		return wrong

	content = request.body
	if not content:
		return JsonResponse({'error': 'No file sent.'}, status=400)
	if len(content) > MAX_ATTACHMENT_BYTES:
		return JsonResponse(
			{'error': 'That file is too large.',
			 'detail': ('%d bytes, and the limit is %d. A table holds the code '
			            'that produced its numbers and the notes that explain '
			            'them; anything larger is a dataset, and a dataset '
			            'wants to be a table.'
			            % (len(content), MAX_ATTACHMENT_BYTES))}, status=413)

	total = sum(a.blob.size for a in
	            table.head_revision.attachments.select_related('blob')
	            if a.name != name) + len(content)
	if total > MAX_ATTACHMENTS_BYTES:
		return JsonResponse(
			{'error': "That would make the table's files too large.",
			 'detail': ('%d bytes in total, and the limit is %d.'
			            % (total, MAX_ATTACHMENTS_BYTES))}, status=413)

	try:
		with transaction.atomic():
			with connection.cursor() as cursor:
				cursor.execute("SET LOCAL lock_timeout = %s", [LOCK_WAIT])
			table = Table.objects.select_for_update().get(pk=table.pk)
			tree = tree_of(table.head_revision)
			refused = _apply_rigour(request, tree)
			if refused is not None:
				return refused
			outcome = commit_table(
				table, tree, author=user,
				base=table.head_revision, strict=True, run=run,
				produced_by=_produced_by(request, user),
				files={name: content},
				message=(request.headers.get('X-Edit-Message')
				         or 'attached %s' % (name,))[:300])
	except OperationalError:
		response = JsonResponse(
			{'error': 'Somebody else is writing this table just now.',
			 'retry_after': 2}, status=429)
		response['Retry-After'] = '2'
		return response
	except TooBig as big:
		return JsonResponse({'error': 'Over a size limit.',
		                     'detail': [b.message for b in big.breaches]},
		                    status=413)

	_refresh_lease(table, user, run)
	return JsonResponse({
		'tid': table.tid,
		'name': name,
		'bytes': len(content),
		'revision': outcome.revision.digest if outcome.revision else None,
		'amended': outcome.amended,
	})


def _bad_attachment_name(name):
	"""Refuse a name that is not a plain file beside the table.

	A table's files are flat: `generate.sage`, `notes.txt`. No directories, so
	there is one place to look and no question about what `../` or an absolute
	path would mean; the export writes them beside the table's document, and a
	name that climbs out of that directory is not a file on a table at all.

	The corpus needs nothing else. Its one nested case was 25 files that the
	import flattened, and nothing has wanted a subdirectory since.
	"""
	if not name or name in ('.', '..'):
		return JsonResponse({'error': 'A file needs a name.'}, status=400)
	if '/' in name or '\\' in name:
		return JsonResponse(
			{'error': "A table's files are flat.",
			 'detail': ('%r names a directory. Use a plain name such as '
			            'generate.sage, so there is one place to look and no '
			            'question about where a path leads.' % (name,))},
			status=400)
	if name.startswith('.'):
		return JsonResponse(
			{'error': 'A file name may not start with a dot.',
			 'detail': 'Hidden files are not what a table carries.'},
			status=400)
	if len(name) > 100:
		return JsonResponse({'error': 'That file name is too long.'},
		                    status=400)
	return None
