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
from .models import Comment

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

from data_pipeline.utils import normalize_table_data
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

def skill(request):
	"""Serve the agent skill as plain markdown.

	The same file the repository holds at
	`.claude/skills/numberdb-table/SKILL.md`, read at request time rather than
	copied, because two copies of instructions drift and the drifting one is
	always the one somebody is reading.

	Markdown rather than a rendered page: the audience is a program being told
	how to contribute a table, and it wants the source. A person who follows
	the link gets something perfectly readable anyway.
	"""
	import os

	from django.conf import settings
	from django.http import Http404, HttpResponse

	path = os.path.join(settings.BASE_DIR, '.claude', 'skills',
	                    'numberdb-table', 'SKILL.md')
	try:
		with open(path, encoding='utf8') as handle:
			body = handle.read()
	except OSError:
		raise Http404('the skill is not installed on this server')
	return HttpResponse(body, content_type='text/markdown; charset=utf-8')


def llms_txt(request):
	"""An index of this site for a language model, at the conventional path.

	`/llms.txt` (llmstxt.org) is the nearest thing to a convention for "where
	are your documents": a short markdown file at the root, listing the pages
	worth reading and what each is. Nothing makes an arbitrary path like
	`/skill` discoverable on its own, and an assistant asked to contribute a
	table should not have to guess.

	Short on purpose. A list of everything is a list nobody reads.
	"""
	from django.http import HttpResponse

	body = """# NumberDB

> A collaborative database of numbers and polynomials: integers, rationals,
> reals, complex numbers, p-adics and polynomials over Z and Q, indexed so that
> a value can be identified from its digits. Every table states how well its
> digits are known.

## For assistants contributing a table

- [Skill: making a NumberDB table](https://numberdb.org/skill): the value types
  and how each is written, size limits, the rigour levels, what each refusal
  from the `numberdb` package means, and what a table's definition has to pin
  down. Plain markdown.
- [Python package](https://pypi.org/project/numberdb/): `pip install numberdb`.
  Search, fetch a table, or publish one with a generator.
- [Web API](https://numberdb.org/api/docs): search and read without a key;
  writing needs one.

## For readers

- [Help](https://numberdb.org/help): how to search, what a written value means,
  and how accurate the numbers are.
- [Tables](https://numberdb.org/tables): the corpus.
- [Source](https://github.com/numberdb/numberdb-website) and
  [data](https://github.com/numberdb/numberdb-data).
"""
	return HttpResponse(body, content_type='text/markdown; charset=utf-8')


def about(request):
	"""Kept as a redirect, because /about had been linked to for years.

	The page itself is gone. It duplicated the help page's Welcome and
	Acknowledgements almost word for word -- stale copies, with example links
	to /C1, /C2 and /C9, which have been 404 since tables were renumbered to
	T-ids -- and its only unique content, the roadmap, has moved to
	`#section-work-in-progress` on the help page, where the "beta" link on the
	front page now points.

	A temporary redirect rather than a permanent one. 301s are cached by
	browsers for a very long time and are correspondingly hard to take back,
	and an "about" page is an ordinary thing for a site to want again later.
	Nothing here rests on consolidating the URL.
	"""
	from django.shortcuts import redirect

	return redirect('db:help')

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

def drafts(request):
	"""Tables being set up, for anybody signed in.

	Existence, not contents. A draft's numbers are unreviewed and may be wrong,
	which is why they answer no search -- but the reason to hide what is in a
	draft is not a reason to hide *that* it exists, and hiding both is how two
	people end up making the same table.

	Sometimes two tables of the same objects are right: T103 and T104 are the
	Hermite polynomials in the physicists' and the probabilists' conventions,
	held twice on purpose. What this page prevents is the accidental case,
	where nobody knew.

	Age is shown and nothing is enforced. An automatic expiry deletes somebody's
	work on a timer, and the timer is always wrong for somebody.
	"""
	if not request.user.is_authenticated:
		from django.shortcuts import redirect

		#allauth owns the login route; there is no `db:login`.
		return redirect('%s?next=%s' % (reverse('account_login'), request.path))

	from .permissions import draft_allowance, is_board_member

	drafts = (Table.objects.filter(published=False)
	          .select_related('created_by')
	          .order_by('tid_int'))
	remaining, held = draft_allowance(request.user)
	rows = []
	for draft in drafts:
		rows.append({
			'table': draft,
			'mine': draft.created_by_id == request.user.pk,
			'may_offer': (draft.created_by_id == request.user.pk
			              or is_board_member(request.user)),
		})
	return render(request, 'drafts.html', {
		'rows': rows,
		'drafts': drafts,
		'draft_count': drafts.count(),
		'mine': sum(1 for d in drafts if d.created_by_id == request.user.pk),
		'remaining': remaining,
		'held': held,
		'is_board': is_board_member(request.user),
	})


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

	def escape_maths(text):
		"""Author text on its way into a string that already holds markup.

		A table's prose is LaTeX, so a '<' in it is mathematics; but some of
		these strings are assembled here with anchors this code wrote, and
		escaping the finished string prints those anchors at the reader
		instead of following them.
		"""
		return text.replace('<', '&lt;') if isinstance(text, str) else text

	def render_text(text, line_breaks = True, escape = True):
		'''
		Parse text for 'CITE', 'HREF', and '\n', 
		and replace accordingly.

		A table's prose is LaTeX and plain text, never HTML, so a '<' in it is
		mathematics and is escaped before anything else happens here. It is
		escaped rather than left alone because a browser starts a tag at '<'
		followed directly by a letter, and then eats everything up to the next
		'>': T13's comment on sums of powers, which contains
		'\sum_{k<m}', has been rendering as half a sentence, and T130's
		parameter list showed 'argument ()' because '$1<D\leq 1000$' swallowed
		the rest of the section. '$a < b$' with a space was always safe, which
		is why this went unnoticed in a dozen other tables.

		MathJax reads the text after the browser has parsed it, so '&lt;'
		reaches it as a '<' and the mathematics renders correctly.

		The anchors this function builds are added afterwards and are not
		affected.
		'''
		
		if not isinstance(text, str):
			raise ValueError('string expected instead of %s' % text.__class__)
		
		if escape:
			text = text.replace('<', '&lt;')
		
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
		#How a parameter's values are written when they are shown.
		#
		#An entry's identity is its plain value -- `v: b`, which is what a
		#citation resolves on -- and `$b$` is how that value is displayed.
		#Both are needed and they are not the same thing. What is not needed is
		#a copy of the display on every record: it is a property of the value,
		#so it belongs on the parameter, stated once.
		value_display = {}
		for _name, _info in (data.get('Parameters') or {}).items():
			if isinstance(_info, dict) and isinstance(_info.get('values'), dict):
				value_display[_name] = _info['values']

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
					#Escaped, because this is code and the browser reads it as
					#markup otherwise. `R.<x> = ZZ[]` -- the ordinary way to
					#make a polynomial ring in Sage -- rendered as `R. = ZZ[]`,
					#the `<x>` swallowed as a tag, so a reader who copied the
					#program got a syntax error. `&` first, or the escapes
					#introduced below would themselves be escaped.
					code = (program['code']
					        .replace('&', '&amp;')
					        .replace('<', '&lt;')
					        .replace('>', '&gt;'))
					text = '%s<br><pre><code class="table-code language-%s">%s</code></pre>' % (
						language,
						code_language,
						code,
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
			#How well the digits are known: proven, believed on a stated
			#assumption, checked by agreement, or assumed. A table that does
			#not say presents all four identically, which is what this line
			#exists to stop. See docs/design/rigour.md.
			'rigour': 'How well the digits are known',
			#Elaborates the line above: what the method actually was, and what
			#was assumed. Optional, and worth more than the single word when
			#the single word is "assumed-bound".
			'rigour details': 'How they were obtained',
			#'accuracy': 'Accuracy',
		}

		#Properties whose label links to the part of the help that explains
		#them. `rigour` says one word -- `assumed-bound`, `heuristic
		#(agreement-checked)` -- and a reader meeting it on a table has
		#nowhere to find out what it means: nothing linked to that section at
		#all, including from here.
		#
		#Not written as HREF{} markup, which is for the corpus and resolves
		#`/help#how-well-known` into `/help?entry=how-well-known` -- an entry
		#of a table called /help.
		property_help = {
			'rigour': 'how-well-known',
			'rigour details': 'how-well-known',
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
					label = property_names[key]
					anchor = property_help.get(key)
					if anchor:
						label = '<a class="HREF" href="%s#%s">%s</a>' % (
							reverse('db:help'), anchor, label)
					text = "%s: " % (label,)
					if key == 'type':
						data_type = value
						if properties['type'] in type_names:
							text += type_names[value]
						else:
							text += "%s (Unknown value)" % (value,)
					elif key == 'sources':
						text += ", ".join(value)                
					elif key == 'complete':
						text += escape_maths(value)
						note = properties.get('complete-note')
						if note:
							text += " (%s)" % (escape_maths(note),)
					else:
						text += escape_maths(value)
				else:
					text = "%s: %s (Unknown key)" % (
						escape_maths(key), escape_maths(value))
				#Not escaped here: this string already holds the anchor built
				#above, and escaping it printed `<a class="HREF" ...>` at the
				#reader. The author's half was escaped as it went in.
				unlabeled_list.append({
					'text': render_text(text, escape=False),
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
		#What a table says about an entry, shown under the entry.
		#
		#Every row has carried this since the beginning and the template only
		#showed it when there was no number, so it was visible exactly when
		#there was nothing to attach it to. Nine thousand of them were
		#invisible, including "Value is only a heuristic estimate" on T100 and
		#the LMFDB link on every elliptic curve entry.
		#
		#Shown by default, because an author who wrote something about a value
		#meant a reader to see it. A table that would rather not can say so.
		show_entry_notes = True

		if 'Display properties' in data:
			display_properties = data['Display properties']
			if 'entry notes' in display_properties:
				show_entry_notes = (
					str(display_properties['entry notes']).strip().lower()
					not in ('hidden', 'no', 'none', 'off', 'false'))
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
					elif _shown_as(value_display, groups_left, p) is not None:
						param_html = _shown_as(value_display, groups_left, p)
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
						shown = render_text(value)
						#A note that is blank, or only spaces, is not a note.
						#Kept out here rather than hidden in the template so
						#that `extra_info` being non-empty means there is
						#something to show -- the template asks exactly that.
						if not str(shown).strip():
							continue
						extra_info[key] = shown
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
					elif _shown_as(value_display, groups_left, p) is not None:
						param_html = _shown_as(value_display, groups_left, p)
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
				'show_entry_notes': show_entry_notes,
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
				'show_entry_notes': show_entry_notes,
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
		if tid != None:
			#The same guard the table page makes. Without it /preview/T133
			#rendered a private draft to anybody who guessed its number,
			#which is the one thing a draft is supposed not to do: it is
			#invisible, answers no search, and is readable by its author and
			#the board. This route loaded it by tid and asked nothing.
			try:
				table = Table.objects.get(tid=tid)
			except Table.DoesNotExist:
				raise Http404
			_refuse_a_draft(request, table)
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
    """Somebody's profile, including what their account may do here.

    Standing was not shown anywhere. An account discovered it was not yet
    allowed to write with a program by being refused, at the end of whatever
    computation it had just finished -- and could not find out what would
    change that, because nothing said.
    """
    from .permissions import (TRUSTED_AFTER, accepted_edit_count,
                              is_board_member, is_trusted)

    accepted = accepted_edit_count(user)
    context = {
        'user_shown': user,
        'is_self': user.pk == request.user.pk,
        'accepted_edits': accepted,
        'trusted_after': TRUSTED_AFTER,
        'is_trusted': is_trusted(user),
        'is_board': is_board_member(user),
        'edits_still_needed': max(0, TRUSTED_AFTER - accepted),
        'revision_count': user.table_revisions.count(),
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
		query_real_intervals = search_real_numbers(r_query, 10-i, per_table=True)
		
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
		query_fractional_part = search_fractional_parts(f_query, 10-i,
		                                                per_table=True)
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
			query_complex = search_complex_numbers(n, int(10-i), per_table=True)
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
		
	#A table's number, answered directly. The dropdown is a separate query
	#from `search_metadata`, so it needs telling too -- the same split that
	#let a draft appear here after `search.py` had stopped showing them.
	from .search import _table_by_number

	numbered = _table_by_number(term)
	if numbered is not None and i < 10:
		entries[i] = {
			'value': str(i),
			'label': '',
			'type': 'table',
			'title': numbered.title,
			'url': '/%s' % (numbered.url,),
			'subtitle': numbered.tid,
		}
		i += 1

	#Searching for tables:
	if ':' not in term and '^' not in term:
		search_query = full_text_search_query(term)
		rank = SearchRank(F('search_vector'), search_query)
		#Published only. `search.py` has filtered this since drafts existed --
		#"drafts are their author's until published, so they do not answer a
		#search by name any more than they answer one by number" -- and this
		#older dropdown was not changed with it, so an anonymous request for
		#"Fibonacci" was answered with two unpublished tables, their titles,
		#their addresses and how many entries they held.
		query_tables = (TableSearch.objects.filter(table__published=True)
		                .annotate(rank=rank).filter(rank__gte=0.01)
		                .order_by('-rank')[:(10-i)])
		
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

	#Two ways in and one way through. The form produces the same YAML the
	#source editor would have produced, and then takes the identical path:
	#the same stale-write check, size limits, schema validation, review rules
	#and messages. A second save path would drift from this one, and the drift
	#would be invisible until the two disagreed about somebody's edit.
	if request.method == 'POST' and request.POST.get('action') == 'save-metadata':
		return _save_metadata_form(request, table, base)

	if request.method == 'POST' and request.POST.get('action') == 'save-sections':
		return _save_sections_form(request, table, base)

	if request.method == 'POST' and request.POST.get('action') == 'save-entries':
		return _save_entries_form(request, table, base)

	if request.method == 'GET' and request.GET.get('form'):
		return _metadata_form_page(request, table, base)

	if request.method == 'POST':
		table_yaml = _submitted_yaml(request)
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

		return _save_edited_tree(request, table, base, tree,
		                         source=table_yaml)

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


def _submitted_yaml(request):
	"""The YAML a browser sent, with its line endings put back.

	HTML says a textarea's content is normalised to CRLF on submission, so the
	document that comes back differs from the one that went out on every single
	line. The stored table was never affected -- the text is parsed to a tree
	and re-dumped, so the endings never reach the database -- but "show
	changes" answered a request to see what you had altered with the entire
	table, which is the same as not answering.
	"""
	return request.POST.get('table', '').replace('\r\n', '\n').replace('\r', '\n')


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
@login_required
def offer_draft(request, tid):
	"""Say that a draft is finished, or take that back.

	The author's statement, and the board's for a draft somebody has
	abandoned. Nothing can work out from outside whether a person is done, and
	a table with entries in it may still be half-built.
	"""
	from .editing import has_entries, may_see, tree_of
	from .permissions import is_board_member

	table = get_object_or_404(Table, tid=tid)
	if table.published:
		raise Http404('This table is already published.')
	if not may_see(table, request.user):
		raise Http404()
	mine = table.created_by_id and table.created_by_id == request.user.pk
	if not (mine or is_board_member(request.user)):
		raise Http404()

	if request.method != 'POST':
		return HttpResponseRedirect(reverse('db:drafts'))

	wanted = request.POST.get('ready') == 'yes'
	if wanted and not has_entries(tree_of(table.head_revision)
	                              if table.head_revision else {}):
		messages.error(request, (
			'%s has no numbers in it yet, so there is nothing to review. '
			'Add at least one value; a program can add the rest.' % (table.tid,)))
		return HttpResponseRedirect(reverse('db:drafts'))

	table.ready_for_review = wanted
	table.save(update_fields=['ready_for_review'])
	messages.success(request, (
		'%s is offered for review; it is in the queue now.' % (table.tid,)
		if wanted else
		'%s is back in progress and out of the review queue.' % (table.tid,)))
	return HttpResponseRedirect(reverse('db:drafts'))


def review_queue(request):
	"""Tables carrying changes nobody has confirmed.

	The queue exists because publication and indexing are separate here: an
	unreviewed edit is already on its page, and what it is waiting for is
	admission to search by number. So this is not a gate somebody is stuck
	behind, and the cost of a long queue is a search that quietly covers less
	than it could, which is exactly the sort of decay that needs to be visible
	somewhere.
	"""
	from django.db.models import Count, Q

	from .models import Number, NumberComplex, NumberPAdic, Polynomial
	from .permissions import is_board_member

	if not is_board_member(request.user):
		raise Http404()

	#Counted from the rows rather than by diffing the documents.
	#
	#`sync_review_flags` already works out which entries are unreviewed and
	#marks them, after every commit and every review, so the answer is in the
	#database on an indexed column. This view used to recompute it: two YAML
	#parses and a full entry comparison for every table whose head had moved
	#since its last review -- which, after a run that touched the metadata of
	#every table in the corpus, was 108 of 109. Forty seconds, most of it
	#spent proving that nothing had changed, and gunicorn killed the worker
	#before the page arrived.
	outstanding = {}
	for model in (Number, NumberComplex, NumberPAdic, Polynomial):
		rows = (model.objects.filter(reviewed=False)
		        .values('table_id').annotate(n=Count('id')))
		for row in rows:
			outstanding[row['table_id']] = (outstanding.get(row['table_id'], 0)
			                                + row['n'])

	waiting = []
	for table in (Table.objects.exclude(head_revision=None)
	                           .select_related('head_revision',
	                                           'reviewed_at_revision')):
		#A draft asks for attention only when its author says it is finished.
		#Otherwise every table entered the queue the moment it was created,
		#and a queue that is mostly half-built tables trains its reader to
		#skim -- which costs exactly the attention it exists to get.
		if not table.published and not table.ready_for_review:
			continue
		count = outstanding.get(table.pk, 0)
		whole = table.reviewed_at_revision_id is None
		if not count and not whole:
			continue
		if whole:
			count = count or table.number_count
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
		table.reviewed_by = request.user
		table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])

		#A draft is published by being reviewed, because that is what the two
		#acts have in common: somebody competent has looked. Anything else
		#means either a table going public that nobody read, or a reviewer
		#confirming values on a page the public cannot reach.
		published_now = False
		if not table.published:
			from .editing import publish_table

			try:
				publish_table(table)
				published_now = True
			except ValueError as empty:
				messages.error(request, str(empty))
				return HttpResponseRedirect(
					reverse('db:review-table', kwargs={'tid': table.tid}))

		marked = sync_review_flags(table)
		if published_now:
			messages.success(request, (
				'%s is published. %s'
				% (table.tid,
				   'Its entries answer search by number from now on.'
				   if not marked else
				   '%d entries are still marked.' % (marked,))))
		else:
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


def _new_table_from_title(request):
	"""Create a draft from a title, and go straight to the editor.

	The form used to be a YAML document in a text area, and it published the
	table the moment it was saved. Both were wrong for the same reason: they
	asked for everything before anything could be looked at.

	Only the title is genuinely needed, because it is what the address is
	built from. Not even the parameters: nothing is frozen while a table is a
	draft -- see `commit_table` -- so they can be settled in the editor, which
	is where the entries that motivate them get written. And a draft is
	invisible until somebody offers it, so a half-written table is not
	published to anybody in the meantime.
	"""
	from .editing import create_table

	title = (request.POST.get('title') or '').strip()
	definition = (request.POST.get('definition') or '').strip()
	if not title:
		messages.error(request, 'A new table needs a title.')
		return render(request, 'new-table.html', _new_table_context(request))

	tree = {'Title': title}
	if definition:
		tree['Definition'] = definition

	#What indexes the family, if the person already knows. It is asked for
	#here because it is what fixes the shape of the entry form: the columns an
	#entry is identified by are the declared parameters, so a table with none
	#has an entry form with no identity in it. Only the names are asked for --
	#a parameter needs nothing else to be valid, and its type, constraints and
	#display are better set in the editor, next to the entries that show what
	#they should be.
	names = [name.strip() for name in
	         (request.POST.get('parameters') or '').replace(',', ' ').split()]
	if names:
		tree['Parameters'] = {name: {} for name in names}

	try:
		table = create_table(tree, author=request.user,
		                     message='created this table', published=False,
		                     via='web')
	except ValueError as trouble:
		messages.error(request, str(trouble))
		return render(request, 'new-table.html', _new_table_context(request))

	messages.success(request, (
		'%s is yours to fill in. It is a draft: nobody else can read it yet, '
		'and its parameters can still change. Offer it for review when it '
		'holds numbers.' % (table.tid,)))
	return HttpResponseRedirect(reverse('db:edit-table',
	                                    kwargs={'tid': table.tid}))


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

	if request.method == 'POST' and request.POST.get('form') == 'simple':
		return _new_table_from_title(request)

	if request.method == 'POST':
		table_yaml = _submitted_yaml(request)
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
			                     message=request.POST.get('message', '').strip(),
			                     via='web')
		except ValueError as e:
			messages.error(request, str(e))
			return render(request, 'new-table.html',
			              _new_table_context(request, table_yaml))

		from .permissions import edits_are_reviewed
		if edits_are_reviewed(request.user):
			table.reviewed_at_revision = table.head_revision
			table.reviewed_by = request.user
			table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])
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


def _new_table_context(request, table_yaml=None):
	"""The new-table page. ``table_yaml`` is None for the simple form."""
	from .editing import NEW_TABLE_TEMPLATE
	from .permissions import is_board_member

	if table_yaml is None:
		table_yaml = NEW_TABLE_TEMPLATE

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
			restore_revision(table, revision, author=request.user, via='web')
			messages.success(request, (
				'Restored the version from %s. This is a new revision rather '
				'than an erasure: what happened in between is still here.'
				% (revision.created.strftime('%Y-%m-%d %H:%M'),)))
			from .permissions import edits_are_reviewed
			if edits_are_reviewed(request.user):
				table.refresh_from_db()
				table.reviewed_at_revision = table.head_revision
				table.reviewed_by = request.user
				table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])
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
		'diff_blocks': _diff_blocks(diff),
		'grouped': _group_by_run(revisions),
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
		files = _files_with_history(table, revision)

	return render(request, 'table-files.html', {
		'table': table,
		'revision': revision,
		'is_current': revision is not None
		              and revision.pk == table.head_revision_id,
		'files': files,
	})


def _files_with_history(table, revision):
	"""This revision's files, each with the revision that last changed it.

	A file belongs to a revision, not to a table: the manifest is complete at
	every revision, so "generate.sage as of March" is a different thing from
	"generate.sage now". Showing the list without saying which revision it
	belongs to, or when each file last moved, leaves a reader assuming these
	are simply the table's files -- and quietly wrong about which code produced
	which numbers.
	"""
	from .models import Attachment

	shown = list(revision.attachments.select_related('blob').all())
	if not shown:
		return []

	#Every version of these names up to and including this revision, oldest
	#first, so the last change to each can be found by walking forward.
	history = (Attachment.objects
	           .filter(revision__table=table,
	                   revision__created__lte=revision.created,
	                   name__in=[a.name for a in shown])
	           .select_related('revision', 'blob')
	           .order_by('revision__created'))

	#Only the revisions where the content actually changed. A file carried
	#through fifty edits appears in fifty manifests and has two versions, and
	#listing the fifty would bury the two.
	introduced = {}
	previous = {}
	versions = {}
	for row in history:
		if previous.get(row.name) != row.blob.digest:
			introduced[row.name] = row.revision
			previous[row.name] = row.blob.digest
			versions.setdefault(row.name, []).append({
				'revision': row.revision,
				'blob': row.blob,
				'is_first': not versions.get(row.name),
			})

	out = []
	for attachment in shown:
		since = introduced.get(attachment.name)
		earlier = list(reversed(versions.get(attachment.name, [])))
		out.append({
			'attachment': attachment,
			'name': attachment.name,
			'blob': attachment.blob,
			'since': since,
			#A file first seen with the table is not "changed", it is original.
			'is_original': since is not None and since.parent_id is None,
			'changed_here': since is not None and since.pk == revision.pk,
			#Newest first, and only where it changed.
			'versions': earlier,
			'version_count': len(earlier),
		})
	return out


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


def _diff_blocks(diff_text):
	"""A unified diff as hunks of tagged lines, for rendering rather than reading.

	One block per hunk, because a diff of a table is usually a handful of
	changes scattered through a thousand entries, and running them together in
	one grey wall makes the reader find the boundaries themselves.

	Each line carries what it is -- added, removed or context -- so the page
	can colour it instead of asking somebody to scan for leading + and -.
	"""
	blocks = []
	current = None
	for line in (diff_text or '').split('\n'):
		if line.startswith('@@'):
			current = {'header': line, 'where': _hunk_in_words(line),
			           'lines': []}
			blocks.append(current)
			continue
		if current is None:
			#Anything before the first hunk header: file headers, which say
			#nothing a reader does not already know from the page.
			continue
		if line.startswith('+'):
			kind = 'added'
		elif line.startswith('-'):
			kind = 'removed'
		elif line.startswith('\\'):
			#"\ No newline at end of file" is about the file, not the table.
			continue
		else:
			kind = 'context'
		current['lines'].append({'kind': kind, 'text': line[1:] if line else ''})
	return blocks


def _save_edited_tree(request, table, base, tree, source=None, back_to=None):
	"""Commit an edited document and report what happened.

	One function for both ways in, because the rules an edit has to satisfy --
	the stale-write check, the size limits, the schema, who gets review -- are
	properties of editing rather than of a particular form. Two copies would
	drift, and the drift would only show when they disagreed about somebody's
	edit.

	``source`` is the YAML the author typed, kept so a refusal can put them
	back in front of it. The form has none, and is sent back to itself.
	"""
	from .limits import EXCEPTION_KEY, TooBig
	from .editing import (InvalidDocument, ParametersChanged, StaleEdit,
	                      commit_table, without_managed_keys)
	from .permissions import edits_are_reviewed

	def refuse():
		if back_to:
			return HttpResponseRedirect(back_to)
		return render(request, 'edit.html',
		              _edit_context(request, table, source or '', base))

	tree = without_managed_keys(tree)

	#Required here as well as in the browser, because the browser's requirement
	#is a convenience and this is the rule. A history entry with no message is
	#the one that tells a later reader nothing, and makes them open the diff to
	#learn what a sentence would have said.
	message = request.POST.get('message', '').strip()
	if not message:
		messages.error(request, (
			'Say what you changed, in a few words. Nothing has been saved. '
			'The history is read by people deciding whether a number is '
			'right, and an entry with no message is the one that leaves them '
			'opening the diff to find out.'))
		return refuse()

	try:
		outcome = commit_table(
			table, tree,
			author=request.user,
			message=message,
			base=base,
			#The form. `web` is about the channel, not about who: a person
			#uses the API and the package too, and those say so themselves.
			via='web',
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
		return refuse()
	except InvalidDocument as bad:
		messages.error(request, (
			'Nothing has been saved. The document is valid YAML but part of it '
			'cannot be made into a table: %s. A value has to be a number the '
			'database can read -- 3.14, not a sentence -- and an entry has to '
			'name the parameters the table declares.' % (bad,)))
		return refuse()
	except StaleEdit as stale:
		messages.error(request, (
			'Somebody else changed this table while you were editing, and '
			'your changes overlap theirs in %d place(s). Nothing has been '
			'saved.' % (len(stale.conflicts),)))
		if back_to:
			return HttpResponseRedirect(back_to)
		context = _edit_context(request, table, source or '', stale.head)
		context['conflicts'] = stale.conflicts
		return render(request, 'edit.html', context)
	except TooBig as big:
		messages.error(request, (
			'Nothing has been saved. %s. These are the limits past which '
			'the editor and the diff stop working, so no reason makes it '
			'workable; a table this large wants to be several tables, or '
			'a program.'
			% ('; '.join(b.message for b in big.breaches).capitalize(),)))
		return refuse()

	if outcome.unchanged:
		messages.info(request, 'No changes to save.')
	elif outcome.merged:
		messages.success(request, (
			'Saved, and merged with a change somebody else made while you '
			'were editing. The table now contains both.'))
	else:
		messages.success(request, 'Saved.')

	for problem in outcome.problems:
		messages.warning(request, 'Saved, but %s' % (problem,))

	for breach in outcome.breaches:
		messages.warning(request, (
			'Saved, but %s. If that is deliberate, please say why in a '
			'"%s" line under Data properties; a reviewer will otherwise '
			'have to guess.' % (breach.message, EXCEPTION_KEY)))

	if outcome.revision and edits_are_reviewed(request.user):
		table.reviewed_at_revision = outcome.revision
		table.reviewed_by = request.user
		table.save(update_fields=['reviewed_at_revision', 'reviewed_by'])
		from .review import sync_review_flags
		sync_review_flags(table)

	if back_to:
		return HttpResponseRedirect(back_to)
	return HttpResponseRedirect(reverse('db:table_by_url',
	                                    kwargs={'url': table.url}))



def _metadata_form_page(request, table, base):
	"""The form view: the settings, or the prose sections.

	Two pages rather than one long one. They edit different things and are
	reached for at different moments -- the settings once when a table is set
	up, the prose whenever there is something to say.
	"""
	from .editing import may_see, tree_of
	from .metadata_form import fields_from
	from .permissions import is_board_member, may_edit
	from .sections_form import sections_from

	if not may_see(table, request.user):
		raise Http404
	tree = tree_of(base) if base is not None else {}

	if request.GET.get('form') == 'entries':
		from .entries_form import rows_from

		rows, meta = rows_from(tree, page=request.GET.get('page') or 1)
		return render(request, 'edit-entries.html', {
			'table_being_edited': table,
			'base_digest': base.digest if base is not None else '',
			'may_edit': may_edit(request.user),
			'is_board_member': is_board_member(request.user),
			'is_draft': not table.published,
			'rows': rows,
			'meta': meta,
			#An identity is what citations resolve on, so it may be typed while
			#a table is a draft and not after. The form shows that rather than
			#refusing the save afterwards.
			'identities_editable': not table.published,
			'pages': range(1, meta['pages'] + 1),
		})

	if request.GET.get('form') == 'sections':
		return render(request, 'edit-sections.html', {
			'table_being_edited': table,
			'base_digest': base.digest if base is not None else '',
			'may_edit': may_edit(request.user),
			'is_board_member': is_board_member(request.user),
			'is_draft': not table.published,
			'sections': sections_from(tree),
			#What CITE{} may point at, so a citation can be inserted rather
			#than typed from memory and misspelt.
			'citable': sorted((tree.get('References') or {}).keys())
			           if isinstance(tree.get('References'), dict) else [],
			#And what HREF{} may point at. A table's slug is what the target
			#is written as, so the picker offers slugs and shows titles: a
			#link typed from memory is a link that resolves to nothing, or
			#worse, to something else.
			'linkable': list(Table.objects.filter(published=True)
			                 .order_by('title')
			                 .values('url', 'title', 'tid')),
			#Existing tags, so a table joins a subject that already has a page
			#rather than starting a second one a letter apart.
			'known_tags': list(Tag.objects.order_by('name')
			                   .values_list('name', flat=True)),
		})

	context = {
		'table_being_edited': table,
		'base_digest': base.digest if base is not None else '',
		'may_edit': may_edit(request.user),
		'is_board_member': is_board_member(request.user),
		'is_draft': not table.published,
	}
	context.update(fields_from(tree))
	#Supplied here rather than by fields_from, which answers about a document
	#and should not also be querying the corpus.
	from .metadata_form import known_other_types
	context['known_other_types'] = known_other_types()
	return render(request, 'edit-metadata.html', context)


def _save_metadata_form(request, table, base):
	"""Apply the form to the stored document and save it the ordinary way.

	The form never sees the whole document, only its own fields, so the
	document it edits is the stored one rather than anything a browser sent
	back. That is what keeps a form incapable of deleting what it does not
	display, and it is why the base revision matters here as much as it does in
	the source editor: the patch is applied to the version the author was
	looking at.
	"""
	from .editing import commit_table, tree_of
	from .metadata_form import apply_to

	base_digest = request.POST.get('base', '')
	if base_digest:
		base = TableRevision.objects.filter(
			table=table, digest=base_digest).first() or base

	#A draft's identities are not pointed at from anywhere yet, so its value
	#keys may still be renamed; a published table's may not.
	tree = apply_to(tree_of(base) if base is not None else {}, request.POST,
	                allow_key_changes=not table.published)
	return _save_edited_tree(request, table, base, tree,
	                         back_to='%s?form=1' % (
		                         reverse('db:edit-table',
		                                 kwargs={'tid': table.tid}),))


def _save_entries_form(request, table, base):
	"""Apply one page of the entries form and save it the ordinary way.

	The page number is carried through the save so the author comes back to the
	rows they were working on, which on a table of a thousand entries is the
	difference between an edit and a search.
	"""
	from .editing import tree_of
	from .entries_form import apply_entries

	base_digest = request.POST.get('base', '')
	if base_digest:
		base = TableRevision.objects.filter(
			table=table, digest=base_digest).first() or base

	tree = apply_entries(tree_of(base) if base is not None else {},
	                     request.POST,
	                     #Renaming an entry reassigns what every citation to it
	                     #resolves to. Free while nobody can be citing it.
	                     allow_identity_changes=not table.published)
	page = request.POST.get('page') or '1'
	return _save_edited_tree(request, table, base, tree,
	                         back_to='%s?form=entries&page=%s' % (
		                         reverse('db:edit-table',
		                                 kwargs={'tid': table.tid}), page))


def _save_sections_form(request, table, base):
	"""Apply the sections form and save it the ordinary way."""
	from .editing import tree_of
	from .sections_form import apply_sections

	base_digest = request.POST.get('base', '')
	if base_digest:
		base = TableRevision.objects.filter(
			table=table, digest=base_digest).first() or base

	tree = apply_sections(tree_of(base) if base is not None else {},
	                      request.POST)
	return _save_edited_tree(request, table, base, tree,
	                         back_to='%s?form=sections' % (
		                         reverse('db:edit-table',
		                                 kwargs={'tid': table.tid}),))


def _shown_as(value_display, groups_left, value):
	"""How this parameter value is written, when its parameter says.

	Only for a level holding one parameter: a grouped level such as
	`['c4', 'c6']` has a key holding two values at once, and a display for the
	pair is a different thing from a display for a value.
	"""
	if not value_display or not groups_left:
		return None
	group = groups_left[0]
	names = group if isinstance(group, (list, tuple)) else [group]
	if len(names) != 1:
		return None
	return (value_display.get(names[0]) or {}).get(str(value))


def _hunk_in_words(header):
	"""`@@ -13,4 +13,8 @@` said in words.

	That notation is a instruction to a program -- where to apply a patch and
	how many lines it covers -- and it is on a page whose readers are being
	asked whether a number is right. What they need from it is where in the
	table they are, and whether this part grew or shrank.
	"""
	import re

	found = re.match(r'@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@', header)
	if not found:
		return ''
	before_start, before_count, after_start, after_count = found.groups()
	before = int(before_count) if before_count is not None else 1
	after = int(after_count) if after_count is not None else 1

	where = 'from line %s' % (after_start,)
	if before == after:
		return '%s (%d line%s)' % (where, after, '' if after == 1 else 's')
	if after > before:
		return '%s (%d line%s, %d more than before)' % (
			where, after, '' if after == 1 else 's', after - before)
	return '%s (%d line%s, %d fewer than before)' % (
		where, after, '' if after == 1 else 's', before - after)


def entry_blame(request, tid):
	"""Where each of a table's entries came from.

	The revisions already hold the answer -- each is a complete document, so
	walking them in order says exactly when an entry's value last changed --
	and it is computed rather than stored. A stored pointer would be faster and
	could disagree with the revisions, which is the failure this project keeps
	finding; the revisions are the truth.

	Only for one page of entries at a time, since answering for a table of a
	thousand means reading its whole history.
	"""
	from .editing import may_see, tree_of
	from .entries_form import PAGE_SIZE, columns_of, identity_of
	from .flatten import entries_block

	table = get_object_or_404(Table, tid=tid)
	if not may_see(table, request.user):
		raise Http404
	if table.head_revision is None:
		raise Http404('this table has no revisions')

	head = tree_of(table.head_revision)
	columns = columns_of(head)
	records = entries_block(head) or []
	if not isinstance(records, list):
		records = []

	page = _as_int(request.GET.get('page')) or 1
	pages = max(1, (len(records) + PAGE_SIZE - 1) // PAGE_SIZE)
	page = max(1, min(page, pages))
	start = (page - 1) * PAGE_SIZE
	shown = records[start:start + PAGE_SIZE]
	wanted = {identity_of(r.get('params') or {}, columns): r
	          for r in shown if isinstance(r, dict)}

	#Oldest first, so the last revision to write a given value wins.
	came_from = {}
	previous = {}
	for revision in table.revisions.select_related(
			'author', 'contributor').order_by('created'):
		try:
			entries = entries_block(tree_of(revision)) or []
		except Exception:
			continue
		if not isinstance(entries, list):
			continue
		for record in entries:
			if not isinstance(record, dict):
				continue
			identity = identity_of(record.get('params') or {}, columns)
			if identity not in wanted:
				continue
			value = record.get('number')
			if previous.get(identity) != value:
				previous[identity] = value
				came_from[identity] = revision

	rows = []
	for record in shown:
		if not isinstance(record, dict):
			continue
		identity = identity_of(record.get('params') or {}, columns)
		rows.append({
			'identity': identity,
			'params': record.get('params') or {},
			'number': record.get('number'),
			'revision': came_from.get(identity),
		})

	return render(request, 'entry-blame.html', {
		'table': table,
		'columns': columns,
		'rows': rows,
		'page': page,
		'pages': pages,
		'total': len(records),
	})


def _group_by_run(revisions):
	"""Revisions with the runs collapsed into one line each.

	A run amends its own revision only while that revision is still the head.
	Two people generating into the same table at once therefore interleave, and
	neither can amend: six submissions become seven revisions, and a thousand
	each would become two thousand.

	Nothing about that is *wrong* -- every revision holds what it held, and an
	entry is still attributed to whoever last changed it -- but a history of two
	thousand lines describing two acts is unreadable, and a reader scrolling it
	learns less than one sentence would tell them.

	So a run is shown as one row, positioned at its most recent revision, with
	its parts available underneath. Revisions with no run stay as they are: a
	person's edit is one act and already reads as one.
	"""
	rows = []
	runs = {}
	for revision in revisions:
		if not revision.run:
			rows.append({'run': '', 'revision': revision, 'parts': [revision],
			             'count': 1})
			continue
		group = runs.get(revision.run)
		if group is None:
			group = {'run': revision.run, 'revision': revision, 'parts': [],
			         'count': 0}
			runs[revision.run] = group
			rows.append(group)
		group['parts'].append(revision)
		group['count'] += 1
	for group in rows:
		if group['run']:
			#The revisions arrive newest first, so the first is the latest and
			#the last is where the run began.
			group['first'] = group['parts'][-1]
			group['latest'] = group['parts'][0]
	return rows


def table_bundle(request, tid):
	"""A table as one file: its document and everything attached to it.

	The numbers and the code that produced them are one thing, and until now a
	reader could have either -- the page, or the files, one at a time. A table
	is small enough that all of it fits in a download, and a reader who wants
	to check a computation wants the whole of it rather than a list of links.

	As of one revision, so the code in the bundle is the code that produced the
	numbers in the same bundle: `?rev=` names an older one, and a bundle taken
	today of a run from March holds March's script.
	"""
	import io
	import zipfile

	from django.http import HttpResponse

	from .editing import may_see, tree_of

	table = get_object_or_404(Table, tid=tid)
	if not may_see(table, request.user):
		raise Http404

	revision = None
	asked = _as_int(request.GET.get('rev'))
	if asked is not None:
		revision = table.revisions.filter(pk=asked).first()
	if revision is None:
		revision = table.head_revision
	if revision is None:
		raise Http404('this table has no revisions')

	folder = table.tid
	buffer = io.BytesIO()
	with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as bundle:
		#The identifier goes back in, as it does in the export: a file that
		#does not say which table it is cannot be read on its own.
		tree = tree_of(revision)
		document = {'ID': table.tid}
		document.update({k: v for k, v in tree.items() if k != 'ID'})
		from .editing import dump_tree

		bundle.writestr('%s/table.yaml' % (folder,), dump_tree(document))

		for attachment in revision.attachments.select_related('blob'):
			bundle.writestr('%s/%s' % (folder, attachment.name),
			                bytes(attachment.blob.content))

		bundle.writestr('%s/README.txt' % (folder,), _bundle_note(table, revision))

	response = HttpResponse(buffer.getvalue(), content_type='application/zip')
	response['Content-Disposition'] = (
		'attachment; filename="%s.zip"' % (table.tid,))
	return response


def _bundle_note(table, revision):
	"""What this bundle is, for somebody opening it a year from now."""
	who = (revision.author.username if revision.author_id
	       else (revision.contributor.author if revision.contributor_id
	             else revision.produced_by or 'unknown'))
	return (
		'%s: %s\n'
		'\n'
		'This is the table as of %s, by %s.\n'
		'%s\n'
		'\n'
		'table.yaml holds the numbers and everything said about them. The other\n'
		'files are what was stored alongside them -- usually the code that\n'
		'produced them. They are recorded, not run.\n'
		'\n'
		'The table as it stands now: %s\n'
		% (table.tid, table.title,
		   revision.created.strftime('%Y-%m-%d %H:%M'), who,
		   'Run: %s' % (revision.run,) if revision.run else '',
		   'https://numberdb.org/%s' % (table.tid,)))


def api_reference(request):
	"""Every endpoint the API has, in one place.

	Written by hand rather than generated: these are plain Django views, so
	there is no schema to introspect, and their docstrings explain why an
	endpoint behaves as it does rather than which headers it takes.

	What is *not* left to hand is coverage. Every route named `api-...` must
	appear here, and a test fails if one does not -- so an endpoint cannot ship
	undocumented. That check exists because the help page had gone stale in
	exactly that way: five write endpoints existed and it mentioned none of
	them.
	"""
	from .api import (LEASE_MINUTES, LOCK_WAIT, MAX_ATTACHMENT_BYTES,
	                  MAX_ATTACHMENTS_BYTES)
	from .permissions import TRUSTED_AFTER
	from .throttle import _limits

	anonymous, identified, _window = _limits()
	return render(request, 'api-reference.html', {
		'anonymous_rate_limit': anonymous,
		'identified_rate_limit': identified,
		'trusted_after': TRUSTED_AFTER,
		'lease_minutes': LEASE_MINUTES,
		'lock_wait': LOCK_WAIT,
		'max_attachment_kb': MAX_ATTACHMENT_BYTES // 1024,
		'max_attachments_kb': MAX_ATTACHMENTS_BYTES // 1024,
	})


#: How many usable keys one account may hold at once. Enough for a laptop, a
#: cluster and a notebook to have their own -- which is the point of labels --
#: and few enough that a runaway script cannot mint thousands.
MAX_ACTIVE_KEYS = 10


@login_required
def api_keys(request):
	"""Issue and revoke one's own API keys.

	Until now these were issued by hand, by email, which is a bottleneck in
	front of the one thing the write API exists for. Nothing about the model
	needed changing: a key was always a token this server cannot read back,
	stored as a hash and shown once.

	Shown once is the part the page has to be honest about. There is no way to
	recover a key later -- not for the user, not for us -- so the only useful
	thing to do with a lost one is revoke it and take another.
	"""
	from django.shortcuts import redirect

	from .models import ApiKey

	if request.method == 'POST':
		action = request.POST.get('action', '')

		if action == 'revoke':
			key = ApiKey.objects.filter(pk=request.POST.get('key') or 0,
			                            user=request.user).first()
			if key is not None and not key.revoked:
				#Revoked, never deleted: a key that turns up in a log or a
				#shared notebook should still say when it was issued and when
				#it was last used.
				key.revoked = True
				key.save(update_fields=['revoked'])
				messages.success(request, 'Key %s… revoked. Anything still '
				                          'using it will start being refused.'
				                 % (key.prefix,))
			return redirect('db:keys')

		if action == 'create':
			active = ApiKey.objects.filter(user=request.user,
			                               revoked=False).count()
			if active >= MAX_ACTIVE_KEYS:
				messages.error(
					request,
					'You already have %d keys. Revoke one you are not using: '
					'a key nobody can account for is a key nobody can safely '
					'revoke.' % (active,))
				return redirect('db:keys')

			label = (request.POST.get('label') or '').strip()[:64]
			try:
				days = int(request.POST.get('days') or 0)
			except ValueError:
				days = 0
			_record, token = ApiKey.issue(request.user, label=label,
			                              days=days or None)
			#Through the session rather than the query string: a key in a URL
			#is a key in the browser history, in the server log, and in the
			#Referer header of the next page. Popped on the way out, so a
			#refresh does not show it again.
			request.session['fresh_api_key'] = token
			return redirect('db:keys')

	from .permissions import (TRUSTED_AFTER, accepted_edit_count,
	                          may_write_through_api)

	return render(request, 'api-keys.html', {
		'keys': request.user.api_keys.all(),
		'fresh_key': request.session.pop('fresh_api_key', None),
		'active_count': request.user.api_keys.filter(revoked=False).count(),
		'max_keys': MAX_ACTIVE_KEYS,
		#A key authenticates; it does not authorise. Saying so here saves
		#somebody discovering it from a 403 at the end of a long computation.
		'may_write': may_write_through_api(request.user),
		'accepted_edits': accepted_edit_count(request.user),
		'trusted_after': TRUSTED_AFTER,
	})


def privacy(request):
	"""What the site records, and why.

	A flat page, but the claims on it are checked: see
	numberdb_app/test_privacy_pages.py and test_no_third_party_assets.py. A
	policy is a set of factual statements about a program, and the ones worth
	writing down are the ones something verifies.
	"""
	return render(request, 'privacy.html', {})


def impressum(request):
	"""Who is responsible for this site, and how to reach them."""
	return render(request, 'impressum.html', {})


@login_required
def export_own_data(request):
	"""Everything this account holds, as a JSON file.

	A right people rarely use, and one that costs nothing to honour properly
	when it is a button rather than an email to answer.
	"""
	import json

	from django.http import HttpResponse

	from .account_data import export_account

	data = export_account(request.user)
	body = json.dumps(data, indent=2, sort_keys=True, default=str)
	answer = HttpResponse(body, content_type='application/json')
	answer['Content-Disposition'] = (
		'attachment; filename="numberdb-%s.json"'
		% (request.user.get_username(),))
	return answer


@login_required
def delete_own_account(request):
	"""Close the account, keeping what it published.

	POST only, and the username has to be typed. What is irreversible should
	not be one stray click away, and this is irreversible: the account, its
	keys and its email address are gone, and only the edits remain, under a
	placeholder name.
	"""
	from django.contrib import messages
	from django.shortcuts import redirect

	from .account_data import delete_account

	if request.method != 'POST':
		return redirect('db:profile')

	typed = (request.POST.get('confirm') or '').strip()
	if typed != request.user.get_username():
		messages.error(request, 'Type your username exactly to confirm. '
		                        'Nothing was deleted.')
		return redirect('db:profile')

	name = request.user.get_username()
	moved = delete_account(request.user)
	#After the account is gone: the session it was pressed from refers to a
	#user that no longer exists, and logout() tidies the cookie rather than
	#leaving the browser holding one.
	from django.contrib.auth import logout
	logout(request)
	messages.info(request,
	              'The account %s has been deleted. Its %d edit%s remain in '
	              'the record, now shown as deleted-user.'
	              % (name, moved.get('edits', 0),
	                 '' if moved.get('edits', 0) == 1 else 's'))
	return redirect('db:home')


def discuss_table(request, tid):
	"""A table's discussion.

	Readable by anyone who can read the table; writable by anyone who may edit
	it. The same bar as editing on purpose: somebody trusted to change a
	number is trusted to discuss it, and a second, different gate here would
	only be a puzzle to work out.
	"""
	from django.contrib import messages
	from django.shortcuts import redirect

	from .discussion import (BODY_LIMIT, PER_HOUR, TooManyComments,
	                         edit_comment, may_moderate, may_post,
	                         post_comment, set_hidden, thread_for,
	                         visible_comments)
	from .editing import may_see

	table = get_object_or_404(Table, tid=tid)
	if not may_see(table, request.user):
		raise Http404('No table %s' % (tid,))

	if request.method == 'POST':
		if not request.user.is_authenticated:
			return redirect('account_login')

		action = request.POST.get('action', '')
		try:
			if action == 'post':
				if not may_post(request.user, table):
					messages.error(request, 'You cannot post here.')
				else:
					post_comment(table, request.user,
					             request.POST.get('body', ''),
					             request.POST.get('about_param', ''))
			elif action == 'save-edit':
				comment = get_object_or_404(Comment,
				                            pk=request.POST.get('comment'),
				                            thread__table=table)
				edit_comment(comment, request.user,
				             request.POST.get('body', ''))
			elif action in ('hide', 'unhide'):
				comment = get_object_or_404(Comment,
				                            pk=request.POST.get('comment'),
				                            thread__table=table)
				set_hidden(comment, request.user, action == 'hide')
		except TooManyComments as e:
			messages.error(request, str(e))
		except PermissionError:
			messages.error(request, 'That is not yours to change.')
		except ValueError as e:
			messages.error(request, str(e))
		return redirect('db:discuss', tid=table.tid)

	editing = request.GET.get('edit')
	context = {
		'table': table,
		'comments': visible_comments(thread_for(table), request.user),
		'can_post': may_post(request.user, table),
		'can_moderate': may_moderate(request.user),
		'body_limit': BODY_LIMIT,
		'per_hour': PER_HOUR,
		'about_param': request.GET.get('entry', ''),
		'editing_pk': int(editing) if (editing or '').isdigit() else None,
	}
	return render(request, 'discuss.html', context)
