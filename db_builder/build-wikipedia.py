#Data is taken from Wikipedia: www.wikipedia.org.

#Needs to be run within numberdb-website/

import sys
from pathlib import Path

sys.path = [str(Path.cwd())] + sys.path #add path of current working directory

import os
import django
from django.db import models
from django.db import transaction

os.environ["DJANGO_SETTINGS_MODULE"] = 'numberdb.settings'
django.setup()
from db.models import WikipediaNumber

import numpy as np
import urllib
from bs4 import BeautifulSoup 
import re

from sage.all import walltime

from utils.my_timer import MyTimer

#path_oeis_data = "db_builder/oeis-data/"


transaction.atomic
def delete_all_wikipedia_tables():
	print("DELETING ALL WIKIPEDIA TABLES")

	WikipediaNumber.objects.all().delete()


transaction.atomic
def build_wikipedia_number_table():

	print("BUILDING WIKIPEDIA_NUMBER TABLE")
	
	numbers = {}
	
	wiki_base_url = 'https://en.wikipedia.org/'
	
	def wiki_url(n):
		if n <= 10 or n == 100:
			return '%swiki/%s' % (wiki_base_url, n)
		else:
			return '%swiki/%s_(number)' % (wiki_base_url, n)
	
	def parse_wiki_number(n):
		print('n:',n)
		return int(n.replace(',',''))
	
	for n in range(-1,1000):
		numbers[n] = WikipediaNumber(
			number = n,
			url = wiki_url(n)
		)
		
	n0s = list(range(1000,10000+1,1000))
	n0s += list(range(20000,100000+1,10000))
	n0s += [10^k for k in range(6,9+1)]
	
	#n0s = [50000] #debug
	
	re_range = re.compile(r'^#([\d,]+)_to_([\d,]+)$')
	print('re_range:',re_range)
	
	for n0 in n0s:
		print('n0:',n0)
		
		url_n0 = wiki_url(n0)
		page = urllib.request.urlopen(url_n0)
		bs = BeautifulSoup(page.read())
	
		#for h3 in bs.find_all('h3'):
		#	for 
		
		ids = []
		id_bounds = {}
		
		for li in bs.find_all('li',attrs={'class':'toclevel-2'}):
			for a in li.find_all('a'):
				print('a:',a)
				if a.has_attr('href'):
					href = a.attrs['href']
					m = re_range.match(href)
					if m == None:
						continue
					n1, n2 = [parse_wiki_number(g) for g in m.groups()]
					print("n1, n2:",n1,n2)
					id = href[1:]
					id_bounds[id] = (n1,n2)
	
		#print("ids:",ids)
		#for id in ids:
		#	for span in h.find_all('span',attrs={'id':id}):
		#		print('span:',span)
	
		for h3 in bs.find_all('h3'):
			span = h3.find('span',attrs={'class':'mw-headline'})
			if span == None or not span.has_attr('id'):
				continue
			id = span.attrs['id']
			#print('id:',id)
			if id not in id_bounds:
				continue
			n1,n2 = id_bounds[id]
			print('h3:',h3)
			ul = h3.findNextSibling()
			for b in ul.find_all('b'):
				print('b:',b)
				a = b.find('a')
				span = b.find('span')
				print('a:',a)
				if a != None:
					print("a:",a)
					href = a.attrs['href'].lstrip('/')
					try:
						n = parse_wiki_number(a.text)
					except ValueError:
						continue
					url = '%s%s' % (wiki_base_url, href)
				elif span != None:
					if span.has_attr('id'):
						url = '%s#%s' % (wiki_url(n0),span.attrs['id'])
					else:
						url = '%s#%s' % (wiki_url(n0),id)
					try:
						n = parse_wiki_number(span.text)
					except ValueError:
						continue
				else:
					try:
						n = parse_wiki_number(b.text)
					except ValueError:
						continue
					url = '%s#%s' % (wiki_url(n0),id)

				if not (n >= n1 and n <= n2):
					continue
				numbers[n] = WikipediaNumber(
					number = n,
					url = url,
				)

	
		#break
		
	#print("numbers:",numbers)
	
	WikipediaNumber.objects.bulk_create(numbers.values())

		
if __name__ == '__main__':

	#timer = MyTimer(cputime)
	timer = MyTimer(walltime)

	#with transaction.atomic():
	timer.run(delete_all_wikipedia_tables)
	timer.run(build_wikipedia_number_table)

	print("Times:\n%s" % (timer,))

