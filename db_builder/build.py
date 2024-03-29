#Needs to be run within numberdb-website/ as follows:
#sage -python db/builder.sage

#numberdb-data/ must lie in the same parent folder as numberdb-website/

import sys
from pathlib import Path

sys.path = [str(Path.cwd())] + sys.path #add path of current working directory

import os
import django
from django.db import transaction

os.environ["DJANGO_SETTINGS_MODULE"] = 'numberdb.settings'
django.setup()
from db.models import Table
from db.models import TableData
from db.models import TableSearch
from db.models import TableCommit
from db.models import Contributor
from db.models import Tag
from db.models import Number
from db.models import NumberPAdic
from db.models import NumberComplex
from db.models import Polynomial
from db.common import table_id_prefix, path_numberdb_data
from db.common import test_table_ids

from django.contrib.sites.models import Site

from sage.all import walltime, Integer
from sage.rings.all import ZZ, QQ
from sage.all import is_pAdicField

from utils.utils import number_param_groups_to_bytes
from utils.utils import to_bytes
from utils.utils import RIFprec
from utils.utils import RBFprec
from utils.utils import CIFprec
from utils.utils import CBFprec

from utils.utils import parse_integer
from utils.utils import parse_positive_integer
from utils.utils import parse_real_interval
from utils.utils import parse_fractional_part
from utils.utils import parse_p_adic
from utils.utils import parse_complex_interval
from utils.utils import parse_polynomial
from utils.utils import number_with_uncertainty_to_real_ball
from utils.utils import is_polynomial_ring

from utils.my_timer import MyTimer

from git import Repo
import yaml
import os
#from pydriller import RepositoryMining

from db_builder.utils import normalize_table_data
from db_builder.utils import load_yaml_recursively

from django.contrib.postgres.search import SearchQuery, SearchRank, SearchVector

def numberdb_data_repository(assert_branch = None):
	repo = Repo(str(path_numberdb_data)) #numberdb-data repository
	if assert_branch is not None:
		branch_name = repo.head.reference.name
		assert(branch_name == assert_branch)
	return repo

def numberdb_data_repository_tree():
	repo = numberdb_data_repository()
	
	tree = repo.head.commit.tree
	return tree


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
	Contributor.objects.all().delete()
	TableSearch.objects.all().delete()
	TableData.objects.all().delete()
	Table.objects.all().delete()
	Tag.objects.all().delete()

@transaction.atomic
def build_table_table(data_repo, test_run=False, test_data=False):

	print("BUILDING TABLE TABLE")
	
	tree = data_repo.head.commit.tree
	
	for item in tree.traverse():
		if item.type != 'blob':
			continue
		path, filename = os.path.split(item.path)
		if filename != "table.yaml":
			continue

		#print("path:",path)

		path_filename = path_numberdb_data / item.path
		table_data = load_yaml_recursively(path_filename)
		
		#print("y:",y)
		if 'ID' not in table_data:
			raise ValueError('No ID in table %s.' % (path,))
		id = table_data['ID']
		#print("id:",id)
		
		if test_data:
			if id not in test_table_ids:
				continue			
		
		#print("path:",path)
		url = os.path.split(path)[-1]
		
		table_data = normalize_table_data(table_data)
		
		#Create Table:
		c = Table()
		c.tid = id
		c.tid_int = int(id[1:])
		c.title = table_data['Title']
		c.title_lowercase = c.title.lower().replace('$','')
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
			
def build_table_commits(data_repo, test_data=False):
	print("BUILD TABLE_COMMIT_TABLE")
	
	#Build table of all commits:
	contributors = {}
	table_commits = []
	

	for i_commit, commit in enumerate(data_repo.iter_commits()):
		
		if test_data and i_commit >= 100:
			break
		
		#author = commit.author.name
		#author_email = commit.author.email


		'''
		contributor, created = Contributor.objects.get_or_create(
			author_and_email = '%s | %s' % (
				commit.author.name,
				commit.author.email,
			),
			defaults = {
				'author': commit.author.name,
				'email': commit.author.email,
			},		
		)
		'''
		
		contributor_pk = '%s | %s' % (
				commit.author.name,
				commit.author.email,
		),
		
		if contributor_pk not in contributors:
			contributors[contributor_pk] = Contributor(
				pk = contributor_pk,
				author = commit.author.name,
				email = commit.author.email,
				table_commit_count = int(1),	
			)
		else:
			contributors[contributor_pk].table_commit_count += int(1)

		#contributors.append(
		
		table_commits.append(TableCommit(
			hexsha = commit.hexsha,
			contributor_id = contributor_pk,
			datetime = commit.committed_datetime,
			timezone = commit.committer_tz_offset,
			summary = commit.summary,
			message = commit.message,			
		))
	#Remove 16 test commits:
	#table_commits = table_commits[:0] + table_commits[17:] 
	
	Contributor.objects.bulk_create(contributors.values())
	TableCommit.objects.bulk_create(table_commits)
	hexsha_to_pk = {
		commit.hexsha: commit.pk
		for commit in TableCommit.objects.all()
	}

	#Find commits that belong to tables:
	g = data_repo.git
	for c in Table.objects.all():
		main_filename = os.path.join(c.path,'table.yaml')
		log = g.log('--follow',main_filename)
		#print("log:",log)
		lines = log.splitlines()
		
		hexshas = []
		for l in lines:
			if l.startswith('commit '):
				hexshas.append(l[7:])

		TableCommit.tables.through.objects.bulk_create(
			TableCommit.tables.through(
				table_id = c.pk,
				tablecommit_id = hexsha_to_pk[hexsha],
			) for hexsha in hexshas if hexsha in hexsha_to_pk
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
				x = parse_real_interval(number, RIF=RIFprec, allow_rationals=False)
				if x == None:
					try:
						x = RBFprec('[%s]' % (number,))
					except ValueError:
						#Currently we interpret numbers with uncertainty 
						#as real balls, whose radius is 1 standard uncertainty.
						#That is, that the actual number lies within it
						#has probability 68%, which is not good.
						#We do this to make the number easier searchable,
						#which is the only current use of the Number-entry.
						#TODO: If other things than search is done for these
						#      numbers with uncertainty, consider their own data structure.
						x = number_with_uncertainty_to_real_ball(number, standard_deviations=1)
						if x == None:
							x = parse_complex_interval(number, CIF=CIFprec, allow_rationals=True)
							if x == None:
								x = parse_p_adic(number)
								if x == None:
									x = parse_polynomial(number)
									if x == None:
										print("unknown format (number will be ignored):", number)
										return 1 #still count it, even though it's not saved in db
		
		R = x.parent()
		
		if R.is_exact():
			if x in exact_numbers:
				#don't save duplicate exact numbers
				return 1 #still count it 
			else:
				exact_numbers.add(x)
		
		p = number_param_groups_to_bytes(param)
		#print("x:",x)
		
		if is_polynomial_ring(R):
			n = Polynomial(sage_polynomial = x)

		elif is_pAdicField(R):
			
			n = NumberPAdic(sage_number = x)

		elif x.imag() == 0:
		
			#Debug:
			#return 0
			
			try:
				n = Number(sage_number = x)
			except OverflowError:
				#print("make x to real interval")
				x = RIFprec(x)
				n = Number(sage_number = x)
			#n.of_type = Searchable.TYPE_NUMBER #not anymore automatic
	
		else:
			
			try:
				n = NumberComplex(sage_number = x)
			except OverflowError:
				#print("make x to complex interval")
				x = CIFprec(x)
				n = NumberComplex(sage_number = x)
		
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
			for key in ['number','numbers','polynomial','polynomials']:
				if key in numbers:
					return traverse_number_table(c, numbers[key], params_so_far, groups_left)

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
						if key in ['number','polynomial']:
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
			if ('Numbers' in data and len(data['Numbers']) > 0) or \
				('Data' in data and len(data['Data']) > 0):
				
				if 'Numbers' in data:
					numbers = data['Numbers']
				elif 'Data' in data:
					numbers = data['Data']
				

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

def build_numberdb_data(data_repo, test_data=False, timer=None):
	if timer == None:
		timer = MyTimer(walltime)
	timer.run(build_table_table,data_repo=data_repo,test_data=test_data)
	timer.run(build_table_commits,data_repo=data_repo,test_data=test_data)
	timer.run(build_tag_table)	
	timer.run(build_number_table)
	timer.run(build_search_index_for_tables)

if __name__ == '__main__':

	#timer = MyTimer(cputime)
	timer = MyTimer(walltime)
	
	data_repo = numberdb_data_repository(assert_branch = 'main')

	with transaction.atomic():
		timer.run(build_table_table,data_repo=data_repo,test_run=True)
		timer.run(delete_all_tables)
		build_numberdb_data(data_repo, test_data=False, timer=timer)
		timer.run(build_misc)

	print("Times:\n%s" % (timer,))

	print("Number count:", Number.objects.count())
	print("NumberPAdic count:", NumberPAdic.objects.count())
	print("NumberComplex count:", NumberComplex.objects.count())
	print("Polynomial count:", Polynomial.objects.count())
	print("Table count:", Table.objects.count())
	print("Tag count:", Tag.objects.count())
	print("TableCommit count:", TableCommit.objects.count())
