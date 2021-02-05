#Needs to be run within numberdb-website/
#numberdb-data must have same 

#Assume we are in numberdb-data working directory.


import os
import django
from django.db import transaction

os.environ["DJANGO_SETTINGS_MODULE"] = 'numberdb.settings'
django.setup()
from db.models import Collection
from db.models import CollectionData
from db.models import Tag
#from db.models import NumberApprox
from db.models import Number
from db.models import SearchTerm
from db.models import Searchable
from db.models import SearchTermValue

from db.utils import number_param_groups_to_bytes

from git import Repo
import yaml
import os

path_data = "../numberdb-data/"

from db_builder.utils import normalize_collection_data
from db_builder.utils import load_yaml_recursively



repo = Repo(path_data) #numberdb-data repository
if repo.bare:
	raise ValueError("repository is bare")
#if repo.is_dirty():
#	raise ValueError("repository is dirty")  # check the dirty state
#repo.untracked_files             # retrieve a list of untracked files


reader = repo.config_reader()             # get a config reader for read-only access
#with repo.config_writer():       # get a config writer to change configuration
#    pass                         # call release() to be sure changes are written and locks are released

head = repo.head
commit = head.commit
tree = commit.tree

#r = repo
#h = repo.head
#c = h.commit
#t = c.tree
index = repo.index
#i = index

#next_ids_filename = os.path.join("data","next_ids.yaml")
collection_id_prefix = "C"

'''
try:
	with open(next_ids_filename,"r") as f:
		next_ids = yaml.load(f,Loader=yaml.BaseLoader)
		next_collection_id = next_ids["next_collection_id"]
		
except FileNotFoundError:
	next_collection_id = collection_id_prefix + "0"

print("next_collection_id:",next_collection_id)

'''

class MyTimer:
	'''
	A simple class that keeps track of several running times.
	Call startTimer("X") and later endTimer("X"), then this class saves
	how long the process "X" took.
	'''

	def __init__(self, get_time=walltime):
		self.get_time = get_time
		self.timers = {};
		self.startTimer("CPU time at start");
	
	def startTimer(self,timerName):
		self.timers[timerName] = self.get_time();

	def endTimer(self,timerName,verbose = True):
		self.timers[timerName] = self.get_time(self.timers[timerName]);
		if verbose:
			print("Time taken for "+timerName+":",self.timers[timerName]);
		return self.timers[timerName];

	def totalTime(self):
		return self.get_time(self.timers["CPU time at start"]);

	def toString(self,linePrefix = ""):
		result = "";
		for timerName, t in self.timers.items():
			if timerName != "CPU time at start":
				result += linePrefix+timerName+": "+str(t)+"\n";
		result += linePrefix+"Total time: "+str(self.totalTime());
		return result;
		
	def __str__(self):
		return self.toString()
		
	def __repr__(self):
		return self.__str__()
		
	def run(self,function,*args,**kwargs):
		timer_name = 'Function %s' % (function.__name__,)
		timer_name += '(%s)' % (', '.join('%s=%s' % (key,kwargs[key]) for key in kwargs),) 
		self.startTimer(timer_name)
		function(*args,**kwargs)
		self.endTimer(timer_name)
		
def id_to_int(id):
	return int(id[1:])


def iter_collections_bulk(weight="number_count", bulk_size=10000):
	'''
	returns iterator over a partition of 
	the elements of Collection.objects.all().	
	'''
	
	cs_bulk = []
	size = 0
	for c in Collection.objects.all():
		cs_bulk.append(c)
		if weight == "number_count":
			size += c.number_count
		else:
			size += weight
		
		if size < bulk_size:
			continue
			
		size = 0
		yield cs_bulk
		
		cs_bulk = []

	if len(cs_bulk) > 0:
		yield cs_bulk

@transaction.atomic
def delete_all_tables():
	print("DELETING ALL TABLES")

	SearchTermValue.objects.all().delete()
	SearchTerm.objects.all().delete()

	#NumberApprox.objects.all().delete()
	Number.objects.all().delete()
	CollectionData.objects.all().delete()
	Collection.objects.all().delete()

	Tag.objects.all().delete()

	Searchable.objects.all().delete()

@transaction.atomic
def build_collection_table(test_run=False):

	print("BUILDING COLLECTION TABLE")
	
	for item in tree.traverse():
		if item.type != 'blob':
			continue
		path, filename = os.path.split(item.path)
		if filename != "collection.yaml":
			continue

		#print("path:",path)

		path_filename = os.path.join(path_data,item.path)
		collection_data = load_yaml_recursively(path_filename)
		
		#print("y:",y)
		if 'ID' not in collection_data:
			raise ValueError('No ID in collection %s.' % (path,))
		id = collection_data['ID']
		#print("id:",id)
		#print("path:",path)
		url = os.path.split(path)[-1]
		
		collection_data = normalize_collection_data(collection_data)
		
		#Create Collection:
		c = Collection()
		c.cid = id
		c.cid_int = int(id[1:])
		c.title = collection_data['Title']
		c.title_lowercase = c.title.lower()
		c.url = url
		c.path = path
		c.of_type = Searchable.TYPE_COLLECTION #not anymore automatic
		#print("try saving c:",c)
		if not test_run:
			c.save()
		#print("saved c:",c)
		#print(type(c.pk))
		#print(c.pk, c.id)
		#c = Collection.objects.get(pk=c.pk)
		
		#Create CollectionData:
		c_data = CollectionData()
		#c_data.collection_id = c.id
		c_data.collection = c
		c_data.json = collection_data
		with open(path_filename) as f: #not recurse into yaml
			c_data.raw_yaml = f.read()
		print("c_data.raw_yaml:",c_data.raw_yaml)
		
		if not test_run:
			#print("try saving c_data:",c_data)
			c_data.save()
			#print("saved c_data:",c_data)

@transaction.atomic
def build_tag_table():
	print("BUILD TAG TABLE")
	for c_data in CollectionData.objects.all():
		c = c_data.collection
		collection_data = c_data.json

		#Create Tags:
		if 'Tags' in collection_data and len(collection_data['Tags']) > 0:
			for tag_name in collection_data['Tags']:
				tag, created = Tag.objects.get_or_create(name=tag_name)
				#OLD: tag.my_collections.add(c)	
				c.my_tags.add(tag)
				if created:
					tag.of_type = Searchable.TYPE_TAG #not anymore automatic
					tag.name_lowercase = tag_name.lower()
				tag.collection_count += 1
				tag.save()
		
		#c.save() #Does c.my_tags.add(tag) need to be saved?

def build_number_table():

	print("BUILD_NUMBER TABLE")

	def save_number(c, number, param):
		#print("save number,param:",number,param)
		x = None #just to declare x as local variable
		
		#TODO: Find more stable type queries:
		try:
			x = ZZ(number)
		except TypeError:
			try:
				x == QQ(number)
			except TypeError:
				try:
					x = RIF(number)
				except TypeError:
						x = RBF('[%s]' % (number,))
		
		
		p = number_param_groups_to_bytes(param)
		
		try:
			n = Number(sage_number = x)
		except OverflowError:
			x = RIF(x)
			n = Number(sage_number = x)
		n.of_type = Searchable.TYPE_NUMBER #not anymore automatic
		n.my_collection = c
		n.param = p
		n.save()

		return 1 #Count of saved numbers

	def traverse_number_table(c, numbers, params_so_far, groups_left):
		if isinstance(numbers,dict):
			if 'equals' in numbers:
				return 0 #not counted
			if 'number' in numbers:
				return traverse_number_table(c, numbers['number'], params_so_far, groups_left)
			if 'numbers' in numbers:
				return traverse_number_table(c, numbers['numbers'], params_so_far, groups_left)

		count = 0  
		if len(groups_left) == 0:
			#numbers is an entry for a number now, either a string or a dict:
			if isinstance(numbers,str):
				count += save_number(c, numbers, params_so_far)
			elif isinstance(numbers,list):           
				for number in numbers:
					count += save_number(c, number, params_so_far)
			elif isinstance(numbers,dict):
				if 'equals' not in numbers:
					for key, value in numbers.items():
						#print("key,value:",key,value)
						if key == 'number':
							count += save_number(c, value, params_so_far)
		else:
			next_group = groups_left[0]
			for p, numbers_p in numbers.items():
				count += traverse_number_table(c, numbers_p, params_so_far+[p], groups_left[1:])

		return count

	for c_data in CollectionData.objects.all():
		with transaction.atomic():
			c = c_data.collection
			data = c_data.json
			#print("data:",data)
			#print("c.title:",c.title)

			count = 0
			if 'Numbers' in data and len(data['Numbers']) > 0:
				numbers = data['Numbers']

				if 'Parameters' in data and len(data['Parameters']) > 0:
					parameters = data['Parameters'].keys() 
				else:
					parameters = []

				if 'Display properties' in data and 'group parameters' in data['Display properties']:
					param_groups = data['Display properties']['group parameters']
				else:
					param_groups = [[p] for p in parameters]

				count += traverse_number_table(c, numbers, params_so_far=[], groups_left=param_groups)
			
			#Update counts:
			c.number_count = count
			c.save()
			for tag in c.my_tags.all():
				tag.number_count += count
				tag.save()
		
@transaction.atomic
def add_sentence_to_search_index(list_of_sentence_searchable_value):

	value_dict = {}
		
	def add_term_to_search_index(word, searchable, value):
		for i in range(1, 1 + max(SearchTerm.MAX_LENGTH_TERM_FOR_TEXT,
									len(word))):
			subword = word.lower()[:i] #first i letters of the word
			term = SearchTerm.TERM_TEXT + subword.encode()
			if len(term) > SearchTerm.term.field.max_length:
				break

			key = (term, searchable.id)
			if key not in value_dict:
				value_dict[key] = value
			else:
				value_dict[key] = max(value, value_dict[key])
			
	#for run in ['searchterms','searchtermvalues']:
	for sentence, searchable, value in list_of_sentence_searchable_value:	
		for word in sentence.strip(" \n").split(" "):
			if word == "":
				continue
			terms = word.split("-")
			#terms = [word] #debug
			for term in terms:
				add_term_to_search_index(term, searchable, value)
			if len(terms) > 1:
				#Also add the whole word (e.g. "L-function"):
				add_term_to_search_index(word, searchable, value)

	#Create new searchterms in DB:
	terms = set(term for term, searchable_id in value_dict)
	searchterms = [SearchTerm(term = term) for term in terms]
	SearchTerm.objects.bulk_create(searchterms,ignore_conflicts=True)
	
	#Create new searchtermvalues in DB:
	searchtermvalues = [SearchTermValue(
							searchterm_id = term,
							searchable_id = searchable_id,
							value = value,
						) for (term,searchable_id),value in value_dict.items()]
	SearchTerm.searchables.through.objects.bulk_create(searchtermvalues)
	
			
def build_search_index_for_tags():
	print("BUILD SEARCH INDEX for TAGS")
	for tag in Tag.objects.all():
		#print(tag.name)
		add_sentence_to_search_index([(tag.name, tag.searchable_ptr, int(1000))])

def build_search_index_for_collection_titles():
	print("BUILD SEARCH INDEX for COLLECTION TITLES")
	for cs_bulk in iter_collections_bulk(weight=1,bulk_size=1000):
		list_of_sentence_searchable_value = \
			[(c.title, c.searchable_ptr, int(100)) for c in cs_bulk]
		add_sentence_to_search_index(list_of_sentence_searchable_value)

def build_search_index_for_collection_keywords():
	print("BUILD SEARCH INDEX for COLLECTION KEYWORDS")
	for cs_bulk in iter_collections_bulk(weight=1,bulk_size=1000):
		list_of_sentence_searchable_value = []
		for c in cs_bulk:
			keywords = c.data.json.get('Keywords')
			if keywords == None:
				continue
			for keyword in keywords:
				list_of_sentence_searchable_value.append((keyword, c.searchable_ptr, int(100)))
		add_sentence_to_search_index(list_of_sentence_searchable_value)

def build_search_index_for_fractional_parts():
	print("BUILD SEARCH INDEX for FRACTIONAL PARTS")
	for cs_bulk in iter_collections_bulk():
		list_of_sentence_searchable_value = []
		for c in cs_bulk:
			#print("c.title:",c.title)
			#print(c.my_numbers.first())
			for n in c.my_numbers.all():
				if n.number_type == Number.NUMBER_TYPE_ZZ:
					continue
				r = n.to_RIF().frac()
				#print("r:",r, n.number_type)
				if r.contains_zero():
					continue
				if r.lower() < 0:
					r += 1; 
				if r.diameter() > 0.1:
					continue
				str_r = str(r)
				if '.' not in str_r:
					continue
					
				#TODO: Bug if scientific notation is used for r:
					
				word = str(r).split(".")[1].strip("?")
				list_of_sentence_searchable_value.append((word, n, 1))
		add_sentence_to_search_index(list_of_sentence_searchable_value)

def build_search_index_for_real_numbers():
	print("BUILD SEARCH INDEX for REAL_NUMBERS")
	
	for cs_bulk in iter_collections_bulk():
		with transaction.atomic():

			value_dict = {}

			for c in cs_bulk:
				for n in c.my_numbers.all():
					r = n.to_RIF()
					if r.contains_zero():
						continue
					log10 = abs(r).log(10)
					if log10.diameter() > 0.5:
						continue
					exp = ZZ(log10.lower().floor())+1
					frac = r/RIF(10)^exp
					
					#r = frac * 10^exp and normally 0.1 <= frac < 1
					
					for i in range(1,SearchTerm.MAX_LENGTH_TERM_FOR_REAL_FRAC+1):
						frac_i = frac * RIF(10)^i
						exp_i = exp - i
						if frac_i.diameter() >= 0.5:
							break
						l = ZZ(frac_i.lower().floor())
						u = ZZ(frac_i.upper().ceil())
						if u > l+1:
							break
						
						for f in set((l,u)):
							term = SearchTerm.TERM_REAL + \
								int(exp_i).to_bytes(SearchTerm.NUM_BYTES_REAL_EXPONENT,byteorder='big',signed=True) + \
								int(f).to_bytes(SearchTerm.NUM_BYTES_REAL_FRAC,byteorder='big',signed=True) 
							
							value = int(10*i)
							key = (term, n.searchable_ptr_id)
							if key not in value_dict:
								value_dict[key] = value
							else:
								value_dict[key] = max(value, value_dict[key])
			

			#Create new searchterms in DB:
			terms = set(term for term, searchable_id in value_dict)
			searchterms = [SearchTerm(term = term) for term in terms]
			SearchTerm.objects.bulk_create(searchterms,ignore_conflicts=True)
			
			#Create new searchtermvalues in DB:
			searchtermvalues = [SearchTermValue(
									searchterm_id = term,
									searchable_id = searchable_id,
									value = value,
								) for (term,searchable_id),value in value_dict.items()]
			SearchTerm.searchables.through.objects.bulk_create(searchtermvalues)


def clean_search_index():
	print("CLEAN SEARCH INDEX")
	for searchterm in SearchTerm.objects.all():
		num_searchables = 0	
		searchables_to_stay = set()
		values_to_delete = []
		last_index = 0
		query = searchterm.values.order_by('-value')
		for value in query:
			last_index += 1
			if value.searchable_id in searchables_to_stay:
				#Already better value:
				values_to_delete.append(value)
				continue
				
			searchables_to_stay.add(value.searchable_id)
			num_searchables += 1
			if num_searchables >= SearchTerm.MAX_RESULTS:
				break
		
		#continue #debug
		
		with transaction.atomic():
			for value in values_to_delete:
				value.delete()
			#query.reverse()[:query.count()-SearchTerm.MAX_RESULTS].delete()
		
			
#timer = MyTimer(cputime)
timer = MyTimer(walltime)

with transaction.atomic():
	timer.run(build_collection_table,test_run=True)
	timer.run(delete_all_tables)
	timer.run(build_collection_table)
	timer.run(build_tag_table)	
	timer.run(build_number_table)

	timer.run(build_search_index_for_tags)
	timer.run(build_search_index_for_collection_titles)
	timer.run(build_search_index_for_collection_keywords)
	timer.run(build_search_index_for_fractional_parts)
	timer.run(build_search_index_for_real_numbers)
	#timer.run(clean_search_index)

print("Times:\n%s" % (timer,))



'''
print("new_collection_paths:",new_collection_paths)

new_filenames = []

for path in new_collection_paths:
	filename = os.path.join(path,"id.yaml")
	with open(filename,"w") as f:
		f.writelines([
			"# Automatically created file. Do NOT edit.\n",
			"# If you copy the containing folder, delete this file in the copy.\n",
			"\n",
			"id: %s\n" % (next_collection_id,),
			])
	new_filenames.append(filename)
	commit_message += "    %s: %s\n" % (next_collection_id, filename)

	print("saved ",filename)
	next_collection_id = succ_id(next_collection_id)

if len(new_filenames) == 0:
	print("Done: No new id needed.") 
	return True
 
with open(next_ids_filename,"w") as f:
	f.writelines([
		"# Automatically created file. Do NOT edit.\n",
		"# If you copy the containing folder, delete this file in the copy.\n",
		"\n",
		"next_collection_id: %s\n" % (next_collection_id,),
		])
	print("saved ",next_ids_filename)
	commit_message += "    updated %s\n" % (next_ids_filename,)
	new_filenames.append(next_ids_filename)
	
for filename in new_filenames:
	index.add([filename])


final_commit = index.commit(commit_message)
print("final_commit.type:",final_commit.type)		

#repo.active_branch.commit = repo.commit('HEAD~1')     


'''
