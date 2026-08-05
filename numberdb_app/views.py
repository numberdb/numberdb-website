from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
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


from sage.all import infinity, copy, ceil, log, latex, factor
from sage.rings.all import ZZ, QQ, RR, CC, RIF, CIF
from sage.rings.all import RealField, RealIntervalField, RealBallField
from sage.rings.all import ComplexField, ComplexIntervalField, ComplexBallField
from utils.utils import is_pAdicField

from .eval_client import ping as evaluator_is_available
from sage.rings.all import PolynomialRing

from urllib.parse import quote_plus, unquote_plus

from mpmath import pslq

from .models import findable_by_number
from .models import UserProfile
from .models import Wanted

from .models import Table
from .models import TableData
from .models import TableRevision
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

from .common import type_names

from .api import advanced_search_results

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


from .search import (PAGE_SIZE, full_text_query, max_relative_width,
                     search_by_term, search_metadata)
from .search import (search_complex_numbers, search_fractional_parts,
                     search_p_adic_numbers, search_real_numbers)

from db_builder.utils import normalize_table_data
from .templatetags.numberdb_urls import entry_suffix

def home(request):
	#The search bar submits here, so the query lives in the URL and a search can
	#be linked, bookmarked and returned to. Without a query this is the plain
	#front page, exactly as before.
	term = request.GET.get('q', '').strip()
	context = {'searchterm': term}
	if term:
		groups = search_by_term(term)
		#Asked as well as the numbers, not instead: "0.5" is a number, and
		#"matrix multiplication" is words, but a term like "Pi" is honestly
		#both, and which was meant is not knowable here.
		tags, tables = search_metadata(term)
		context['result_groups'] = groups
		context['result_tags'] = tags
		context['result_tables'] = tables
		context['result_count'] = sum(len(g['numbers']) for g in groups)
		context['result_meta_count'] = len(tags) + len(tables)
		context['result_total'] = (context['result_count']
		                           + context['result_meta_count'])
		context['result_page_size'] = PAGE_SIZE
		context['searched'] = True

	#The page asks for just the panel when it is updating in place, so a search
	#does not rebuild the whole document. The full response is still what a
	#plain GET returns, which is what makes the URL work when shared, and what
	#happens if the request never runs.
	if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
		if not term:
			return HttpResponse('')
		return render(request, 'includes/search-results-panel.html', context)
	return render(request, 'home.html', context)

def about(request):
    return render(request, 'about.html', {})

def help(request):
	contribution_count = {}
	for contributor in Contributor.objects.all():
		name = contributor.author
		if name in contribution_count:
			contribution_count[name] += contributor.table_commit_count
		else:
			contribution_count[name] = contributor.table_commit_count
	contribution_count = [
		{'name': name, 'count': count} 
		for name, count in contribution_count.items()
	]
	contribution_count.sort(key = lambda name_count: -name_count['count'])
	print("contribution_count:",contribution_count)
	#contributors = Contributor.objects.all().order_by('-table_commit_count')
	context = {
		'contribution_count': contribution_count,
		#Documented from the setting, so the help text cannot drift from the
		#cutoff search actually applies.
		'max_relative_width': max_relative_width(),
		#Documented from the settings in force, so the help cannot promise a
		#limit the server does not apply.
		'anonymous_rate_limit': getattr(settings, 'NUMBERDB_ANONYMOUS_RATE_LIMIT', 60),
		'identified_rate_limit': getattr(settings, 'NUMBERDB_IDENTIFIED_RATE_LIMIT', 1000),
	}
	return render(request, 'help.html', context)

def tables(request):
	page = request.GET.get('page', 1)
	#print("page:",page)
	#Drafts belong to their authors until published; the listing is public.
	tables = Table.objects.filter(published=True)
	sortby_default = 'title'
	sortby = request.GET.get('sort_by',default=sortby_default)
	if sortby == 'entry_count':
		tables = tables.order_by('-number_count')
	elif sortby == 'id':
		tables = tables.order_by('tid_int')
	elif sortby == 'title':
		tables = tables.order_by('title_lowercase')
	else:
		tables = tables.order_by(sortby_default)
	paginator = Paginator(tables, 50)
	try:
		shown_tables = paginator.page(page)
	except PageNotAnInteger:
		shown_tables = paginator.page(1)
	except EmptyPage:
		shown_tables = paginator.page(paginator.num_pages)
	#print("shown_tables:",shown_tables)
	return render(request, 'tables.html', {'tables': shown_tables, 'sortby': sortby})

def tags(request):
	page = request.GET.get('page', 1)
	tags = Tag.objects.all()
	sortby_default = 'entry_count'
	sortby = request.GET.get('sort_by',default=sortby_default)
	if sortby == 'table_count':
		tags = tags.order_by('-table_count')
	elif sortby == 'entry_count':
		tags = tags.order_by('-number_count')
	elif sortby == 'name':
		tags = tags.order_by('name_lowercase')
	else:
		tags = tags.order_by(sortby_default)
	paginator = Paginator(tags, 50)
	try:
		shown_tags = paginator.page(page)
	except PageNotAnInteger:
		shown_tags = paginator.page(1)
	except EmptyPage:
		shown_tags = paginator.page(paginator.num_pages)
	return render(request, 'tags.html', {'tags': shown_tags, 'sortby': sortby})

def tag(request, tag_url):
	page = request.GET.get('page', 1)
	tag = Tag.from_url(tag_url)
	#tag = Tag.objects.get(name=tag_name)
	tables = tag.tables.all()
	sortby_default = 'entry_count'
	sortby = request.GET.get('sort_by',default=sortby_default)
	if sortby == 'entry_count':
		tables = tables.order_by('-number_count')
	elif sortby == 'id':
		tables = tables.order_by('tid_int')
	elif sortby == 'title':
		tables = tables.order_by('title_lowercase')
	else:
		tables = tables.order_by(sortby_default)
	paginator = Paginator(tables, 50)
	try:
		shown_tables = paginator.page(page)
	except PageNotAnInteger:
		shown_tables = paginator.page(1)
	except EmptyPage:
		shown_tables = paginator.page(paginator.num_pages)
	return render(request, 'tag.html', {'tag': tag, 'tables': shown_tables, 'sortby': sortby})

def wanteds(request):
	page = request.GET.get('page', 1)
	wanteds = Wanted.objects.all()
	sortby_default = 'date'
	sortby = request.GET.get('sort_by',default=sortby_default)
	if sortby == 'date':
		wanteds = wanteds.order_by('date_created')
	elif sortby == 'title':
		wanteds = wanteds.order_by('title')
	else:
		wanteds = wanteds.order_by(sortby_default)
	paginator = Paginator(wanteds, 50)
	try:
		shown_wanteds = paginator.page(page)
	except PageNotAnInteger:
		shown_wanteds = paginator.page(1)
	except EmptyPage:
		shown_wanteds = paginator.page(paginator.num_pages)
	return render(request, 'wanteds.html', {'wanteds': shown_wanteds, 'sortby': sortby})

def welcome(request):
    return render(request, 'welcome.html')

def render_table(request, table, context=None):
	context = dict(context or {})
	context.update(table_context(table))
	context.update(_entry_address(request, table, context))
	return render(request, 'table.html', context)


def _parameter_order(table):
	"""The table's parameter names, in the order the entries nest.

	Read from the document rather than stored, because it is the document that
	decides: the identity of an entry is its parameter values in nesting order,
	and the Parameters section is what names them.
	"""
	import yaml as _yaml
	try:
		tree = _yaml.load(table.data.full_yaml, Loader=_yaml.BaseLoader) or {}
	except Exception:
		return []
	return list((tree.get('Parameters') or {}).keys())


def _reference_href(ref):
	"""Turn an HREF{} target into a link that a server can resolve.

	    Factorial#0        ->  /Factorial?entry=0#0
	    #CL                ->  ?entry=CL#CL          (same table)
	    Factorial          ->  /Factorial            (no entry named)
	    https://...        ->  unchanged

	Left as a bare fragment, these are citations that keep working while
	meaning something else, which is the failure this addressing exists to
	remove. They are data rather than markup, so they are rewritten as they are
	rendered rather than migrated in place.
	"""
	from urllib.parse import quote

	ref = (ref or '').strip()
	if not ref or ref.startswith(('http://', 'https://', 'mailto:')):
		return ref

	table_part, sep, entry = ref.partition('#')
	if not sep or not entry:
		#A whole table, or an in-page anchor that names no entry.
		return ref
	suffix = '?entry=%s' % (quote(entry, safe=',:'),)
	if not table_part:
		return suffix                       # same table
	return '%s%s' % (table_part, suffix)


def _entry_address(request, table, context):
	"""Resolve ?entry=<parameters>, which the server can actually see.

	A single value has always had an address of the form

	    /Best_Sobolev_constant#6,18/11,9/4

	but a fragment is never sent to the server. So nothing could render one
	entry, validate that it exists, or tell a reader that a citation had gone
	stale: the page simply loaded and the browser found nothing to scroll to.
	For a database whose worth is that a number has a permanent address, that
	is the wrong way to fail.

	It travels in the query string rather than the path because 6736 of the
	identities contain a "/" -- parameters are rationals like 18/11 -- and a
	percent-encoded slash inside a path segment is rewritten or rejected by a
	good deal of software between here and the reader.

	The fragment stays, so the browser still scrolls. The query is what makes
	the address resolvable.
	"""
	requested = (request.GET.get('entry') or '').strip()
	if not requested:
		return {}

	#Normalised the same way the anchors are, so that a citation written with
	#the spaces a person naturally types still finds its entry.
	from .review import _normalise_param
	wanted = _normalise_param(requested)

	#A named citation, "n=6,p=18/11", is resolved against the table's declared
	#parameters and turned into the positional form the anchors still use.
	#
	#Named is the form worth writing down. A positional identity says 1,2 and
	#nothing about what 1 and 2 are, so if the parameters are ever nested the
	#other way round, 1,2 still exists and quietly means a different number:
	#the link does not break, it lies. a=1,b=2 cannot be confused with a=2,b=1.
	if '=' in wanted:
		named = {}
		for part in wanted.split(','):
			if '=' not in part:
				named = None
				break
			name, _, value = part.partition('=')
			named[name.strip()] = value.strip()
		order = _parameter_order(table)
		if named is not None and order and set(named) <= set(order):
			wanted = ','.join(named[name] for name in order if name in named)
		elif named is not None:
			messages.warning(request, (
				'This table has no parameter %s.'
				% (', '.join(sorted(set(named) - set(order))) or 'of that name',)))
			return {'entry': requested, 'entry_found': False}

	known = set()
	section = context.get('number_section') or {}
	for row in (section.get('number_list') or []):
		known.add(row.get('params_id') or '')

	if wanted in known:
		return {'entry': wanted, 'entry_found': True,
		        'canonical_entry_url': '%s?entry=%s' % (
			        reverse('db:table', kwargs={'tid': table.tid}),
			        quote_plus(wanted))}

	#Said out loud rather than ignored. A citation that has stopped working is
	#worth knowing about, and the reader is the only person in a position to
	#notice.
	messages.warning(request, (
		'This table has no entry %s. It may have been renumbered or removed; '
		'the table itself is shown below.' % (requested,)))
	return {'entry': wanted, 'entry_found': False}

def table_by_tid(request, tid):
    try:
        table = Table.objects.get(tid=tid)
    except Table.DoesNotExist:
        raise Http404
    _refuse_a_draft(request, table)
    return render_table(request, table, {'requested_tid': tid})
    
def table_by_url(request, url):
    try:
        table = Table.objects.get(url=url)
    except Table.DoesNotExist:
        raise Http404
    _refuse_a_draft(request, table)
    return render_table(request, table, {'requested_url': url})


def _refuse_a_draft(request, table):
    """A draft is not found, rather than forbidden, to anybody else.

    Answering "you may not see this" would confirm that a table with that name
    or that number exists, which is the one thing a private draft should not
    tell a stranger.
    """
    from .editing import may_see

    if not may_see(table, getattr(request, 'user', None)):
        raise Http404

def table_context(table, preview=False):

	def wrap_in_div(div_class,html):
		return '<div class="%s">%s</div>' % (div_class,html)

	def render_text(text, line_breaks = True):
		'''
		Parse text for 'CITE', 'HREF', and '\n', 
		and replace accordingly.
		'''
		
		if not isinstance(text, str):
			raise ValueError('string expected instead of %s' % text.__class__)
		
		#Parse 'CITE's:
		parts = text.split("CITE{")
		new_text = parts[0]
		for part in parts[1:]:
			try: 
				ref, part2 = part.split("}",maxsplit=1)
			except ValueError:
				raise ValueError('no closing bracket in CITE')
			try:
				new_text += '<a class="CITE" href="#%s">%s</a>%s' % (ref, show_label_as[ref], part2)
				#new_text += '<a class="CITE" href="#%s" onClick="(event) => {scrollTo(event,);}">%s</a>%s' % (ref, ref, show_label_as[ref], part2)
			except KeyError:
				raise ValueError('unknown label %s in CITE' % (ref,))
				
		#Parse 'HREF's:
		parts = new_text.split("HREF{")
		new_text = parts[0]
		for part in parts[1:]:
			try: 
				ref, part2 = part.split("}",maxsplit=1)
			except ValueError:
				raise ValueError('no closing bracket in HREF')
			if part2 != "" and part2[0] == "[":
				try:
					caption, part2 = part2[1:].split("]",maxsplit=1)
				except ValueError:
					caption = ref
			else:
				caption = ref
			#A reference such as HREF{Factorial#0} names an entry, and until now
			#it produced a fragment-only link: exactly the form that resolves to
			#the wrong number if a table is ever renested, without breaking. 98
			#references in the corpus carry an entry this way, so they are given
			#the query form as well.
			new_text += '<a class="HREF" href="%s">%s</a>%s' % (
				_reference_href(ref), caption, part2)
				
		if line_breaks:
			#Parse '\n's:
			new_text = new_text.replace("\n","<br>")
		return new_text

	current_job = ''

	try:

		current_job = 'loading yaml'
		#data = table.data.json
		data = yaml.load(table.data.full_yaml,Loader=yaml.BaseLoader)

		html = ''

		#Deduce label names:
		show_label_as = {}
		i_label = 1
		for header in ('Formulas','Comments'):
			current_job = 'parsing label names for %s' % (header,)
			if header in data and len(data[header]) > 0:
				for label in data[header]:
					show_label_as[label] = '(%s)' % (i_label,)
					i_label += 1
		i_label = 1
		for header in ('Programs',):
			current_job = 'parsing label names for %s' % (header,)
			if header in data and len(data[header]) > 0:
				for label in data[header]:
					print("label:",label)
					show_label_as[label] = '(P%s)' % (i_label,)
					i_label += 1
		i_label = 1
		for header in ('References','Links'):
			current_job = 'parsing label names for %s' % (header,)
			if header in data and len(data[header]) > 0:
				for label in data[header]:
					show_label_as[label] = '[%s]' % (i_label,)
					i_label += 1
			
		sections = []
			
		current_job = 'parsing definition'
		if 'Definition' in data:
			section = {
				'title': 'Definition',
				'text': render_text(data['Definition']),
			}
			sections.append(section)
			
		current_job = 'parsing parameters'
		if 'Parameters' in data and len(data['Parameters']) > 0:
			labeled_list = []
			parameters = {}
			for p, info in data['Parameters'].items():
				current_job = 'parsing parameter %s' % (p,)
				p_latex = info['display'] if 'display' in info else "$%s$" % (p,)

				text = ' &mdash;&nbsp;&nbsp; '
				if 'title' in info:
					text += '%s' % (render_text(info['title']),)    
				elif 'type' in info:
				#if 'type' in info:
					if info['type'] in type_names:
						text += type_names[info['type']]
					else:
						text += "%s (Unknown type)" % (info['type'],)
				if 'constraints' in info:
					constraints = info['constraints']
					if isinstance(constraints,list):
						constraints = ', '.join(constraints)
					text += ' (%s)' % (render_text(constraints),)

				if 'show-in-parameter-list' in info and info['show-in-parameter-list'].lower() == 'no':
					#Don't show this parameter in the homepage of this table.
					parameters[p] = ''
					continue

				parameters[p] = p_latex
					
				labeled_list.append({
					'label_id': p,
					'label_caption': render_text(p_latex),
					'text': text,
				})
			if len(labeled_list) > 0:
				section = {
					'title': 'Parameters',
					'labeled_list': labeled_list,
				}
				sections.append(section)

		else:
			parameters = []
						
		for header in ('Formulas','Comments'):
			current_job = 'parsing %s' % (header,)
			if header in data and len(data[header]) > 0:
				labeled_list = []
				for label, text in data[header].items():
					current_job = 'parsing %s %s' % (header,label)
					labeled_list.append({
						'label_id': label,
						'label_caption': show_label_as[label],
						'text': render_text(text),
					})
				section = {
					'title': header,
					'labeled_list': labeled_list,
				}
				sections.append(section)
		
		highlight_language = {
			'Sage': 'python',
			'default': '',
		}

		#Continue i_label, as it's all interior data, not a direct reference.
		for header in ('Programs',):
			current_job = 'parsing %s' % (header,)
			if header in data and len(data[header]) > 0:
				labeled_list = []
				for label, program in data[header].items():
					current_job = 'Parse program %s' % (label,)
					language = render_text(program['language'])
					if language in highlight_language:
						code_language = highlight_language[language]
					else:
						code_language = highlight_language['default']
					text = '%s<br><pre><code class="table-code language-%s">%s</code></pre>' % (
						language,
						code_language,
						#render_text(program['code']),
						program['code'],
					)
					labeled_list.append({
						'label_id': label,
						'label_caption': show_label_as[label],
						'text': text,
					})
				section = {
					'title': 'Programs',
					'labeled_list': labeled_list,
				}
				sections.append(section)

		for header in ('References','Links'):
			current_job = 'parsing %s' % (header,)
			if header in data and len(data[header]) > 0:
				labeled_list = []
				for label, reference in data[header].items():
					current_job = 'Parse %s %s' % (header,label)
					text = ""
					if isinstance(reference, str):
						text = render_text(reference)
					else:
						#Matched case-insensitively. The corpus spells arXiv 14
						#times and arxiv 4, MR 7 times and mr twice, and an exact
						#lookup silently rendered the reference without its link:
						#no error, no warning, just a citation missing the thing
						#a reader wants to click.
						fields = {k.lower(): v for k, v in reference.items()}
						if 'bib' in fields:
							text += render_text(fields['bib'].rstrip('\n')) + " "
						if 'arxiv' in fields:
							link = fields['arxiv']
							link = link.split("[")[0].strip(" \n")
							link = link.split("/abs/")[-1]
							link = link.split("/pdf/")[-1]
							link = link.split("/ps/")[-1]
							link = link.split("/format/")[-1]
							link = link.split("arXiv:")[-1]
							link = link.split("arxiv:")[-1]
							link = "https://www.arxiv.org/abs/%s" % (link,)
							text += '(<a href="%s">arXiv</a>) ' % (link,)
						if 'doi' in fields:
							link = fields['doi'].split("doi.org/")[-1]
							link = "https://doi.org/%s" % (link,)
							text += '(<a href="%s">doi</a>) ' % (link,)
						#zbMATH before MathSciNet, because zbMATH Open serves the
						#document to anybody: an anonymous request returns the
						#record, while MathSciNet returns a JavaScript shell and,
						#behind it, a subscription. A reader without an
						#institution can follow one of these links and not the
						#other, so the open one goes first.
						#
						#Accepts 'zbl' and 'zbmath', and tolerates a value written
						#either as a bare Zbl number or with the prefix.
						if 'zbl' in fields or 'zbmath' in fields:
							link = str(fields.get('zbl') or fields.get('zbmath')).strip()
							link = link.split("an:")[-1].strip()
							if link.lower().startswith('zbl'):
								link = link[3:].strip()
							text += ('(<a href="https://zbmath.org/?q=an%%3A%s">zbMATH</a>) '
							         % (link,))
						#Never rendered at all before: there was no branch for it,
						#so nine Mathematical Reviews numbers sat in the data
						#doing nothing. Kept despite the paywall, because the
						#number is real information and is useful to anyone who
						#does have access.
						if 'mr' in fields:
							link = str(fields['mr']).strip()
							link = link.split("mr=")[-1].lstrip("MRmr")
							text += ('(<a href="https://mathscinet.ams.org/'
							         'mathscinet-getitem?mr=%s">MR</a>) ' % (link,))
						if 'url' in fields:
							if 'title' in fields:
								text += '<a href="%s">%s</a> ' % (fields['url'],fields['title'])
							else:
								text += '<a href="%s">%s</a> ' % (fields['url'],fields['url'])
						if 'github' in fields:
							link = fields['github'].split("github.com/")[-1]
							link = "https://github.com/%s" % (link,)
							text += '(<a href="%s">github</a>) ' % (link,)

					labeled_list.append({
						'label_id': label,
						'label_caption': show_label_as[label],
						'text': text,
					})
				section = {
					'title': header,
					'labeled_list': labeled_list,
				}
				sections.append(section)

		data_type = None #Will be set to data['Data properties']['type'].

		property_names = {
			'type': 'Entries are of type',
			'complete': 'Table is complete',
			'sources': 'Sources of data',
			'relative precision': 'Relative precision',
			'absolute precision': 'Absolute precision',
			'reliability': 'Reliability',
			#'accuracy': 'Accuracy',
		}
		current_job = 'parsing data properties'
		if 'Data properties' in data and len(data['Data properties']) > 0:
			properties = data['Data properties']
			#print("properties:",properties)
			unlabeled_list = []
			for key, value in properties.items():
				current_job = 'Parse data property %s' % (key,)
				if len(value) == 0:
					continue
				#Rendered as part of 'complete' rather than on a line of its own,
				#since "Table is complete: yes (assuming GRH)" is the sentence a
				#reader wants. Skipped here so it does not also appear alone.
				if key == 'complete-note':
					continue
				if key in property_names:
					text = "%s: " % (property_names[key])
					if key == 'type':
						data_type = value
						if properties['type'] in type_names:
							text += type_names[value]
						else:
							text += "%s (Unknown value)" % (value,)
					elif key == 'sources':
						text += ", ".join(value)                
					elif key == 'complete':
						text += value
						note = properties.get('complete-note')
						if note:
							text += " (%s)" % (note,)
					else:
						text += value
				else:
					text = "%s: %s (Unknown key)" % (key, value)     
				unlabeled_list.append({
					'text': render_text(text),
				})
			section = {
				'title': 'Data properties',
				'unlabeled_list': unlabeled_list,
			}
			sections.append(section)
			print("properties:",properties)

		current_job = 'parsing display properties'
		param_groups = [[p] for p in parameters]
		number_header = None
		if 'Display properties' in data:
			display_properties = data['Display properties']
			if 'group parameters' in display_properties:
				param_groups = display_properties['group parameters']
			if 'number-header' in display_properties:
				number_header = display_properties['number-header']
		#print("param_groups:",param_groups)

		param_groups_display = []
		for group in param_groups:
			group_display = ''
			for p in group:
				p_latex = parameters[p] if p in parameters else p
				group_display += '%s%s' % (
					',&nbsp;' if group_display != '' else '',
					p_latex,
				)
			param_groups_display.append(group_display)
		if param_groups_display != []:
			if param_groups_display[-1] != '':
				param_groups_display[-1] += '&nbsp' #similar to the ":" in the table body

		#OLD: rendering of numbers:
		def render_number_table_as_tree(numbers, params_so_far=[], groups_left=param_groups):
			nonlocal current_job
			current_job = 'parsing number with parameter %s' % (str(params_so_far),)
			html = ''

			def wrap_in_subtable(inner_html):
				return '<div class="table-subtable">%s</div>' % (inner_html,)

			def format_param_group(param_group):
				result = ', '.join(p.strip(' ') for p in param_group.split(','))
				result = result.replace(' ','&nbsp;')
				return result

			if isinstance(numbers,dict):
				if 'number' in numbers or \
					'numbers' in numbers or \
					'datum' in numbers or \
					'data' in numbers or \
					'equals' in numbers:
					#Numbers are given with extra information at this level:
					for key in numbers:
						if key in ('number','numbers','datum','data','param-latex'):
							continue
						html += '%s: %s<br>' % (key, render_text(numbers[key]))
					if 'number' in numbers:
						html += render_number_table(numbers['number'], params_so_far, groups_left)
					elif 'numbers' in numbers:
						html += render_number_table(numbers['numbers'], params_so_far, groups_left)
					elif 'datum' in numbers:
						html += render_number_table(numbers['datum'], params_so_far, groups_left)
					elif 'data' in numbers:
						html += render_number_table(numbers['data'], params_so_far, groups_left)
					return html
				
			if len(groups_left) == 0:
				#numbers is an entry for a number now, either a string or a dict:
				if isinstance(numbers,str):
					html += '<div class="table-number">%s</div>' % (numbers,)
				else:
					if isinstance(numbers,list):           
						for number in numbers:
							html += '<div class="table-number">%s</div>' % (number,)
					elif isinstance(numbers,dict):  
						for key, value in numbers.items():
							html += '<div class="table-number-%s">%s</div>' % (key,render_text(value),)

			else:
				if preview and isinstance(numbers,str) and numbers.startswith("INPUT"):
					return '%s (not shown in preview)' % numbers
				next_group = groups_left[0]
				html += '<div class="table-subtable">'
				for p, numbers_p in numbers.items():
					if len(groups_left) <= 1:
						param = number_param_groups_to_string(params_so_far+[p])
						id_str = 'id="%s"' % (param,) if param != '' else ''
					else:
						id_str = ''
					html_p = '<div %s class="table-block">' % (id_str,)
					if isinstance(numbers_p,dict) and 'param-latex' in numbers_p:
						param_html = numbers_p['param-latex']
					else:
						param_html = format_param_group(p)
					html_p += '<div class="table-param-group"><span>%s:</span></div>' % (param_html,)
					html_inner = render_number_table(numbers_p, params_so_far+[p], groups_left[1:])
					html_p += '<div class="table-cell-right">%s</div>' % (wrap_in_subtable(html_inner),)
					html_p += '</div>'
					html += html_p
				html += '</div>'

			return html    

		def number_table_as_list(numbers, params_id_so_far='', params_display_so_far=[], groups_left=param_groups, extra_info={}):
			nonlocal current_job
			current_job = 'parsing number with parameter %s' % (str(params_display_so_far),)

			def format_param_group(param_group, separator=','):
				result = separator.join(p.strip(' ') for p in param_group.split(','))
				#result = result.replace(' ','&nbsp;')
				return result

			if isinstance(numbers,dict):
				if 'number' in numbers or \
					'numbers' in numbers or \
					'datum' in numbers or \
					'data' in numbers or \
					'equals' in numbers:
						
					#Numbers are given with extra information at this level:
					extra_info = copy(extra_info)
					for key, value in numbers.items():
						if key in ('number','numbers','param-latex'):
							continue
						extra_info[key] = render_text(value)
					if 'number' in numbers:
						numbers = numbers['number']
					elif 'numbers' in numbers:
						numbers = numbers['numbers']
					else:
						#Just extra info is given:
						
						if len(params_display_so_far) > 0:
							params_display_so_far[-1] += ':'
						return [{
							'params_id': params_id_so_far,
							'params_display': params_display_so_far + ['' for g in groups_left],
							'extra_info': extra_info,						
						}]
						
					return number_table_as_list(
						numbers, 
						params_id_so_far, 
						params_display_so_far, 
						groups_left, 
						extra_info,
					)
				
			if len(groups_left) == 0:
				#numbers is an entry for a number now, either a string or a dict:
				
				if isinstance(numbers,str):
					numbers = (numbers,)
				result = []
				if len(params_display_so_far) > 0:
					params_display_so_far[-1] += ':'
				for number in numbers:
					result.append({
						'params_id': params_id_so_far,
						'params_display': params_display_so_far,
						'number': number,
						#Marked in the table so a reader who cannot find this
						#number in the search can see why.
						'not_findable': not findable_by_number(number)
							if isinstance(number, str) else False,
						'extra_info': extra_info,
					})
				return result
				
			else:
				if preview and isinstance(numbers,str) and numbers.startswith("INPUT"):
					return ({
						'params_display': params_display_so_far + ['' for g in groups_left],
						'number': '%s (not shown in preview)' % numbers,
						'extra_info': extra_info,						
					},)
				result = []

				next_group = groups_left[0]
				later_groups = groups_left[1:]
				for p, numbers_p in numbers.items():
					if isinstance(numbers_p,dict) and 'param-latex' in numbers_p:
						param_html = numbers_p['param-latex']
					else:
						param_html = format_param_group(p,', ').replace(' ','&nbsp;')
					params_display_so_far_p = params_display_so_far + [param_html]
					if params_id_so_far == '':
						params_id_so_far_p = format_param_group(p)
					else:
						params_id_so_far_p = '%s,%s' % (
							params_id_so_far, 
							format_param_group(p),
						)

					result += number_table_as_list(
						numbers_p, 
						params_id_so_far_p,
						params_display_so_far_p,
						later_groups,
						extra_info,
					)

			return result

		#html += '</div>'
		#html += '<div class="col-m-6">'
				
		current_job = 'parsing numbers'
		if 'Numbers' in data and len(data['Numbers']) > 0:
			numbers = data['Numbers']
			number_section = {
				'title': pluralize('Number',table.number_count),
				'param_groups': param_groups_display,
				'number_header': number_header,
			}
			number_list = number_table_as_list(numbers)
			'''
			if len(number_list) == 1:
				#single numbers are displayed differently:
				number_section['number'] = number_list[0]
			else:
				number_section['number_list'] = number_list
			'''
			number_section['number_list'] = number_list
			#number_section['html'] = render_number_table_as_tree(numbers) #OLD
			#sections.append(number_section)

		elif 'Data' in data and len(data['Data']) > 0:
			numbers = data['Data']
			print('data_type:',data_type)
			if data_type == None:
				number_section_title = 'Data'
			else:
				if data_type.find('[') >= 0:
					number_section_title = 'Polynomials'
				else:
					number_section_title = 'Numbers'				
			number_section = {
				'title': number_section_title,
				'param_groups': param_groups_display,
				'number_header': number_header,
			}
			number_list = number_table_as_list(numbers)
			number_section['number_list'] = number_list

		#html += '</div>'
		#html += '</div>'
		
		context = {
			'table': table,
			'sections': sections,
			'number_section': number_section,
		}
		if not preview:
			context['tags'] = table.tags.all()
		else:
			context['tags'] = []


	except (AttributeError, ValueError, Exception) as e: 
		#TODO: Should remove Exception here after checking which exceptions are expected.
		error_message = 'Error while %s: %s' % (current_job, e)
		raise ValueError(error_message)
	
	return context

def build_preview_context(table_yaml):
	"""Render a table document the way the site will render it.

	Extracted from `preview` so the editor and the preview page cannot drift:
	an editor that previews through different code from the page is worse than
	no preview, because the author trusts it.

	Raises ValueError with a readable message when the document cannot be
	rendered, rather than returning a half-built context.
	"""
	try:
		yaml_data = yaml.load(table_yaml, Loader=yaml.BaseLoader)
	except (yaml.scanner.ScannerError, yaml.composer.ComposerError,
	        yaml.parser.ParserError) as e:
		raise ValueError('YAML format error: %s' % (
			str(e).replace(' in "<unicode string>"', '').replace('^', ''),))

	if not isinstance(yaml_data, dict):
		raise ValueError('A table must be a mapping of sections.')
	if 'Title' not in yaml_data:
		raise ValueError('The table has no Title.')

	c_data = TableData()
	c_data.full_yaml = yaml.dump(normalize_table_data(yaml_data),
	                             sort_keys=False)
	c = Table()
	c.data = c_data
	c.title = yaml_data['Title']
	c.path = 'PATH-OF-COLLECTION-YAML'
	c.tid = 'AUTOMATIC-COLLECTION-ID'

	tags = []
	for tag_name in (yaml_data.get('Tags') or []):
		if isinstance(tag_name, str):
			tags.append(Tag(name=tag_name))

	context = {'preview': True, 'tags': tags}
	context.update(table_context(c, preview=True))
	return context


def preview(request, tid=None):
	#First try to get yaml from Textarea:
	table_yaml = request.GET.get('table',default=None)
	
	#Second try to get yaml from table if tid is give:
	if table_yaml == None:
		print('tid:',tid)
		if tid != None:
			table = Table.objects.get(tid=tid)
			if table != None:
				table_yaml = table.data.raw_yaml
	
	#Third option is: Set table_yaml to default:
	if table_yaml == None:
		table_yaml = \
			'ID: INPUT{id.yaml} #keep this and do not worry\n\n' + \
			'Title: <title>\n\n' + \
			'Definition: >\n' + \
			'  <definition>\n\n' + \
			'Numbers:\n' + \
			'- 3.14\n'
	
	context = {
		'table_yaml': table_yaml,
	}
			
	c_data = TableData()
	try:
		yaml_data = yaml.load(table_yaml,Loader=yaml.BaseLoader)
	except (yaml.scanner.ScannerError, 
			yaml.composer.ComposerError,
			yaml.parser.ParserError) as e:
		print("e:",e)
		messages.error(
			request, 
			'YAML format error: %s' % \
				(e.__str__().replace(' in "<unicode string>"','').replace('^',''),),
		)
		return render(request,'preview.html',context)
	
	
	#Not used currently:
	#c_data.json = normalize_table_data(yaml_data)
	#print("c_data.json:",c_data.json)

	#TODO: Should avoid dumping yaml, and reloading it in table_context():
	c_data.full_yaml = yaml.dump(normalize_table_data(yaml_data),sort_keys=False)
	
	c = Table()
	c.data = c_data
	#c.title = c_data.json['Title']
	c.title = yaml_data['Title']
	c.path = 'PATH-OF-COLLECTION-YAML'
	c.tid = 'AUTOMATIC-COLLECTION-ID'
	
	tags = []
	#if 'Tags' in c_data.json:
	if 'Tags' in yaml_data:
		#for tag_name in c_data.json['Tags']:
		for tag_name in yaml_data['Tags']:
			assert(isinstance(tag_name,str))
			tags.append(Tag(name=tag_name))

	context.update({
		'preview': True,
		'tags': tags,
	})
	
	#print('table_yaml:',table_yaml)
	try:
		c_context = table_context(c,preview=True)
		context.update(c_context)
	except ValueError as e:
		print("e:",e,type(e))
		messages.error(
			request, 
			'%s' % \
				(e.__str__(),), #.replace(' in "<unicode string>"','').replace('^','')
		)
		return render(request,'preview.html',context)
		
	print("context:",context)

	return render(request,'preview.html',context)

def show_own_profile(request):
    return show_profile_of_user(request, request.user)

def show_profile_of_user(request, user):
    context = {
        'user_shown': user,
        'is_self': user.pk == request.user.pk,
    }
    return render(request,'profile-show.html',context)

def show_other_profile(request, other_user_id):
    other_user = get_object_or_404(User, pk=other_user_id)
    return show_profile_of_user(request, other_user)

def edit(request, error_message=""):
    context = {
        'edit_user': request.user,
        'error_message': error_message,
    }
    print("context:",context)
    return render(request,'profile-edit.html',context)

def update(request, user_id):
    #TODO

    user = get_object_or_404(User, pk=user_id)
    profile = user.profile
    profile.bio = request.POST['bio']
    profile.save()
    return HttpResponseRedirect(reverse('db:profile'))

def suggestions(request):
	time0 = time()
	
	R = PolynomialRing(QQ,2,'x')
	#print('factor(x^2):',factor(R.gen(0)**2)) #debug
	#print('12.is_squarefree():',ZZ(12).is_squarefree()) #debug: SignalError in Sage 9.3
	
	def wrap_response(entries):
		data = {
			'entries': entries,
			'time_request': "{:.3f}s".format(time()-time0),
		}
		#print("data:",data)
		return JsonResponse(data,safe=True)

	#Was defined here, and only here, which is why a submitted search found no
	#tables while the dropdown above the same box found them. Now shared with
	#search_by_term via search.py, so both ask the question the same way.
	full_text_search_query = full_text_query

	term_entered = request.GET['term']
	term = term_entered.strip(" \n")
	if term == '':
		return wrap_response({})
	
	entries = {}
	i = 0
	suggested_numbers = []
	added_suggested_number_pks =  set()
	
	def add_suggested_numbers():
		nonlocal suggested_numbers
		nonlocal i
		
		for number in suggested_numbers:
			if number.pk in added_suggested_number_pks:
				continue
			else:
				added_suggested_number_pks.add(number.pk)
			table = number.table
			param = number.param_str()
			entry_i = {
				'value': str(i),
				'label': '',
				'type': 'number',
				'title': table.title,
				#Both forms: the query so the server can confirm the entry,
				#the fragment so the browser scrolls. See entry_suffix.
				'url': '/%s%s' % (table.url, entry_suffix(param)),
			}
			if len(param) > 0: 
				entry_i['subtitle'] = '%s (#%s)' % (number.str_short(), param)
			else:
				entry_i['subtitle'] = '%s' % (number.str_short(),)
			if hasattr(number,'query_frac'):
				entry_i['subtitle'] += ' (fractional part)'
			entries[i] = entry_i
			i += 1
			
		suggested_numbers = []
	
	exact_number_not_in_DB = None

	#Searching for exactly given integer:
	query_integers = Number.objects.none()
	n = parse_integer(term)
	if n != None:
		try:
			number = Number(sage_number=n)
		except OverflowError:
			#n cannot be represented as bigint.
			#Thus try to search it as a real number:
			
			exact_number_not_in_DB = n
			number = None
			
		if number != None:
			query_integer = Number.objects.filter(
				number_blob = number.number_blob_bytes(),
				#number_type = Number.NUMBER_TYPE_ZZ,
				number_type = number.number_type,
			)[:1]
			print("number:",number)
			if len(query_integer) > 0:
				suggested_numbers.append(query_integer[0])
			else:
				number = None
		if number == None:
			entry_i = {
				'value': str(i),
				'label': '',
				'type': 'link',
				'title': 'Basic properties of',
				'subtitle': '%s (not in search index)'  % (n,),
				'url': reverse('db:properties',kwargs={'number':str(n)}),
			}
			entries[i] = entry_i
			i += 1
			
	add_suggested_numbers() #Treat integers first

	if i >= 10:
		return wrap_response(entries)
		
	#Searching for rational numbers that are not integers:
	query_rationals = Number.objects.none()
	if '/' in term:
		n = parse_rational_number(term)
		if n != None:
			try:
				number = Number(sage_number=n)
			except OverflowError:
				#n cannot be represented as quotient with default height bound.
				#Thus try to search it as a real number:
				
				exact_number_not_in_DB = n
				number = None		
				
			if number != None:
				query_rational = Number.objects.filter(
					number_blob = number.number_blob_bytes(),
					#number_type = Number.NUMBER_TYPE_QQ,
					number_type = number.number_type,
				)[:1]
				print("number:",number)
				if len(query_rational) > 0:
					suggested_numbers.append(query_rational[0])
				else:
					number = None
			if number == None:
				entry_i = {
					'value': str(i),
					'label': '',
					'type': 'link',
					'title': 'Basic properties of',
					'subtitle': '%s (not in search index)'  % (n,),
					'url': reverse('db:properties',kwargs={
						'numerator': str(n.numerator()),
						'denominator': str(n.denominator()),
					}),
				}
				entries[i] = entry_i
				i += 1
				
		add_suggested_numbers() #Treat rationals second

		if i >= 10:
			return wrap_response(entries)
	

	#Searching for real number up to given precision:
	real_number_not_in_DB = None
	found_as_real_number = False
	
	if exact_number_not_in_DB != None:
		r = RIF(exact_number_not_in_DB)
	else:
		r = parse_real_interval(term)
	if r != None:
		r_query = blur_real_interval(r)
		print("r_query:",r_query)
		#Overlap rather than containment, ranked by how much of each stored
		#interval the query accounts for -- see search.py.
		query_real_intervals = search_real_numbers(r_query, 10-i)
		
		if len(query_real_intervals) > 0:
			found_as_real_number = True
			suggested_numbers += list(query_real_intervals)
			add_suggested_numbers()

			if i >= 10:
				return wrap_response(entries)
				
		else:
			real_number_not_in_DB = r

	#Searching for real numbers by given fractional part:
	query_fractional_part = Number.objects.none()
	f = parse_fractional_part(term)
	if f != None:
		print("f:",f)
		f_query = blur_real_interval(f)
		print("f_query:",f_query)
		#Overlap rather than containment, ranked -- see search.py.
		query_fractional_part = search_fractional_parts(f_query, 10-i)
		for _number in query_fractional_part:
			#Preserved from the annotate() this replaced: the template uses it
			#to mark a hit as matched on the fractional part.
			_number.query_frac = _number.pk
		
		if len(query_fractional_part) > 0:
			found_as_real_number = True
			found_real_numbers = True
			suggested_numbers += list(query_fractional_part)
			add_suggested_numbers()

			if i >= 10:
				return wrap_response(entries)
		
		else:
			real_number_not_in_DB = f

	if found_as_real_number == False and real_number_not_in_DB != None:
		number = real_number_not_in_DB
		if number != None:
			entry_i = {
				'value': str(i),
				'label': '',
				'type': 'link',
				'title': 'Basic properties of' ,
				'subtitle': '%s (not in database)' % (number,),
				'url': reverse('db:properties',kwargs={'number':real_interval_to_string_via_endpoints(number)}),
			}
			entries[i] = entry_i
			i += 1
	
	add_suggested_numbers()
	
	if i >= 10:
		return wrap_response(entries)
		
		#Searching for rational numbers that are not integers:

	#Searching for p-adic numbers:
	query_p_adics = NumberPAdic.objects.none()
	n = parse_p_adic(term)
	if n != None:
		#The query's precision is no longer capped. The cap was a workaround for
		#the search finding only stored values *inside* the query: a precise
		#query produced a long string that no shorter stored string could start
		#with, so it had to be blunted until it was coarser than everything
		#stored. That masked the asymmetry rather than fixing it, and it held
		#only as long as every stored value stayed more precise than the cap.
		#Coarser stored values are now found directly, so the query keeps the
		#precision the user gave it.
		number = NumberPAdic(sage_number=n)
			
		if number != None:
			print("number:",number)
			query_p_adics = search_p_adic_numbers(
				number.number_string, int(10-i))
			print("query_p_adics:",query_p_adics)
			suggested_numbers += list(query_p_adics)
			#print("suggested_numbers:",suggested_numbers)
			add_suggested_numbers()

		if i >= 10:
			return wrap_response(entries)

	#Searching for complex numbers:
	if 'i' in term.lower().replace('j','i'):
		query_complex = NumberComplex.objects.none()
		n = parse_complex_interval(term)
		if n != None:
			#The query's precision is no longer capped here. It had to be,
			#because the Z-order prefix search could only find cells inside the
			#query: a precise query produced a long searchstring that no
			#shorter stored string could start with, so nothing matched. Box
			#overlap is symmetric, so a precise query finds coarser stored
			#values on its own and the query keeps its precision.
			query_complex = search_complex_numbers(n, int(10-i))
			print("query_complex:",query_complex)
			suggested_numbers += list(query_complex)
			#print("suggested_numbers:",suggested_numbers)
			add_suggested_numbers()

			if i >= 10:
				return wrap_response(entries)

	#Searching for polynomials:
	query_polynomial = Polynomial.objects.none()
	n = parse_polynomial(term)
	if n != None and n.number_of_terms() >= 2:
		polynomial = Polynomial(sage_polynomial=n)
			
		if polynomial != None:
			print("polynomial:",polynomial)
			print("number_string:",polynomial.number_string)
			print("hash:",polynomial.number_string_hash)
			query_polynomials = Polynomial.objects.filter(
				number_string_hash = polynomial.number_string_hash,							
				number_string = polynomial.number_string,
			)[:int(10-i)]
			print("query_polynomials:",query_polynomials)
			if len(query_polynomials) > 0:
				suggested_numbers += list(query_polynomials)
				#print("suggested_numbers:",suggested_numbers)
				add_suggested_numbers()
			elif polynomial.variable_count > 0:
				entry_i = {
					'value': str(i),
					'label': '',
					'type': 'link',
					'title': 'Basic properties of',
					'subtitle': '%s (not in search index)'  % (n,),
					'url': reverse('db:properties',kwargs={
						'number': quote_plus(str(n).replace(' ','')),
					}),
				}
				entries[i] = entry_i
				i += 1

		if i >= 10:
			return wrap_response(entries)
	
	#Searching for tag names:
	if ':' not in term and '^' not in term:
		search_query = full_text_search_query(term)
		rank = SearchRank(F('search_vector'), search_query)
		query_tags = Tag.objects.annotate(rank=rank).filter(rank__gte=0.01).order_by('-rank')[:(10-i)]
		
		#OLD: Simpler query:
		#query_tags = Tag.objects.filter(search_vector = term)[:(10-i)]
		
		for tag in query_tags:
			entry_i = {
				'value': str(i),
				'label': '',
				'type': 'tag',
				'title': '<div class="tag">%s</div>' % (tag.name,),
				'subtitle': '%s table%s, %s number%s' % (
					tag.table_count,
					's' if tag.table_count != 1 else '',
					tag.number_count,
					's' if tag.number_count != 1 else '',
				),
				'url': reverse('db:tag', kwargs={'tag_url': tag.url()}),
			}
			entries[i] = entry_i
			i += 1

		if i >= 10:
			return wrap_response(entries)
		
	#Searching for tables:
	if ':' not in term and '^' not in term:
		search_query = full_text_search_query(term)
		rank = SearchRank(F('search_vector'), search_query)
		query_tables = TableSearch.objects.annotate(rank=rank).filter(rank__gte=0.01).order_by('-rank')[:(10-i)]
		
		#OLD: Simpler query:
		#query_tables = TableSearch.objects.filter(search_vector = term)[:(10-i)]
		
		for c_search in query_tables:
			table = c_search.table
			entry_i = {
				'value': str(i),
				'label': '',
				'type': 'table',
				'title': table.title,
				'url': '/%s' % (table.url,),
			}
			if table.number_count != 1:
				entry_i['subtitle'] = '%s numbers' % table.number_count
			else:
				number = table.numbers.first()
				entry_i['subtitle'] = '%s' % (number.str_as_real_interval(),)
			entries[i] = entry_i
			i += 1
			
	return wrap_response(entries)

def properties_of_rational(request, numerator, denominator):
	return properties(request, '%s/%s' % (numerator, denominator))

def properties(request, number):

	#Deliberately NOT unquote_plus(number): Django has already percent-decoded
	#the path segment, so decoding again is a second pass over decoded text.
	#unquote_plus additionally maps '+' to a space -- form-encoding semantics,
	#wrong for a path -- which silently corrupted every documented format
	#containing a plus:
	#
	#  '3.14 +/- 2e-2'  -> '3.14  /- 2e-2'     (real ball)
	#  '3 + O(2^5)'     -> '3   O(2^5)'        (p-adic)
	#  '2^0+2^1+O(2^5)' -> '2^0 2^1 O(2^5)'    (p-adic)
	#
	#all of which then failed to parse and 404'd. Nothing in the app builds
	#/properties/ URLs, so there is no producer relying on '+' meaning space.
	
	def wrap_response(context):
		print("context:",context)
		return render(request,'properties.html',context)

	def append_oeis_context(n, context, page=1):
		context['OEIS_href'] = 'https://oeis.org/search?q=%s' % (n,)
		try:
			#Check whether n is small enough for database:
			np.int64(n)
		except OverflowError:
			return context
			
		
		#oeis_number = OeisNumber.objects.get(number=int(n))
		oeis_sequences = OeisSequence.objects.filter(numbers__number = n).order_by('a_number')
		
		paginator = Paginator(oeis_sequences, 100)
		try:
			shown_oeis_sequences = paginator.page(page)
		except PageNotAnInteger:
			shown_oeis_sequences = paginator.page(1)
		except EmptyPage:
			shown_oeis_sequences = paginator.page(paginator.num_pages)
		
		#print('oeis_sequences:',oeis_sequences)
		context['show_OEIS_sequences'] = True
		context['OEIS_sequences'] = shown_oeis_sequences
		context['integer'] = n

		return context
		
	def append_factorization_to_context(n, context):
		#Prime factorization:
		factorization = factor_with_timeout(n)
		if factorization != None:
			context['properties'].append({
				'title': 'Prime factorization',
				'plain': str(factorization),
				'latex': '$%s$' % (latex(factorization),),
			})
		else:
			timeout_message = 'The factorization timed out.'
			context['properties'].append({
				'title': 'Prime factorization',
				'plain': timeout_message,
				'latex': timeout_message,
			})
		return context

	def append_context_for_integer(n, context):
		context = append_factorization_to_context(n, context)
			
		special_families = []
		if n.is_perfect_power():
			special_families.append('perfect power')
		if n.is_prime():
			special_families.append('prime')
		if n.is_prime_power():
			special_families.append('prime power')
		try:
			if n.is_squarefree():
				special_families.append('squarefree')
		except SignalError:
			pass
		if n.is_square():
			special_families.append('square')
		if len(special_families) > 0:
			context['properties'].append({
				'title': 'Belongs to special families',
				'plain': ', '.join(special_families),
				'latex': ', '.join(special_families),
			})

		try:
			wiki_number = WikipediaNumber.objects.get(number=n)
			context['Wiki_href'] = wiki_number.url
		except WikipediaNumber.DoesNotExist:
			pass
			
		context = append_oeis_context(n, context)
			
		return context
		
	def append_context_for_rational_number(n, context):
		context = append_factorization_to_context(n, context)
		
		return context
	
	context = {
		'properties': [],
	}
	
	#If oeis_page is given, we are only interested in returning more oeis-sequences.
	oeis_page = request.GET.get('oeis_page', None)
	if oeis_page != None:
		n = parse_integer(number)
		if n != None:
			context = append_oeis_context(n, context, oeis_page)
			if 'show_OEIS_sequences' in context:
				return wrap_response(context)	
	
	
	#Case 1: given number is an integer:
	n = parse_integer(number)
	if n != None:
		context['number'] = n
		context['properties'].append({
			'title': 'Number',
			'plain': str(n),
			'latex': '$%s$' % (latex(n),),
		})
		append_context_for_integer(n, context)
		return wrap_response(context)

	#Case 2: given number is a rational number:
	if '/' in number:
		n = parse_rational_number(number)
		if n != None:
			context['number'] = n
			context['properties'].append({
				'title': 'Number',
				'plain': str(n),
				'latex': '$%s$' % (latex(n),),
			})
			append_context_for_rational_number(n, context)
			return wrap_response(context)

	#Case 3: given number is real interval:
	r = parse_real_interval(number)
	if r != None:
		print("r:",r)
		context['number'] = r
		context['properties'].append({
			'title': 'Number',
			'plain': str(r),
			'latex': '$%s$' % (latex(r),),
		})
	
		#Simplest rational:
		q = r.simplest_rational()
		context['properties'].append({
			'title': 'Simplest contained rational number',
			'plain': str(q),
			'latex': '$%s$' % (latex(q),),
		})
		
		#Continued fraction:
		#Check first whether anything is determined: an interval wide enough to
		#contain several integers (e.g. "12e2" = [1100, 1300]) pins down no
		#partial quotient at all, and asking Sage for the empty continued
		#fraction raises. The 'Insufficient precision.' branch below was always
		#the intended answer; it was simply unreachable.
		cf = StableContinuedFraction(r)
		cf_sage = cf.sage() if cf.determined_coefficients() else None
		if cf_sage is not None and len(cf_sage) > 0:
			context['properties'].append({
				'title': 'Continued fraction',
				'latex': '$%s$' % (cf.latex(),),
				'plain': str(cf),
			})
			
			#Convergents:
			convergents = cf_sage.convergents()
			context['properties'].append({
				'title': 'Convergents',
				'plain': ', '.join(str(convergent) for convergent in convergents),
				'latex': ', '.join('$%s$' % (latex(convergent),) for convergent in convergents),
			})
		else:
			precision_message = 'Insufficient precision.'
			context['properties'].append({
				'title': 'Possible continued fraction',
				'latex': precision_message,
				'plain': precision_message,
			})
			context['properties'].append({
				'title': 'Convergents',
				'plain': precision_message,
				'latex': precision_message,
			})
			
		minpolys = {}
		for deg in range(1,10+1):
			try:
				f = r.algdep(deg)
			except ValueError:
				continue
			if f.degree() == deg:
				if f(r).contains_zero():
					if f.is_irreducible():
						minpolys[deg] = f
		if len(minpolys) > 0:
			context['properties'].append({
				'title': 'Possible algebraic dependences',
				'plain': '<br> '.join('%s = 0' % (f,) for f in minpolys.values()), 
				'latex': '<br> '.join('$%s = 0$' % (latex(f),) for f in minpolys.values()), 
			})
		else:
			empty_message = 'No heuristic algebraic dependencies up to degree 10 found.'
			context['properties'].append({
				'title': 'Possible algebraic dependences',
				'plain': empty_message, 
				'latex': empty_message, 
			})
		
		context['ISC_href'] = 'http://wayback.cecm.sfu.ca/cgi-bin/isc/lookup?number=%s&lookup_type=simple' % (r.center(),)
		
		try:
			n = r.unique_integer()
			context['properties'].append({
				'title': 'Unique integer contained in this real interval',
				'plain': str(n), 
				'latex': '$%s$' % latex(n), 
			})
			append_context_for_integer(n, context)			
		except ValueError:
			pass
		
		return wrap_response(context)

	#Case 4: given number is actually a polynomial over Q:
	r = parse_polynomial(number)
	if r != None:
		print("r:",r)
		context['polynomial'] = r
		context['properties'].append({
			'title': 'Polynomial',
			'plain': str(r),
			'latex': '$%s$' % (latex(r),),
		})
	
		#Factorization:
		f = None
		#f = factor(r)
		try:
			f = r.factor()
			#f = factor(r)
		except SignalError:
			print('Signal error during factorization.')
			pass
			
		if f != None:
			context['properties'].append({
				'title': 'Factorization',
				'plain': str(f),
				'latex': '$%s$' % (latex(f),),
			})
		
		return wrap_response(context)

	raise Http404("Number cannot be parsed.")

def advanced_search(request):

	#Warn up front if the sandboxed evaluator is down, rather than letting the
	#user compose an expression and only then discover it cannot be run.
	if not evaluator_is_available():
		messages.error(request, 'Error: The advanced search server is currently not running and has to be restarted. We apologize.')


	#default_program = 'x = 3.14159265\nnumbers = {n: sin(x/n) for n in [1..10]}\n'
	default_program = '{n: sin(pi/n) for n in [1..10]}\n'
	#default_program = '{n: sin(pi*n/2)\n  for n in [1..10000]\n}\n'
	#default_program = '{n: sin(pi*n/2)\n  for n in [1..10]\n}\n'
	#default_program = '{n: sin(1/n) for n in [1..10]}\n'
	
	program = request.GET.get('expression',default=None)
	show_results = request.GET.get('results',default='true')

	context = {}
	
	if program == None:
		program = default_program
	else:
		if show_results == 'true':
			search_results_context = advanced_search_results(request,return_type='dict')
			print('search_results_context:',search_results_context)
			messages_html = render_to_string(
				'includes/messaging.html',
				context = search_results_context,
			)
			result_html = render_to_string(
				'includes/advanced-search-results.html', 
				context = search_results_context,
			)
			context['search_results'] = {
				'messages_html': messages_html,
				'result_html': result_html,
				'time_request': search_results_context['time_request'],
			}
	context['program'] = program
	
	'''	
	if not request.user.is_authenticated:	
		print("not authenticated")
		messages.error(request, 'You need to be logged in to use advanced search.')
	'''
	
	return render(request, 'advanced-search.html', context)

	
def debug(request):
	if settings.DEBUG:
		context = {}
		return render(request,'debug.html',context)
	raise Http404()
	
def table_history(request, tid=None):
	page = request.GET.get('page', 1)
	print('tid:',tid)
	#if tid != None:
	table = Table.objects.get(tid=tid)
	commits = table.commits.all()
	sortby_default = 'time'
	sortby = request.GET.get('sort_by',default=sortby_default)
	order_by_map = {
		'time': ['-datetime'],
		'author': ['contributor__author', '-datetime'],
	}
	if sortby not in order_by_map:
		sortby = sortby_default
	commits = commits.order_by(*order_by_map[sortby])
	paginator = Paginator(commits, 50)
	try:
		shown_commits = paginator.page(page)
	except PageNotAnInteger:
		shown_commits = paginator.page(1)
	except EmptyPage:
		shown_commits = paginator.page(paginator.num_pages)
	context = {
		'table': table,
		'tags': table.tags.all(),
		'commits': shown_commits,
		'sortby': sortby,
	}
	return render(request, 'table-history.html', context)


@login_required
def edit_table(request, tid):
	"""Edit a table's source and save it as a new revision.

	Built on the preview machinery rather than beside it, so what an author
	sees before saving is produced by the same code that renders the table
	afterwards. A preview that renders differently from the page is worse than
	no preview, because it is trusted.

	Saving publishes immediately. What the author does not get automatically is
	review: unless they are on the board, the entries they changed are marked
	and held out of search by number until somebody confirms them.
	"""
	from .limits import EXCEPTION_KEY, TooBig
	from .editing import (InvalidDocument, ParametersChanged, StaleEdit,
	                      commit_table,
	                      tree_of)
	from .permissions import is_board_member

	table = get_object_or_404(Table, tid=tid)
	base = table.head_revision

	if request.method == 'POST':
		table_yaml = request.POST.get('table', '')
		base_digest = request.POST.get('base', '')
		#The revision the author actually saw, carried through the form. Without
		#it a save would silently apply to whatever head had become, which is
		#the stale write this whole design exists to prevent.
		if base_digest:
			base = TableRevision.objects.filter(
				table=table, digest=base_digest).first() or base

		try:
			tree = yaml.load(table_yaml, Loader=yaml.BaseLoader)
		except yaml.YAMLError as e:
			messages.error(request, 'YAML format error: %s' % (
				str(e).replace(' in "<unicode string>"', ''),))
			return render(request, 'edit.html', _edit_context(
				request, table, table_yaml, base))

		if not isinstance(tree, dict):
			messages.error(request, 'A table must be a mapping of sections.')
			return render(request, 'edit.html', _edit_context(
				request, table, table_yaml, base))

		#Nothing is written until the author has asked for it. Rendering first
		#is not a nicety here: a table is mostly numbers, and the difference
		#between a correct edit and a damaging one is often a single character
		#that only becomes visible once the page is drawn.
		action = request.POST.get('action', 'save')
		if action in ('preview', 'diff'):
			context = _edit_context(request, table, table_yaml, base)
			if action == 'diff':
				context['diff'] = _diff_against(base, table_yaml)
				if not context['diff']:
					messages.info(request, 'No changes yet.')
			return render(request, 'edit.html', context)

		from .editing import with_managed_keys
		tree = with_managed_keys(tree, table)

		try:
			outcome = commit_table(
				table, tree,
				author=request.user,
				message=request.POST.get('message', '').strip(),
				base=base,
			)
		except ParametersChanged as changed:
			messages.error(request, (
				'This edit changes the table\'s parameters, from %s to %s. '
				'Nothing has been saved. Every entry is identified by its '
				'parameter values, so changing them silently reassigns every '
				'identity in the table: existing links and references would '
				'still work and would point at different numbers. If the table '
				'really needs different parameters, that is a separate '
				'operation, not an edit.'
				% (', '.join(changed.before), ', '.join(changed.after) or 'none')))
			return render(request, 'edit.html', _edit_context(
				request, table, table_yaml, base))
		except StaleEdit as stale:
			messages.error(request, (
				'Somebody else changed this table while you were editing, and '
				'your changes overlap theirs in %d place(s). Nothing has been '
				'saved.' % (len(stale.conflicts),)))
			context = _edit_context(request, table, table_yaml, stale.head)
			context['conflicts'] = stale.conflicts
			return render(request, 'edit.html', context)
		except InvalidDocument as bad:
			messages.error(request, (
				'Nothing has been saved. The document is valid YAML but one of '
				'its values cannot be read as a number: %s. Check the entry it '
				'names, and remember that a value is text -- 3.14, not a '
				'quoted sentence.' % (bad,)))
			return render(request, 'edit.html', _edit_context(
				request, table, table_yaml, base))
		except TooBig as big:
			messages.error(request, (
				'Nothing has been saved. %s. These are the limits past which '
				'the editor and the diff stop working, so no reason makes it '
				'workable; a table this large wants to be several tables, or '
				'a program.'
				% ('; '.join(b.message for b in big.breaches).capitalize(),)))
			return render(request, 'edit.html', _edit_context(
				request, table, table_yaml, base))

		if outcome.unchanged:
			messages.info(request, 'No changes to save.')
		elif outcome.merged:
			messages.success(request, (
				'Saved, and merged with a change somebody else made while you '
				'were editing. The table now contains both.'))
		else:
			messages.success(request, 'Saved.')

		#Saved either way: the author may well have a good reason, and the
		#review queue is a better place to weigh one than a form that refuses.
		for breach in outcome.breaches:
			messages.warning(request, (
				'Saved, but %s. If that is deliberate, please say why in a '
				'"%s" line under Data properties; a reviewer will otherwise '
				'have to guess.' % (breach.message, EXCEPTION_KEY)))

		#An edit by somebody with a confirmed track record publishes as
		#reviewed. Requiring a board member to review their own work would be a
		#queue of one person's edits waiting for that same person, and
		#requiring it of a trusted account turns review into a formality that
		#teaches reviewers to click through. Everybody else waits.
		from .permissions import edits_are_reviewed
		if outcome.revision and edits_are_reviewed(request.user):
			table.reviewed_at_revision = outcome.revision
			table.save(update_fields=['reviewed_at_revision'])
			from .review import sync_review_flags
			sync_review_flags(table)

		return HttpResponseRedirect(reverse('db:table_by_url',
		                                    kwargs={'url': table.url}))

	#full_yaml, not raw_yaml. The raw file is what a contributor wrote for the
	#data repository, and for 30 tables that means `Numbers: INPUT{numbers.yaml}`
	#-- a macro pointing at a sibling file. Seeding the editor from it would show
	#somebody a macro instead of their numbers, and saving would store the macro
	#as literal text: T92 would go from 1024 values to one entry whose value is
	#the string "INPUT{numbers.yaml}". full_yaml is the same document with those
	#references already resolved, which is what the site renders and what the
	#revision should record.
	source = (base.content if base is not None
	          else (table.data.full_yaml if hasattr(table, 'data') else ''))
	#The identifier is the site's, not the author's, so it is not shown.
	try:
		from .editing import dump_tree, without_managed_keys
		source = dump_tree(without_managed_keys(
			yaml.load(source, Loader=yaml.BaseLoader) or {}))
	except yaml.YAMLError:
		pass
	return render(request, 'edit.html',
	              _edit_context(request, table, source, base))


def _diff_against(base, table_yaml, before_label='saved version',
                  after_label='your version'):
	"""A unified diff between the stored revision and what is in the box.

	Shown on request rather than always: for a table of a thousand entries the
	diff is the only practical way to see what an edit did, and the rendered
	preview is the only practical way to see whether it is right. They answer
	different questions, so Wikipedia offers both and so does this.
	"""
	import difflib

	before = (base.content if base is not None else '').splitlines(keepends=True)
	after = table_yaml.splitlines(keepends=True)
	lines = list(difflib.unified_diff(
		before, after,
		fromfile=before_label, tofile=after_label, n=2))
	#The first two lines are the ---/+++ headers, which say nothing a reader
	#does not already know from the surrounding page.
	return ''.join(lines[2:]) if lines else ''


def _edit_context(request, table, table_yaml, base):
	"""The editor, plus a preview rendered from what is in the box."""
	from .permissions import is_board_member

	context = {
		'table_being_edited': table,
		'table_yaml': table_yaml,
		'base_digest': base.digest if base is not None else '',
		'is_board_member': is_board_member(request.user),
		'preview': True,
	}
	#Rendered through the same path as /preview, so a document that cannot be
	#rendered is reported while it is being written rather than after it has
	#been saved.
	try:
		context.update(build_preview_context(table_yaml))
	except ValueError as e:
		messages.error(request, str(e))
	except Exception as e:                            # pragma: no cover
		messages.error(request, 'Could not render a preview: %s' % (e,))
	return context


@login_required
def review_queue(request):
	"""Tables carrying changes nobody has confirmed.

	The queue exists because publication and indexing are separate here: an
	unreviewed edit is already on its page, and what it is waiting for is
	admission to search by number. So this is not a gate somebody is stuck
	behind, and the cost of a long queue is a search that quietly covers less
	than it could, which is exactly the sort of decay that needs to be visible
	somewhere.
	"""
	from .permissions import is_board_member
	from .review import ALL_UNREVIEWED, unreviewed_params

	if not is_board_member(request.user):
		raise Http404()

	waiting = []
	for table in (Table.objects.exclude(head_revision=None)
	                           .select_related('head_revision',
	                                           'reviewed_at_revision')):
		outstanding = unreviewed_params(table)
		if outstanding is ALL_UNREVIEWED:
			count, whole = table.number_count, True
		elif outstanding:
			count, whole = len(outstanding), False
		else:
			continue
		waiting.append({
			'table': table,
			'count': count,
			'whole_table': whole,
			'head': table.head_revision,
			'since': table.reviewed_at_revision,
		})

	waiting.sort(key=lambda w: w['head'].created, reverse=True)
	return render(request, 'review-queue.html', {'waiting': waiting})


@login_required
def review_table(request, tid):
	"""Look at what changed in one table, and confirm it.

	Confirming moves the reviewed pointer to the current head, which is what
	admits the changed values back into search by number. It deliberately does
	not mean "these numbers are correct": it means somebody competent looked.
	The distinction matters when deciding who to add to the board.
	"""
	from .editing import tree_of
	from .permissions import is_board_member
	from .review import ALL_UNREVIEWED, sync_review_flags, unreviewed_params

	if not is_board_member(request.user):
		raise Http404()

	table = get_object_or_404(Table, tid=tid)
	head = table.head_revision
	if head is None:
		raise Http404('This table has no revisions to review.')

	if request.method == 'POST':
		#Confirming is recorded against the revision that was on screen, not
		#against whatever head has become: approving work nobody looked at is
		#the one thing a review queue must not do.
		seen = request.POST.get('head', '')
		if seen and seen != head.digest:
			messages.error(request, (
				'This table changed again while you were looking at it. '
				'Nothing was confirmed; the newer changes are shown now.'))
			return HttpResponseRedirect(reverse('db:review-table',
			                                    kwargs={'tid': table.tid}))
		table.reviewed_at_revision = head
		table.save(update_fields=['reviewed_at_revision'])
		marked = sync_review_flags(table)
		messages.success(request, (
			'Confirmed. %s'
			% ('Nothing is now waiting on this table.' if not marked
			   else '%d entries are still marked.' % (marked,))))
		return HttpResponseRedirect(reverse('db:review-queue'))

	outstanding = unreviewed_params(table)
	before = tree_of(table.reviewed_at_revision)
	after = tree_of(head)
	return render(request, 'review-table.html', {
		'table_being_reviewed': table,
		'head': head,
		'since': table.reviewed_at_revision,
		'whole_table': outstanding is ALL_UNREVIEWED,
		'outstanding': sorted(outstanding) if outstanding is not ALL_UNREVIEWED else [],
		'diff': _diff_against(table.reviewed_at_revision, head.content),
		'history': table.revisions.all()[:20],
	})


@login_required
def new_table(request):
	"""Create a table here rather than in the data repository.

	This is the last thing that made the repository a source of truth: as long
	as tables could only come into existence there, the import had to keep the
	authority to create them, and "the database is the store of record" was
	true of edits but not of existence.

	The T-number is allocated by the database now. It used to come from
	`next_ids.yaml`, a file the repository maintained and whose first line told
	everybody not to edit it -- which is a fair sign that it wanted to be a
	sequence in a database rather than a file in git.
	"""
	from .editing import NEW_TABLE_TEMPLATE, create_table

	if request.method == 'POST':
		table_yaml = request.POST.get('table', '')
		try:
			tree = yaml.load(table_yaml, Loader=yaml.BaseLoader)
		except yaml.YAMLError as e:
			messages.error(request, 'YAML format error: %s' % (
				str(e).replace(' in "<unicode string>"', ''),))
			return render(request, 'new-table.html',
			              _new_table_context(request, table_yaml))

		action = request.POST.get('action', 'save')
		if action == 'preview' or not isinstance(tree, dict):
			if not isinstance(tree, dict):
				messages.error(request, 'A table must be a mapping of sections.')
			return render(request, 'new-table.html',
			              _new_table_context(request, table_yaml))

		try:
			table = create_table(tree, author=request.user,
			                     message=request.POST.get('message', '').strip())
		except ValueError as e:
			messages.error(request, str(e))
			return render(request, 'new-table.html',
			              _new_table_context(request, table_yaml))

		from .permissions import edits_are_reviewed
		if edits_are_reviewed(request.user):
			table.reviewed_at_revision = table.head_revision
			table.save(update_fields=['reviewed_at_revision'])
			from .review import sync_review_flags
			sync_review_flags(table)

		messages.success(request, (
			'Created %s. Its identifier is %s, which is permanent; the address '
			'below can change if the title does.'
			% (table.title, table.tid)))
		return HttpResponseRedirect(reverse('db:table_by_url',
		                                    kwargs={'url': table.url}))

	return render(request, 'new-table.html',
	              _new_table_context(request, NEW_TABLE_TEMPLATE.format(
		              title='A short, descriptive title')))


def _new_table_context(request, table_yaml):
	from .permissions import is_board_member

	context = {
		'table_yaml': table_yaml,
		'is_board_member': is_board_member(request.user),
		'preview': True,
	}
	try:
		context.update(build_preview_context(table_yaml))
	except ValueError as e:
		messages.error(request, str(e))
	return context


def revision_history(request, tid):
	"""Every version of a table, with a way to compare and to go back.

	The history the site keeps and the history the data repository keeps are
	different things -- the repository's commits are how a table arrived, the
	revisions are what has happened to it since -- so both are shown, the
	revisions first because they are the ones that can be acted on.
	"""
	from .editing import restore_revision
	from .permissions import may_edit

	table = get_object_or_404(Table, tid=tid)
	revisions = list(
		table.revisions.select_related('author', 'contributor').all()[:200])

	if request.method == 'POST':
		if not may_edit(request.user):
			return HttpResponseRedirect(
				'%s?next=%s' % (reverse('account_login'), request.path))
		#By row rather than by digest: the digest is content-addressed, so a
		#restore produces a revision whose digest already exists, and "restore
		#the one with this content" would then be an ambiguous request.
		revision = table.revisions.filter(
			pk=_as_int(request.POST.get('restore'))).first()
		if revision is None:
			messages.error(request, 'No such revision.')
		elif revision.pk == table.head_revision_id:
			messages.info(request, 'That is already the current version.')
		else:
			restore_revision(table, revision, author=request.user)
			messages.success(request, (
				'Restored the version from %s. This is a new revision rather '
				'than an erasure: what happened in between is still here.'
				% (revision.created.strftime('%Y-%m-%d %H:%M'),)))
			from .permissions import edits_are_reviewed
			if edits_are_reviewed(request.user):
				table.refresh_from_db()
				table.reviewed_at_revision = table.head_revision
				table.save(update_fields=['reviewed_at_revision'])
				from .review import sync_review_flags
				sync_review_flags(table)
		return HttpResponseRedirect(reverse('db:revision-history',
		                                    kwargs={'tid': table.tid}))

	#Comparing two versions. Defaults to "this one against the one before it",
	#which is the question somebody looking at a history almost always has.
	by_id = {r.pk: r for r in revisions}
	to_revision = by_id.get(_as_int(request.GET.get('to')))
	if to_revision is None and revisions:
		to_revision = revisions[0]
	asked_from = _as_int(request.GET.get('from'))
	if asked_from is not None:
		from_revision = by_id.get(asked_from)
	elif to_revision is not None:
		later = [r for r in revisions if r.created < to_revision.created]
		from_revision = later[0] if later else None
	else:
		from_revision = None

	diff = ''
	if to_revision is not None:
		diff = _diff_against(
			from_revision, to_revision.content,
			before_label=(_revision_label(from_revision)
			              if from_revision is not None else 'nothing'),
			after_label=_revision_label(to_revision))

	return render(request, 'revision-history.html', {
		'table': table,
		'revisions': revisions,
		'head': table.head_revision,
		'reviewed_at': table.reviewed_at_revision,
		'from_revision': from_revision,
		'to_revision': to_revision,
		'diff': diff,
		'may_edit': may_edit(request.user),
	})


def _revision_label(revision):
	"""How a revision is named to a reader: when, and by whom."""
	if revision.author_id:
		who = revision.author.username
	elif revision.contributor_id:
		who = revision.contributor.author
	else:
		who = revision.produced_by or 'unknown'
	return '%s by %s' % (revision.created.strftime('%Y-%m-%d %H:%M'), who)


def _as_int(text):
	"""A query parameter read as a row id, or None if it is not one.

	Anything can arrive in a query string, and a `ValueError` from `int()`
	would be a 500 for what is really just a malformed link.
	"""
	try:
		return int(text)
	except (TypeError, ValueError):
		return None


def table_files(request, tid):
	"""The files a table carries, as of one revision.

	Defaults to the current one; `?rev=` names any other, which is what makes a
	citation of "the code that produced these numbers" mean something. An older
	revision keeps its own manifest, so the address stays honest after the
	script is rewritten.
	"""
	from .editing import manifest_of

	table = get_object_or_404(Table, tid=tid)
	revision = None
	asked = _as_int(request.GET.get('rev'))
	if asked is not None:
		revision = table.revisions.filter(pk=asked).first()
	if revision is None:
		revision = table.head_revision

	files = []
	if revision is not None:
		files = list(revision.attachments.select_related('blob').all())

	return render(request, 'table-files.html', {
		'table': table,
		'revision': revision,
		'is_current': revision is not None
		              and revision.pk == table.head_revision_id,
		'files': files,
	})


def table_file(request, tid, name):
	"""One file, shown as source or handed over as a download."""
	from django.http import HttpResponse

	table = get_object_or_404(Table, tid=tid)
	revision = None
	asked = _as_int(request.GET.get('rev'))
	if asked is not None:
		revision = table.revisions.filter(pk=asked).first()
	if revision is None:
		revision = table.head_revision
	if revision is None:
		raise Http404('this table has no revisions')

	attachment = revision.attachments.select_related('blob').filter(
		name=name).first()
	if attachment is None:
		raise Http404('no such file on this revision')

	text = attachment.blob.text() if attachment.is_source else None
	if request.GET.get('raw') or text is None:
		#Never text/html or anything else a browser will execute: these bytes
		#were uploaded by a contributor, and the site must not become a way to
		#serve a script from numberdb.org's own origin.
		response = HttpResponse(bytes(attachment.blob.content),
		                        content_type='application/octet-stream')
		response['Content-Disposition'] = (
			'attachment; filename="%s"' % (name.rsplit('/', 1)[-1],))
		response['X-Content-Type-Options'] = 'nosniff'
		return response

	return render(request, 'table-file.html', {
		'table': table,
		'revision': revision,
		'is_current': revision.pk == table.head_revision_id,
		'attachment': attachment,
		'text': text,
	})
