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
from db.models import Table
from db.models import TableData
from db.models import TableSearch
from db.models import TableCommit
from db.models import Tag
from db.models import Number
from db.models import NumberPAdic

from django.contrib.sites.models import Site

from utils.utils import number_param_groups_to_bytes
from utils.utils import to_bytes
from utils.utils import RIFprec
from utils.utils import RBFprec

from utils.utils import parse_integer
from utils.utils import parse_positive_integer
from utils.utils import parse_real_interval
from utils.utils import parse_fractional_part
from utils.utils import parse_p_adic


from git import Repo
import yaml
import os
#from pydriller import RepositoryMining

path_data = "../numberdb-data/"

from db_builder.utils import normalize_table_data
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

main = head.reference
assert(main.name == 'main') #assert that we are on main branch
log = main.log()

table_id_prefix = "T"


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


def iter_tables_bulk(weight="number_count", bulk_size=10000):
	'''
	returns iterator over a partition of 
	the elements of Table.objects.all().	
	'''
	
	cs_bulk = []
	size = 0
	for c in Table.objects.all():
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
	TableCommit.objects.all().delete()
	TableSearch.objects.all().delete()
	TableData.objects.all().delete()
	Table.objects.all().delete()
	Tag.objects.all().delete()

@transaction.atomic
def build_table_table(test_run=False):

	print("BUILDING TABLE TABLE")
	
	for item in tree.traverse():
		if item.type != 'blob':
			continue
		path, filename = os.path.split(item.path)
		if filename != "table.yaml":
			continue

		#print("path:",path)

		path_filename = os.path.join(path_data,item.path)
		table_data = load_yaml_recursively(path_filename)
		
		#print("y:",y)
		if 'ID' not in table_data:
			raise ValueError('No ID in table %s.' % (path,))
		id = table_data['ID']
		#print("id:",id)
		#print("path:",path)
		url = os.path.split(path)[-1]
		
		table_data = normalize_table_data(table_data)
		
		#Create Table:
		c = Table()
		c.tid = id
		c.tid_int = int(id[1:])
		c.title = table_data['Title']
		c.title_lowercase = c.title.lower()
		c.url = url
		c.path = path
		#c.of_type = Searchable.TYPE_TABLE #not anymore automatic
		#print("try saving c:",c)
		if not test_run:
			c.save()
		#print("saved c:",c)
		#print(type(c.pk))
		#print(c.pk, c.id)
		#c = Table.objects.get(pk=c.pk)
		
		#Create TableData:
		c_data = TableData()
		#c_data.table_id = c.id
		c_data.table = c
		c_data.json = table_data
		c_data.full_yaml = yaml.dump(table_data, sort_keys=False)
		with open(path_filename) as f: #not recurse into yaml
			c_data.raw_yaml = f.read()
		#print("c_data.raw_yaml:",c_data.raw_yaml)
		
		if not test_run:
			#print("try saving c_data:",c_data)
			c_data.save()
			#print("saved c_data:",c_data)
			
def build_table_commits():
	print("BUILD TABLE_COMMIT_TABLE")
	
	#Build table of all commits:
	table_commits = []
	for commit in repo.iter_commits():
		table_commits.append(TableCommit(
			hexsha = commit.hexsha,
			author = commit.author.name,
			author_email = commit.author.email,
			datetime = commit.committed_datetime,
			timezone = commit.committer_tz_offset,
			summary = commit.summary,
			message = commit.message,			
		))
	#Remove 16 test commits:
	#table_commits = table_commits[:0] + table_commits[17:] 
	
	TableCommit.objects.bulk_create(table_commits)
	hexsha_to_pk = {
		commit.hexsha: commit.pk
		for commit in TableCommit.objects.all()
	}

	#Find commits that belong to tables:
	g = repo.git
	for c in Table.objects.all():
		main_filename = os.path.join(c.path,'table.yaml')
		log = g.log('--follow',main_filename)
		print("log:",log)
		lines = log.splitlines()
		
		hexshas = []
		for l in lines:
			if l.startswith('commit '):
				hexshas.append(l[7:])

		TableCommit.tables.through.objects.bulk_create(
			TableCommit.tables.through(
				table_id = c.pk,
				tablecommit_id = hexsha_to_pk[hexsha],
			) for hexsha in hexshas
		)
	

@transaction.atomic
def build_tag_table():
	print("BUILD TAG TABLE")
	for c_data in TableData.objects.all():
		c = c_data.table
		table_data = c_data.json

		#Create Tags:
		if 'Tags' in table_data and len(table_data['Tags']) > 0:
			for tag_name in table_data['Tags']:
				tag, created = Tag.objects.get_or_create(name=tag_name)
				#OLD: tag.my_tables.add(c)	
				c.tags.add(tag)
				if created:
					#tag.of_type = Searchable.TYPE_TAG #not anymore automatic
					tag.name_lowercase = tag_name.lower()
				tag.table_count += 1
				tag.save()

	Tag.objects.update(search_vector = SearchVector('name', weight='A'))
		

def build_number_table():

	print("BUILD_NUMBER TABLE")
	
	exact_numbers = set() 
	#TODO: Find a better way to remove duplicate exact numbers 
	#when database gets bigger.

	def save_number(c, number, param):
		#print("save number,param:",number,param)
		x = None #just to declare x as local variable
		
		#TODO: Find more stable type queries:
		'''
		try:
			x = ZZ(number)
		except TypeError:
			try:
				x == QQ(number)
			except TypeError:
				try:
					#x = RIFprec(number)
					x = parse_real_interval(number)
					if x == None:
						raise TypeError()
				except TypeError:
						x = RBFprec('[%s]' % (number,))
		'''
		
		x = parse_integer(number)
		if x == None:
			try:
				x = QQ(number)
			except TypeError:
				x = parse_real_interval(number, RIF=RIFprec)
				if x == None:
					try:
						x = RBFprec('[%s]' % (number,))
					except ValueError:
						x = parse_p_adic(number)
						
						#if x != None:
						#	print("Currently p-adic numbers are not saved in db. x =",x)
						#	return 1
						
						if x == None:
							print("unknown format (number will be ignored):", number)
							return 1 #still count it, even though it's not saved in db
		
		if x.parent().is_exact():
			if x in exact_numbers:
				#don't save duplicate exact numbers
				return 1 #still count it 
			else:
				exact_numbers.add(x)
		
		p = number_param_groups_to_bytes(param)
		#print("x:",x)

		if is_pAdicField(x.parent()):
			
			n = NumberPAdic(sage_number = x)

		else:
		
			#Debug:
			#return 0
			
			try:
				n = Number(sage_number = x)
			except OverflowError:
				#print("make x to real interval")
				x = RIFprec(x)
				n = Number(sage_number = x)
			#n.of_type = Searchable.TYPE_NUMBER #not anymore automatic
		
		
		#print("debug0")
		n.table = c
		
		#print("debug1")
		n.param = p
	
		#print("before saving number")
		n.save()

		return 1 #Count of numbers

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

	total_number_count = 0
	
	for c_data in TableData.objects.all().order_by('table_id'):
		with transaction.atomic():
			c = c_data.table
			data = c_data.json
			#print("data:",data)
			#print("c.title:",c.title)

			#reset set of exact numbers for each table:
			#this makes repeated numbers in each table appear only once.
			exact_numbers = set() 

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
			total_number_count += count
			
	print(" === total_number_count:",total_number_count)

def build_search_index_for_tables():
	print("BUILD SEARCH INDEX for TABLES")
	
	for cs_bulk in iter_tables_bulk():
		with transaction.atomic():

			table_search_vectors = []

			for c in cs_bulk:
				c_search = TableSearch()
				c_search.table = c
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
	TableSearch.objects.update(search_vector = search_vector)

def build_misc():
	print("BUILD MISC TABLES")

	'''
	Site.objects.all().delete()
	Site(
		domain = 'numberdb.org',
		name = 'NumberDB',
	).save()
	'''
	site = Site.objects.first()
	if site.domain != 'numberdb.org' or \
		site.name != 'NumberDB':
		
		site.domain = 'numberdb.org'
		site.name = 'NumberDB'
		site.save()

#timer = MyTimer(cputime)
timer = MyTimer(walltime)

with transaction.atomic():
	timer.run(build_table_table,test_run=True)
	timer.run(delete_all_tables)
	timer.run(build_table_table)
	timer.run(build_table_commits)
	timer.run(build_tag_table)	
	timer.run(build_number_table)
	timer.run(build_search_index_for_tables)
	timer.run(build_misc)

print("Times:\n%s" % (timer,))

print("Number count:", Number.objects.count())
print("NumberPAdic count:", NumberPAdic.objects.count())
print("Table count:", Table.objects.count())
print("Tag count:", Tag.objects.count())
print("TableCommit count:", TableCommit.objects.count())
