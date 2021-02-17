#Needs to be run within numberdb-website/ as follows:
#sage 
#load('db_builder.sage')
#exit


#numberdb-data must have same 

#Assume we are in numberdb-data working directory.


import os
import django
from django.db import transaction

os.environ["DJANGO_SETTINGS_MODULE"] = 'numberdb.settings'
django.setup()
from db.models import Collection
from db.models import CollectionData
from db.models import CollectionSearch
from db.models import Tag
from db.models import Number

from utils.utils import number_param_groups_to_bytes
from utils.utils import to_bytes
from utils.utils import RIFprec
from utils.utils import RBFprec

from git import Repo
import yaml
import os

path_data = "../numberdb-data/"

from db_builder.utils import normalize_collection_data
from db_builder.utils import load_yaml_recursively

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector


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

collection_id_prefix = "C"


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

	Number.objects.all().delete()
	CollectionSearch.objects.all().delete()
	CollectionData.objects.all().delete()
	Collection.objects.all().delete()
	Tag.objects.all().delete()

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
		#c.of_type = Searchable.TYPE_COLLECTION #not anymore automatic
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
		c_data.full_yaml = yaml.dump(collection_data, sort_keys=False)
		with open(path_filename) as f: #not recurse into yaml
			c_data.raw_yaml = f.read()
		#print("c_data.raw_yaml:",c_data.raw_yaml)
		
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
				c.tags.add(tag)
				if created:
					#tag.of_type = Searchable.TYPE_TAG #not anymore automatic
					tag.name_lowercase = tag_name.lower()
				tag.collection_count += 1
				tag.save()

	Tag.objects.update(search_vector = SearchVector('name', weight='A'))
		

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
					x = RIFprec(number)
				except TypeError:
						x = RBFprec('[%s]' % (number,))
		
		
		p = number_param_groups_to_bytes(param)
		#print("x:",x)
		
		try:
			n = Number(sage_number = x)
		except OverflowError:
			#print("make x to real interval")
			x = RIFprec(x)
			n = Number(sage_number = x)
		#n.of_type = Searchable.TYPE_NUMBER #not anymore automatic
		
		#print("debug0")
		n.collection = c
		
		#print("debug1")
		n.param = p
	
		#print("before saving number")
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
			for tag in c.tags.all():
				tag.number_count += count
				tag.save()

def build_search_index_for_collections():
	print("BUILD SEARCH INDEX for COLLECTIONS")
	
	for cs_bulk in iter_collections_bulk():
		with transaction.atomic():

			collection_search_vectors = []

			for c in cs_bulk:
				c_search = CollectionSearch()
				c_search.collection = c
				json = c_data = c.data.json
				#c_search.save()
				c_search.weight_A_text = c.title
				if 'Keywords' in json:
					c_search.weight_A_text += ' ' + ' '.join(json['Keywords'])
				if 'Tags' in json:
					c_search.weight_B_text += ' ' + ' '.join(json['Tags'])
				if 'Definition' in json:
					c_search.weight_C_text = json['Definition']
				if 'Comments' in json:
					c_search.weight_D_text = ' '.join(json['Comments'].values())
				c_search.save()
				
	search_vector = SearchVector('weight_A_text',weight='A')
	search_vector += SearchVector('weight_B_text',weight='B')
	search_vector += SearchVector('weight_C_text',weight='C')
	search_vector += SearchVector('weight_D_text',weight='D')
	CollectionSearch.objects.update(search_vector = search_vector)
				
	
#timer = MyTimer(cputime)
timer = MyTimer(walltime)

with transaction.atomic():
	timer.run(build_collection_table,test_run=True)
	timer.run(delete_all_tables)
	timer.run(build_collection_table)
	timer.run(build_tag_table)	
	timer.run(build_number_table)
	
	timer.run(build_search_index_for_collections)

print("Times:\n%s" % (timer,))

