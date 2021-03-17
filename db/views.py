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

import Pyro5.api
import Pyro5.errors

#from sage import *
#from sage.all import *
#from sage.arith.all import *
#from sage.rings.complex_number import *
#from sage.rings.all import *
#from sage.rings.all import RealIntervalField


from sage.all import *
#from sage.rings.all import *

'''
from sage.all import ceil
from sage.rings.complex_number import ComplexNumber
from sage.rings.complex_field import ComplexField
from sage.rings.real_mpfr import RealLiteral, RealField, RealNumber
from sage.rings.integer import Integer
from sage.rings.rational import Rational
from sage.rings.integer_ring import ZZ
from sage.rings.rational_field import QQ
from sage.rings.infinity import infinity
'''
'''
#from sage.repl.rich_output.pretty_print import pretty_print
from sage.misc.latex import latex
from sage.misc.misc import is_iterator

from sage.repl.preparse import preparse
from sage.arith.srange import ellipsis_range
from sage.functions.trig import *
from sage.symbolic.constants import *
from sage.functions.all import *
'''

from mpmath import pslq

from .models import UserProfile
from .models import Collection
from .models import CollectionData
from .models import CollectionSearch
from .models import Tag
from .models import Number
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
from utils.utils import blur_real_interval


from db_builder.utils import normalize_collection_data

def home(request):
    #messages.success(request, 'Test message for home page.')
    #return HttpResponse('Hello, World!')
    return render(request, 'home.html', {})

def about(request):
    return render(request, 'about.html', {})

def help(request):
    return render(request, 'help.html', {})

def collections(request):
	page = request.GET.get('page', 1)
	#print("page:",page)
	collections = Collection.objects.all()
	sortby_default = 'title'
	sortby = request.GET.get('sort_by',default=sortby_default)
	if sortby == 'number_count':
		collections = collections.order_by('-number_count')
	elif sortby == 'id':
		collections = collections.order_by('cid_int')
	elif sortby == 'title':
		collections = collections.order_by('title_lowercase')
	else:
		collections = collections.order_by(sortby_default)
	paginator = Paginator(collections, 50)
	try:
		shown_collections = paginator.page(page)
	except PageNotAnInteger:
		shown_collections = paginator.page(1)
	except EmptyPage:
		shown_collections = paginator.page(paginator.num_pages)
	#print("shown_collections:",shown_collections)
	return render(request, 'collections.html', {'collections': shown_collections, 'sortby': sortby})

def tags(request):
	page = request.GET.get('page', 1)
	tags = Tag.objects.all()
	sortby_default = 'number_count'
	sortby = request.GET.get('sort_by',default=sortby_default)
	if sortby == 'collection_count':
		tags = tags.order_by('-collection_count')
	elif sortby == 'number_count':
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
	collections = tag.collections.all()
	sortby_default = 'number_count'
	sortby = request.GET.get('sort_by',default=sortby_default)
	if sortby == 'number_count':
		collections = collections.order_by('-number_count')
	elif sortby == 'id':
		collections = collections.order_by('cid_int')
	elif sortby == 'title':
		collections = collections.order_by('title_lowercase')
	else:
		collections = collections.order_by(sortby_default)
	paginator = Paginator(collections, 50)
	try:
		shown_collections = paginator.page(page)
	except PageNotAnInteger:
		shown_collections = paginator.page(1)
	except EmptyPage:
		shown_collections = paginator.page(paginator.num_pages)
	return render(request, 'tag.html', {'tag': tag, 'collections': shown_collections, 'sortby': sortby})

def welcome(request):
    return render(request, 'welcome.html')

def render_collection(request, collection):
	context = collection_context(collection)							
	return render(request, 'collection.html', context)

def collection_by_cid(request, cid):
    # do something else...
    # return some data along with the view...
    
    #cid = "C%s" % (cid,)
    
    try:
        collection = Collection.objects.get(cid=cid)
    except Collection.DoesNotExist:
        raise Http404
    return render_collection(request, collection)
    
def collection_by_url(request, url):
    try:
        collection = Collection.objects.get(url=url)
    except Collection.DoesNotExist:
        raise Http404
    return render_collection(request, collection)

def collection_context(collection, preview=False):

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
			new_text += '<a class="HREF" href="%s">%s</a>%s' % (ref, caption, part2)
				
		if line_breaks:
			#Parse '\n's:
			new_text = new_text.replace("\n","<br>")
		return new_text

	current_job = ''

	try:

		current_job = 'loading yaml'
		#data = collection.data.json
		data = yaml.load(collection.data.full_yaml,Loader=yaml.BaseLoader)

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
			
		
		#html += '<div class="grid12">'
		#html += '<div class="col-m-6">'

		sections = []
			
		current_job = 'parsing definition'
		if 'Definition' in data:
			section = {
				'title': 'Definition',
				'text': render_text(data['Definition']),
			}
			sections.append(section)
			
		type_names = {
			"Z": "integer",
			"Q": "rational number",
			"R": "real number",
			"C": "complex number",
			"ZI": "integer interval",
			"RI": "real interval",
			"CI": "complex interval",
			"RB": "real ball",
			"CB": "complex ball",
		}  
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
					text += ' (%s)' % (render_text(info['constraints']),)

				if 'show-in-parameter-list' in info and info['show-in-parameter-list'].lower() == 'no':
					#Don't show this parameter in the homepage of this collection.
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
					text = '%s<br><pre><code class="collection-code language-%s">%s</code></pre>' % (
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
						if 'bib' in reference:
							text += render_text(reference['bib'].rstrip('\n')) + " "
						if 'arXiv' in reference:
							link = reference['arXiv']
							link = link.split("[")[0].strip(" \n")
							link = link.split("/")[-1]
							link = "https://www.arxiv.org/abs/%s" % (link,)
							text += '(<a href="%s">arXiv</a>) ' % (link,)
						if 'doi' in reference:
							link = reference['doi'].split("doi.org/")[-1]
							link = "https://doi.org/%s" % (link,)
							text += '(<a href="%s">doi</a>) ' % (link,)
						if 'url' in reference:
							if 'title' in reference:
								text += '<a href="%s">%s</a> ' % (reference['url'],reference['title'])
							else:
								text += '<a href="%s">%s</a> ' % (reference['url'],reference['url'])

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

		property_names = {
			'type': 'Numbers are of type',
			'complete': 'Collection is complete',
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
				if key in property_names:
					text = "%s: " % (property_names[key])
					if key == 'type':
						if properties['type'] in type_names:
							text += type_names[value]
						else:
							text += "%s (Unknown value)" % (value,)
					elif key == 'sources':
						text += ", ".join(value)                
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
				return '<div class="collection-subtable">%s</div>' % (inner_html,)

			def format_param_group(param_group):
				result = ', '.join(p.strip(' ') for p in param_group.split(','))
				result = result.replace(' ','&nbsp;')
				return result

			if isinstance(numbers,dict):
				if 'number' in numbers or \
					'numbers' in numbers or \
					'equals' in numbers:
					#Numbers are given with extra information at this level:
					for key in numbers:
						if key in ('number','numbers','param-latex'):
							continue
						html += '%s: %s<br>' % (key, render_text(numbers[key]))
					if 'number' in numbers:
						html += render_number_table(numbers['number'], params_so_far, groups_left)
					elif 'numbers' in numbers:
						html += render_number_table(numbers['numbers'], params_so_far, groups_left)
					return html
				
			if len(groups_left) == 0:
				#numbers is an entry for a number now, either a string or a dict:
				if isinstance(numbers,str):
					html += '<div class="collection-number">%s</div>' % (numbers,)
				else:
					#html += '<div class="collection-subtable">'
					#html += '<div class="collection-block">'
					#html += '<div class="collection-entry">'
					if isinstance(numbers,list):           
						for number in numbers:
							html += '<div class="collection-number">%s</div>' % (number,)
					elif isinstance(numbers,dict):  
						for key, value in numbers.items():
							html += '<div class="collection-number-%s">%s</div>' % (key,render_text(value),)
					#html += '</div>'
					#html += '</div>'
					#html += '</div>'
				'''
				param = number_param_groups_to_string(params_so_far)
				#print("param:",param)
				if param != '':
					html = '<div id="%s" class="anchor-id">%s</div>' % (
						param,
						html,
					)
				'''
			else:
				if preview and isinstance(numbers,str) and numbers.startswith("INPUT"):
					return '%s (not shown in preview)' % numbers
				next_group = groups_left[0]
				html += '<div class="collection-subtable">'
				for p, numbers_p in numbers.items():
					if len(groups_left) <= 1:
						param = number_param_groups_to_string(params_so_far+[p])
						id_str = 'id="%s"' % (param,) if param != '' else ''
					else:
						id_str = ''
					html_p = '<div %s class="collection-block">' % (id_str,)
					if isinstance(numbers_p,dict) and 'param-latex' in numbers_p:
						param_html = numbers_p['param-latex']
					else:
						param_html = format_param_group(p)
					html_p += '<div class="collection-param-group"><span>%s:</span></div>' % (param_html,)
					html_inner = render_number_table(numbers_p, params_so_far+[p], groups_left[1:])
					html_p += '<div class="collection-cell-right">%s</div>' % (wrap_in_subtable(html_inner),)
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
				'title': pluralize('Number',collection.number_count),
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

		#html += '</div>'
		#html += '</div>'
		
		context = {
			'collection': collection,
			'sections': sections,
			'number_section': number_section,
		}
		if not preview:
			context['tags'] = collection.tags.all()
		else:
			context['tags'] = []


	except (AttributeError, ValueError, Exception) as e: 
		#TODO: Should remove Exception here after checking which exceptions are expected.
		error_message = 'Error while %s: %s' % (current_job, e)
		raise ValueError(error_message)
	
	return context

def preview(request, cid=None):
	#First try to get yaml from Textarea:
	collection_yaml = request.GET.get('collection',default=None)
	
	#Second try to get yaml from collection if cid is give:
	if collection_yaml == None:
		print('cid:',cid)
		if cid != None:
			collection = Collection.objects.get(cid=cid)
			if collection != None:
				collection_yaml = collection.data.raw_yaml
	
	#Third option is: Set collection_yaml to default:
	if collection_yaml == None:
		collection_yaml = \
			'ID: INPUT{id.yaml} #keep this and do not worry\n\n' + \
			'Title: <title>\n\n' + \
			'Definition: >\n' + \
			'  <definition>\n\n' + \
			'Numbers:\n' + \
			'- 3.14\n'
	
	context = {
		'collection_yaml': collection_yaml,
	}
			
	c_data = CollectionData()
	try:
		yaml_data = yaml.load(collection_yaml,Loader=yaml.BaseLoader)
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
	#c_data.json = normalize_collection_data(yaml_data)
	#print("c_data.json:",c_data.json)

	#TODO: Should avoid dumping yaml, and reloading it in collection_context():
	c_data.full_yaml = yaml.dump(normalize_collection_data(yaml_data),sort_keys=False)
	
	c = Collection()
	c.data = c_data
	#c.title = c_data.json['Title']
	c.title = yaml_data['Title']
	c.path = 'PATH-OF-COLLECTION-YAML'
	c.cid = 'AUTOMATIC-COLLECTION-ID'
	
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
	
	#print('collection_yaml:',collection_yaml)
	try:
		c_context = collection_context(c,preview=True)
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
    #latest_question_list = Question.objects.order_by('-pub_date')[:5]
    #context = {
    #    'blub': 0,
    #}
    #print("request:",request.user.__dir__())
    #template = loader.get_template('polls/index.html')
    #return HttpResponse(template.render(context, request))
    #return render(request,'profile/show.html',context)
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
    profile = user.userprofile
    profile.bio = request.POST['bio']
    profile.save()
    return HttpResponseRedirect(reverse('db:profile'))

def suggestions(request):
	time0 = time()
	
	def wrap_response(entries):
		data = {
			'entries': entries,
			'time_request': "{:.3f}s".format(time()-time0),
		}
		#print("data:",data)
		return JsonResponse(data,safe=True)

	def full_text_search_query(term):
		#OLD:
		#return SearchQuery(term, search_type='plain')
		
		terms = term.split(' ')
		term1 = ' & '.join("'%s'" % (t,) for t in terms[:-1])
		term2 = '%s:*' % (terms[-1][:6],)
		q1 = SearchQuery(term1, search_type='raw')
		q2 = SearchQuery(term2, search_type='raw')
		#print('term1, term2:', term1, term2)
		if term1 != '':
			return q1 & q2
		else:
			return q2
	
	term_entered = request.GET['term']
	term = term_entered.strip(" \n")
	if term == '':
		return wrap_response({})
	
	entries = {}
	i = 0
	suggested_numbers = []
	
	def add_suggested_numbers():
		nonlocal suggested_numbers
		nonlocal i
		
		for number in suggested_numbers:
			collection = number.collection
			param = number.param_str()
			entry_i = {
				'value': str(i),
				'label': '',
				'type': 'number',
				'title': collection.title,
				'url': '/%s#%s' % (collection.url, param),
			}
			if len(param) > 0: 
				entry_i['subtitle'] = '%s (#%s)' % (number.str_as_real_interval(), param)
			else:
				entry_i['subtitle'] = '%s' % (number.str_as_real_interval(),)
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
				'subtitle': '%s (not in database)'  % (n,),
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
					#number_type = Number.NUMBER_TYPE_ZZ,
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
					'subtitle': '%s (not in database)'  % (n,),
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
	query_real_intervals = Number.objects.none()
	r = None
	if exact_number_not_in_DB != None \
		or '.' in term \
		or 'p' in term or 'P' in term \
		or 'e' in term or 'E' in term:
			
		if exact_number_not_in_DB != None:
			r = RIF(exact_number_not_in_DB)
		else:
			r = parse_real_interval(term)
		
		if r != None:
			r_query = blur_real_interval(r)
			print("r_query:",r_query)
			query_real_intervals = Number.objects.filter(
				lower__range = (float(r_query.lower()),float(r_query.upper())),
				upper__range = (float(r_query.lower()),float(r_query.upper())),							
			)

	#Searching for real numbers by given fractional part:
	query_fractional_part = Number.objects.none()
	f = parse_fractional_part(term)
	if f != None:
		print("f:",f)
		f_query = blur_real_interval(f)
		print("f_query:",f_query)
		query_fractional_part = Number.objects.filter(
			frac_lower__range = (float(f_query.lower()),float(f_query.upper())),
			frac_upper__range = (float(f_query.lower()),float(f_query.upper())),							
		).annotate(query_frac = F('pk'))

	query_real_numbers = query_integers.union(
						query_rationals,
						query_real_intervals,
						query_fractional_part
					)[:(10-i)]
	#print("query_real_numbers:",query_real_numbers)
	if len(query_real_numbers) > 0:
		suggested_numbers += list(query_real_numbers)
	else:
		number = r if r != None else f
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
	
	#Searching for tag names:
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
			'subtitle': '%s collection%s, %s number%s' % (
				tag.collection_count,
				's' if tag.collection_count != 1 else '',
				tag.number_count,
				's' if tag.number_count != 1 else '',
			),
			'url': reverse('db:tag', kwargs={'tag_url': tag.url()}),
		}
		entries[i] = entry_i
		i += 1

	if i >= 10:
		return wrap_response(entries)
		
	#Searching for collections:
	search_query = full_text_search_query(term)
	rank = SearchRank(F('search_vector'), search_query)
	query_collections = CollectionSearch.objects.annotate(rank=rank).filter(rank__gte=0.01).order_by('-rank')[:(10-i)]
	
	#OLD: Simpler query:
	#query_collections = CollectionSearch.objects.filter(search_vector = term)[:(10-i)]
	
	for c_search in query_collections:
		collection = c_search.collection
		entry_i = {
			'value': str(i),
			'label': '',
			'type': 'collection',
			'title': collection.title,
			'url': '/%s' % (collection.url,),
		}
		if collection.number_count != 1:
			entry_i['subtitle'] = '%s numbers' % collection.number_count
		else:
			number = collection.numbers.first()
			entry_i['subtitle'] = '%s' % (number.str_as_real_interval(),)
		entries[i] = entry_i
		i += 1
		
	
	return wrap_response(entries)

def properties_of_rational(request, numerator, denominator):
	return properties(request, '%s/%s' % (numerator, denominator))

def properties(request, number):
	
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
		if n.is_squarefree():
			special_families.append('squarefree')
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

	#Case 2: given number is an integer:
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
		cf = StableContinuedFraction(r)
		cf_sage = cf.sage()
		if len(cf_sage) > 0:
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

	raise Http404("Number cannot be parsed.")

def advanced_search(request):

	try:
		E = Pyro5.api.Proxy("PYRONAME:safe_eval")
		#print("E:",E)
		ping_back = E.ping(b'test')
		print("ping_back:",ping_back)
	
	except (Pyro5.errors.NamingError,Pyro5.errors.CommunicationError) as e:
		print("e:",e, type(e))
		'''
		#print("error:",error)
		messages.append({
			'tags': 'alert-danger',
			'text': 'Error: The advanced search server is currently not running and has to be restarted. We apologize.',
		})
		return wrap_response(None, messages)
		'''
		messages.error(request, 'Error: The advanced search server is currently not running and has to be restarted. We apologize.')
		#return HttpResponseRedirect(reverse('db:home'))
	
	'''	
	if not request.user.is_authenticated:	
		print("not authenticated")
		messages.error(request, 'You need to be logged in to use advanced search.')
	'''
	
	context = {
		#'program': 'x = 3.14159265\nnumbers = {n: sin(x/n) for n in [1..10]}\n', 
		#'program': '{n: sin(pi/n) for n in [1..10]}\n',
		#'program': '{n: sin(pi*n/2)\n  for n in [1..10000]\n}\n',
		'program': '{n: sin(pi*n/2)\n  for n in [1..10]\n}\n',
		#'program': '{n: sin(1/n) for n in [1..10]}\n', 
	}
	
	return render(request, 'advanced-search.html', context)

def advanced_suggestions(request):
	time0 = time()
	
	def wrap_response(results, messages = None):
		context = {
			'results': results,
			'messages': messages,
		}
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
		return JsonResponse(data,safe=True)

		
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

	program = request.GET.get('program',default=None)
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

	def do_query():
		nonlocal i
		nonlocal param
		
		for number in query_real_intervals[:(max_results - i)]:
			results.append({
				'param': param,
				'number': number,
				'collection': number.collection,		
			})
			i += 1
			if i >= max_results:
				break
	
	for param, r in param_numbers:
		#Searching for real number up to given precision:
		r_query = blur_real_interval(r)
		print("r_query:",r_query)
		query_real_intervals |= Number.objects.filter(
			lower__range = (float(r_query.lower()),float(r_query.upper())),
			upper__range = (float(r_query.lower()),float(r_query.upper())),							
		)
		query_i += 1
		if query_i >= query_bulk_size:
			do_query()
			query_real_intervals = Number.objects.none()
			query_i = 0
			
		if i >= max_results:
			messages.append({
				'tags': 'alert-warning',
				'text': 'We only show the first %s results.' % (max_results,),
			})
			break
			
	do_query()
	
	return wrap_response(results,messages)
	
def debug(request):
	if settings.DEBUG:
		context = {}
		return render(request,'debug.html',context)
	raise Http404()
	
def collection_history(request, cid=None):
	print('cid:',cid)
	#if cid != None:
	
	collection = Collection.objects.get(cid=cid)
	
	context = {
		'collection': collection,
		'tags': collection.tags.all(),
		'commits': collection.commits.all(),
	}
			
	print("context:",context)

	return render(request,'collection-history.html',context)

