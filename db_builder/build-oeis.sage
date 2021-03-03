#Data is taken from www.oeis.org, the On-Line Encyclopedia of Integer Sequences.

#Needs to be run within numberdb-website/
#Assumed that update-oeis.sh was executed beforehand 


import os
import django
from django.db import models
from django.db import transaction

os.environ["DJANGO_SETTINGS_MODULE"] = 'numberdb.settings'
django.setup()
from db.models import OeisNumber
from db.models import OeisSequence

import numpy as np

path_oeis_data = "db_builder/oeis-data/"


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


transaction.atomic
def delete_all_oeis_tables():
	print("DELETING ALL OEIS TABLES")

	OeisNumber.objects.all().delete()
	OeisSequence.objects.all().delete()

transaction.atomic
def build_oeis_name_table():

	print("BUILDING OEIS SEQUENCE NAMES TABLE")
	
	i = 0
	
	filename_names = os.path.join(path_oeis_data,'names')
	with open(filename_names,'r') as f:
		sequences = []
		for line in f.readlines():
			if line.startswith('#'):
				continue
			if not line.startswith('A'):
				continue
			a, name = line.split(' ',maxsplit = 1)
			a_number = int(a[1:])
			name = name.rstrip('\n')
			
			sequence = OeisSequence(
				a_number = a_number,
				name = name,
			)
			sequences.append(sequence)
			i += 1
			print("i:",i)
			
			if i % 10000 == 0:
				OeisSequence.objects.bulk_create(sequences)
				sequences = []
				
		OeisSequence.objects.bulk_create(sequences)

'''
#OLD: Works but uses tons of memory (around 16GB)
@transaction.atomic
def build_oeis_number_table():

	print("BUILDING OEIS NUMBER TABLE")
	
	i = 0
	
	filename_numbers = os.path.join(path_oeis_data,'stripped')
	with open(filename_numbers,'r') as f:
		oeis_numbers = {}
		
		sequence_number_links = []

		for line in f.readlines():
			if line.startswith('#'):
				continue
			if not line.startswith('A'):
				continue
			a, numbers = line.split(' ',maxsplit = 1)
			a_number = int(a[1:])
			numbers_list = [int(n) for n in numbers.split(',') if len(n.lstrip('-'))>=3]
			numbers = set(numbers_list)
			
			for n in numbers:
				try:
					np.int64(n)
				except OverflowError:
					continue
				if n not in oeis_numbers:
					oeis_numbers[n] = OeisNumber(number = n, sequence_count = 1)
				else:
					oeis_numbers[n].sequence_count += 1
				sequence_number_links.append(
					OeisSequence.numbers.through(
						oeisnumber_id = n,
						oeissequence_id = a_number,
					)
				)
			i += 1
			print("i:",i)
		OeisNumber.objects.bulk_create(oeis_numbers.values())
		OeisSequence.numbers.through.objects.bulk_create(sequence_number_links)
'''


#@transaction.atomic
def build_oeis_number_table():

	print("BUILDING OEIS NUMBER TABLE")
	
	i = 0
	
	filename_numbers = os.path.join(path_oeis_data,'stripped')
	with open(filename_numbers,'r') as f:
		oeis_numbers = {}
		sequence_number_links = []

		for line in f.readlines():
			if line.startswith('#'):
				continue
			if not line.startswith('A'):
				continue
			a, numbers = line.split(' ',maxsplit = 1)
			a_number = int(a[1:])
			numbers_list = [int(n) for n in numbers.split(',') if len(n.lstrip('-'))>=3]
			numbers = set(numbers_list)
			
			for n in numbers:
				try:
					np.int64(n)
				except OverflowError:
					continue
				if n not in oeis_numbers:
					oeis_numbers[n] = OeisNumber(number = n, sequence_count = -1)
				#else:
				#	oeis_numbers[n].sequence_count += 1
				sequence_number_links.append(
					OeisSequence.numbers.through(
						oeisnumber_id = n,
						oeissequence_id = a_number,
					)
				)
			i += 1
			print("i:",i)

			if i % 1000 == 0:
				OeisNumber.objects.bulk_create(oeis_numbers.values(),ignore_conflicts=True)
				OeisSequence.numbers.through.objects.bulk_create(sequence_number_links,ignore_conflicts=True)
				oeis_numbers = {}
				sequence_number_links = []
			
		OeisNumber.objects.bulk_create(oeis_numbers.values(),ignore_conflicts=True)
		OeisSequence.numbers.through.objects.bulk_create(sequence_number_links,ignore_conflicts=True)


#@transaction.atomic
def build_oeis_sequence_counter():

	print("BUILDING OEIS SEQUENCE_COUNTER")
	
	i = 0

	#q = OeisNumber.objects.annotate(models.Count('sequences')).update(sequence_count=models.F('sequences__count'))
	
	'''
	q = OeisNumber.objects.update(
		sequence_count = models.Subquery(
			#OeisNumber.objects.filter(pk=models.OuterRef('pk')).count
			OeisNumber.sequences.through.objects.filter(oeisnumber_id = models.OuterRef('pk').count())
		)
	)
	'''
	
	q = OeisNumber.objects.update(sequence_count=models.Count('sequences'))
	
	'''
	numbers = []
	
	for n in OeisNumber.objects.iterator():
		n.sequence_count = n.sequences.count()
		numbers.append(n)
		
		i += 1
		print("i:",i)

		if i % 10000 == 0:
			OeisNumber.objects.bulk_update(numbers,['sequence_count'])
			numbers = []

	OeisNumber.objects.bulk_update(numbers,['sequence_count'])
	'''

#timer = MyTimer(cputime)
timer = MyTimer(walltime)

#with transaction.atomic():

#timer.run(delete_all_oeis_tables)
#timer.run(build_oeis_name_table)
#timer.run(build_oeis_number_table)
timer.run(build_oeis_sequence_counter)

print("Times:\n%s" % (timer,))

