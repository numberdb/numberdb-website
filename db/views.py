from django.shortcuts import render, get_object_or_404
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.urls import reverse
from django.contrib.auth.models import User
from django.views import generic
from django.http import JsonResponse
from django.contrib import messages

from numpy import random as random
import re
#from sage import *
#from sage.all import *
#from sage.arith.all import *
#from sage.rings.complex_number import *
#from sage.rings.all import *
#from sage.rings.all import RealIntervalField


from sage import *
from sage.rings.all import *

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

from .models import UserProfile
from .models import Collection
from .models import Tag
from .models import Number
from .models import Searchable
from .models import SearchTerm
from .models import SearchTermValue


def home(request):
    #messages.success(request, 'Test message for home page.')
    #return HttpResponse('Hello, World!')
    return render(request, 'home.html', {})

def about(request):
    return render(request, 'about.html', {})

def help(request):
    return render(request, 'help.html', {})

def collections(request):
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
    return render(request, 'collections.html', {'collections': collections})

def tags(request):
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
    return render(request, 'tags.html', {'tags': tags})

def tag(request, tag_name):
    tag = Tag.objects.get(name=tag_name)
    collections = tag.my_collections.all()
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
    return render(request, 'tag.html', {'tag': tag, 'collections': collections})

def welcome(request):
    return render(request, 'welcome.html')

def collection(request, cid):
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

def render_collection(request, collection):
    data = collection.data.json
    html = ""
    html += '<a class="github-link" href="https://github.com/bmatschke/numberdb-data/tree/main/%s/collection.yaml">edit on github</a>' % (collection.path,)
    html += '<div class="collection-title">%s</div>' % (collection.title,)

    #Deduce label names:
    show_label_as = {}
    i_label = 1
    for header in ('Formulas','Comments'):
        if header in data and len(data[header]) > 0:
            for label in data[header]:
                show_label_as[label] = '(%s)' % (i_label,)
                i_label += 1
    i_label = 1
    if 'Programs' in data and len(data['Programs']) > 0:
        for label in data['Programs']:
            show_label_as[label] = '(P%s)' % (i_label,)
            i_label += 1
    i_label = 1
    for header in ('References','Links'):
        if header in data and len(data[header]) > 0:
            for label in data[header]:
                show_label_as[label] = '[%s]' % (i_label,)
                i_label += 1
    
    def render_text(text):
        '''
        Parse text for 'CITE', 'HREF', and '\n', 
        and replace accordingly.
        '''
        
        #Parse 'CITE's:
        parts = text.split("CITE{")
        new_text = parts[0]
        for part in parts[1:]:
            try: 
                ref, part2 = part.split("}",maxsplit=1)
                new_text += '<a class="CITE" href="#%s">%s</a>%s' % (ref, show_label_as[ref], part2)
                #new_text += '<a class="CITE" href="#%s" onClick="(event) => {scrollTo(event,);}">%s</a>%s' % (ref, ref, show_label_as[ref], part2)
            except (ValueError, KeyError):
                new_text += "(???)" + part2
                #TODO: Should output warning: "No closing bracket!"

        #Parse 'HREF's:
        parts = new_text.split("HREF{")
        new_text = parts[0]
        for part in parts[1:]:
            try: 
                ref, part2 = part.split("}",maxsplit=1)
                if part2 != "" and part2[0] == "[":
                    try:
                        caption, part2 = part2[1:].split("]",maxsplit=1)
                    except ValueError:
                        caption = ref
                else:
                    caption = ref
                new_text += '<a class="HREF" href="%s">%s</a>%s' % (ref, caption, part2)
            except (ValueError, KeyError):
                new_text += "[???]" + part2
                #TODO: Should output warning: "No closing bracket!"

        #Parse '\n's:
        new_text = new_text.replace("\n","<br>")
        return new_text
        
    for tag in collection.my_tags.all():
        html += '<a class="tag" href="%s">%s</a> ' % \
                (reverse('db:tag',kwargs={'tag_name': tag.name}),tag.name)
        
    if 'Definition' in data:
        html += '<div class="collection-section">%s</div>' % ("Definition")
        html += '<div class="collection-entry">%s</div>' % (render_text(data['Definition']),)

    type_names = {
        "Z": "integer",
        "R": "real number",
        "C": "complex number",
        "ZI": "integer interval",
        "RI": "real interval",
        "CI": "complex interval",
        "RB": "real ball",
        "CB": "complex ball",
    }  
    if 'Parameters' in data and len(data['Parameters']) > 0:
        html += '<div class="collection-section">%s</div>' % ("Parameters")
        for p, info in data['Parameters'].items():
            p_latex = info['latex-name'] if 'latex-name' in info else "$%s$" % (p,)
            html += '<div class="collection-block" id="%s">' % (p,)
            html += '<div class="collection-label">%s</div>' % (render_text(p_latex))
            html += ' &mdash;&nbsp;&nbsp; '
            if 'title' in info:
                html += '%s' % (render_text(info['title']),)    
            elif 'type' in info:
            #if 'type' in info:
                if info['type'] in type_names:
                    text = type_names[info['type']]
                else:
                    text = "%s (Unknown type)" % (info['type'],)
                html += text    
            if 'constraints' in info: 
                html += ' (%s)' % (render_text(info['constraints']),)
            html += '</div>'
        parameters = data['Parameters'].keys() 
    else:
        parameters = []
                    
    for header in ('Formulas','Comments'):
        if header in data and len(data[header]) > 0:
            html += '<div class="collection-section">%s</div>' % (header,)
            for label, text in data[header].items():
                html += '<div class="collection-block" id="%s">' % (label,)
                html += '<div class="collection-label">%s</div>' % (show_label_as[label],)
                html += '<div class="collection-entry">%s</div>' % (render_text(text),)
                html += '</div>'

    #Continue i_label, as it's all interior data, not a direct reference.
    if 'Programs' in data and len(data['Programs']) > 0:
        html += '<div class="collection-section">%s</div>' % ('Programs',)
        for label, program in data['Programs'].items():
            html += '<div class="collection-block" id="%s">'  % (label,)
            html += '<div class="collection-label">%s</div>' % (show_label_as[label],)
            html += '<div class="collection-entry">(%s)<br><code>%s</code></div>' % (render_text(program['language']),render_text(program['code']))
            html += '</div>'

    for header in ('References','Links'):
        if header in data and len(data[header]) > 0:
            html += '<div class="collection-section">%s</div>' % (header,)
            for label, reference in data[header].items():
                html += '<div class="collection-block" id="%s">' % (label,)
                html += '<div class="collection-label">%s</div>' % (show_label_as[label],)
                text = ""
                if 'bib' in reference:
                    text += render_text(reference['bib']) + " "
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
                html += '<div class="collection-entry">%s</div>' % (text,)
                html += '</div>'

    property_names = {
        'type': 'Numbers are of type',
        'complete': 'Collection is complete',
        'sources': 'Sources of data',
        'relative precision': 'Relative precision',
        'absolute precision': 'Absolute precision',
    }
    if 'Data properties' in data and len(data['Data properties']) > 0:
        properties = data['Data properties']
        html += '<div class="collection-section">%s</div>' % ('Data properties',)
        for key, value in properties.items():
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
            html += '<div class="collection-block">'
            html += '<div class="collection-entry">%s</div>' % (render_text(text),)
            html += '</div>'
   
    if 'Display properties' in data and 'group parameters' in data['Display properties']:
        param_groups = data['Display properties']['group parameters']
    else:
        param_groups = [[p] for p in parameters]
    
    def render_number_table(numbers, params_so_far=[], groups_left=param_groups):
        html = ''
        if len(groups_left) == 0:
            #numbers is an entry for a number now, either a string or a dict:
            if isinstance(numbers,str):
                html += '<div class="number">%s</div>' % (numbers,)
            elif isinstance(numbers,list):           
                for number in numbers:
                    html += '<div class="number">%s</div>' % (number,)
            elif isinstance(numbers,dict):  
                for key, value in numbers.items():
                    html += '<div class="number-%s">%s</div>' % (key,render_text(value),)
        else:
            next_group = groups_left[0]
            for p, numbers_p in numbers.items():
                html_p = '<div class="param-group">%s:</div>' % (p,)
                html_inner = render_number_table(numbers_p, params_so_far+[p], groups_left[1:])
                html_p += '<div class="cell-right">%s</div>' % (html_inner,)
                html += html_p
        return html    
            
    if 'Numbers' in data and len(data['Numbers']) > 0:
        numbers = data['Numbers']
        html += '<div class="collection-section">%s</div>' % ('Numbers',)
        html += render_number_table(numbers)
                            
    return render(request, 'collection.html', {'collection': collection, 'collection_html': html})

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
        'user': request.user,
        'error_message': error_message,
    }
    return render(request,'profile-edit.html',context)

def update(request, user_id):
    #TODO

    user = get_object_or_404(User, pk=user_id)
    profile = user.userprofile
    profile.bio = request.POST['bio']
    profile.save()
    return HttpResponseRedirect(reverse('db:profile'))

def parse_real_interval(s):
	r = RIF(s)

def suggestions(request):
	term_entered = request.GET['term']
	term = term_entered.strip(" \n")
	if term == '':
		return JsonResponse({},safe=True)

	def text_term_to_bytes(term):
		for i in range(SearchTerm.MAX_LENGTH_TERM_FOR_TEXT,0,-1):
			term_suffix = term[:i].lower() #substring of at most 4 letters
			term_bytes = SearchTerm.TERM_TEXT + term_suffix.encode()
			if len(term_bytes) <= SearchTerm.term.field.max_length:
				return term_bytes
		return SearchTerm.TERM_TEXT

	
	cZZplus = re.compile(r'\d+')
	cRIF = re.compile(r'([+-]?)(\d*)((?:\.\d*)?)((?:[eE]-?\d+)?)')
	cRIF_P = re.compile(r'([+-]?)(\d*)[pP]([+-]?)([1-9]\d*)')
	
	#Determine type of search term:
	
	matchZZ = cZZplus.match(term)
	if matchZZ != None and matchZZ.end() == len(term):
		#Given searchterm is a positive integer:
		term = text_term_to_bytes(term)

	else:
		matchRIF = cRIF.match(term)
		if matchRIF != None and matchRIF.end() == len(term):
			#Given searchterm is a real interval:
			sign, a, b, e = matchRIF.groups()
			if sign != '-':
				sign = ''
			if b != '':
				b = b[1:]
			exp = ZZ(e[1:]) if e != '' else 0 
			exp -= len(b)
			ab = (a + b).lstrip('0')
			ab_cropped = ab[:SearchTerm.MAX_LENGTH_TERM_FOR_REAL_FRAC]
			print("ab,ab_cropped:",ab,ab_cropped)
			exp += len(ab) - len(ab_cropped)
			f = ZZ(sign+ab_cropped) if ab_cropped != '' else 0			
			term = SearchTerm.TERM_REAL + \
				int(exp).to_bytes(SearchTerm.NUM_BYTES_REAL_EXPONENT,byteorder='big',signed=True) + \
				int(f).to_bytes(SearchTerm.NUM_BYTES_REAL_FRAC,byteorder='big',signed=True) 
			print("exp,f:",exp,f)
		
		else:
			matchRIF_P = cRIF_P.match(term)
			if matchRIF_P != None and matchRIF_P.end() == len(term):
				#Given searchterm is a real interval in "p-notation":
				signExp, exp, signFrac, frac = matchRIF_P.groups()
				print("signExp, exp, signFrac, frac:",signExp, exp, signFrac, frac)
				if signExp != '-':
					signExp = ''
				if signFrac != '-':
					signFrac = ''
				exp = ZZ(signExp + exp) if exp != '' else 0 
				frac_cropped = frac[:SearchTerm.MAX_LENGTH_TERM_FOR_REAL_FRAC]
				exp -= len(frac_cropped)
				f = ZZ(signFrac+frac_cropped)			
				term = SearchTerm.TERM_REAL + \
					int(exp).to_bytes(SearchTerm.NUM_BYTES_REAL_EXPONENT,byteorder='big',signed=True) + \
					int(f).to_bytes(SearchTerm.NUM_BYTES_REAL_FRAC,byteorder='big',signed=True) 
				print("exp,f:",exp,f)

			else:
				#Given searchterm is something else:
				term = text_term_to_bytes(term)

	try:
		searchterm = SearchTerm.objects.get(term=term)
	except SearchTerm.DoesNotExist:
		return JsonResponse({},safe=True)
	
	data = {}
	i = 1
	

	#for searchable in searchterm.searchables.all():
	for value in searchterm.values.order_by('-value'):
		searchable = value.searchable
	
		of_type = searchable.of_type
		data_i = {}
		if of_type == Searchable.TYPE_TAG:
			tag = searchable.tag
			data_i['value'] = str(i)
			data_i['label'] = ''
			data_i['type'] = 'tag'
			data_i['title'] = 'Tag: %s' % (tag.name,)
			data_i['subtitle'] = '%s collection%s, %s number%s' % (
				tag.collection_count,
				's' if tag.collection_count != 1 else '',
				tag.number_count,
				's' if tag.number_count != 1 else '',
			)
			data_i['url'] = reverse('db:tag', kwargs={'tag_name': tag.url()})
			#data_i['subtitle'] = 'dummy subtitle'
		elif of_type == Searchable.TYPE_COLLECTION:
			collection = searchable.collection
			data_i['value'] = str(i)
			data_i['label'] = ''
			data_i['type'] = 'collection'
			data_i['title'] = '%s' % (collection.title,)
			if collection.number_count != 1:
				data_i['subtitle'] = '%s numbers' % collection.number_count
			else:
				n = collection.my_numberapproxs.first()
				#r = RIF(n.lower,n.upper)
				#r = n.lower
				data_i['subtitle'] = '%s' % (n,)
			data_i['url'] = '/' + collection.url
		elif of_type == Searchable.TYPE_NUMBER:
			number = searchable.number
			collection = number.my_collection
			data_i['value'] = str(i)
			data_i['label'] = ''
			data_i['type'] = 'number'
			data_i['title'] = '%s' % (collection.title,)
			param = number.param.decode()
			if len(number.param) > 0: 
				data_i['subtitle'] = '%s (#%s)' % (number.to_RIF(), param)
			else:
				data_i['subtitle'] = '%s' % (number.to_RIF(),)
			data_i['url'] = '/' + "%s#%s" % (collection.url, param)
		
		#if 'url' in data_i:
		#	data_i['url'] += '?searchterm=%s' % (term_entered,)
		data[i] = data_i
		i += 1
	
	'''
	#Debug:
	data = {
		1: {"value": "1 value", "label": "", "type": "number", "title": "Pi", "subtitle": "3.14159265?", "url": "Pi"},
		2: {"value": "2 value", "label": "", "type": "number", "title": "E", "subtitle": "2.718281828?", "url": "E"},
		#2: {"label": "2 label", "value": "2 value"},
	}
	'''
	
	return JsonResponse(data,safe=True)
