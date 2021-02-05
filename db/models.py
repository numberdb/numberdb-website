from django.db import models
from django.contrib.auth.models import User

from django.dispatch import receiver
from django.db.models.signals import post_save

from urllib.parse import quote_plus
from urllib.parse import unquote_plus

import numpy as np

from sage import *
from sage.rings.all import *

from .utils import my_real_interval_to_string

class UserProfile(models.Model):
	user = models.OneToOneField(User, on_delete=models.CASCADE)
	bio = models.TextField(max_length=500, blank=True)

	date_updated = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)
	
	def __str__(self):
		return 'Profile of %s' % (self.user,)
	

@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
	if created:
		UserProfile.objects.create(user=instance)

@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
	if hasattr(instance,"profile"):
		instance.profile.save()
    




class Searchable(models.Model):

	TYPE_TAG = b't'
	TYPE_COLLECTION = b'c'
	TYPE_NUMBER = b'n'
	
	TYPES = [
		(TYPE_TAG, "Tag"),
		(TYPE_COLLECTION, "Type Collection"),
		(TYPE_NUMBER, "Number"),
	]
	
	of_type = models.BinaryField(
		max_length = 1,
		#choices = TYPES,
		default = TYPE_COLLECTION,
	)
	#Obtains the following entries by inheritance:
	# - collection
	# - numberapprox
	# - tag
	
	def __str__(self):
		if self.of_type == Searchable.TYPE_TAG:
			return self.tag.__str__()
		elif self.of_type == Searchable.TYPE_COLLECTION:
			return self.collection.__str__()
		elif self.of_type == Searchable.TYPE_NUMBER:
			return self.number.__str__()

class Tag(Searchable):

	#sub_id = models.AutoField(primary_key=True)
	name = models.CharField(
		max_length = 32,
		unique = True,
		#primary_key = True,
		db_index = True,
	)
	name_lowercase = models.CharField(
		max_length = name.max_length,
		#unique = True,
		#primary_key = True,
		db_index = True,
	)
	#collections = models.ManyToManyField(
	#	Collection,
	#	related_name = "tags",
	#)
	
	collection_count = models.IntegerField(
		default = 0,
	)
	number_count = models.IntegerField(
		default = 0,
	)
	
	#Don't set of_type here, rather do in once in build.sage:
	#def __init__(self, *args, **kwargs):
	#	super(Searchable, self).__init__(*args, **kwargs)
	#	self.of_type = Searchable.TYPE_TAG
	
	def url(self):
		return quote_plus(self.name)
		#return self.name
		
	def from_url(url):
		name = unquote_plus(url)
		return Tag.objects.get(name=name)
		
	def __str__(self):
		return 'Tag %s (%s/%s)' % (self.name,self.collection_count,self.number_count)
		

class Collection(Searchable):

	#sub_id = models.AutoField(primary_key=True)
	cid = models.CharField(
		max_length=10, 
		unique=True, 
		#primary_key=True,
		db_index=True,
	)
	cid_int = models.IntegerField(
		db_index=True,
		default=0,
	)
	url = models.CharField(
		max_length=256, 
		unique=True,
		db_index=True,
	)
	path = models.CharField(
		max_length=512, 
		unique=True,
		db_index=True,
	)
	title = models.CharField(
		max_length=256, 
		unique=True,
		db_index=True,
	)
	title_lowercase = models.CharField(
		max_length=title.max_length, 
		db_index=True,
		default = '',
	)
	my_tags = models.ManyToManyField(
		Tag,
		related_name = 'my_collections',
		#db_constraint=False,
	)
	number_count = models.IntegerField(   
		default = 0,
	)
	#subtitle = models.CharField(
	#	max_length = 32,
	#	unique = False,
	#}

	#Don't set of_type here, rather do in once in build.sage:
	#def __init__(self, *args, **kwargs):
	#	super(Searchable, self).__init__(*args, **kwargs)
	#	self.of_type = Searchable.TYPE_COLLECTION

	def __str__(self):
		return 'Collection %s' % (self.title,)

class CollectionData(models.Model):

	collection = models.OneToOneField(
		Collection,
		related_name="data", 
		on_delete=models.CASCADE,
		#db_constraint=False,
	)
	json = models.JSONField(
		default = dict,
	)
	raw_yaml = models.TextField(
		default = '',
	)
	
	def __str__(self):
		return 'Data for %s' % (self.collection,)

'''
class NumberApprox(Searchable):

	lower = models.FloatField(
	)
	upper = models.FloatField(
	)
	my_collection = models.ForeignKey(
		Collection, 
		on_delete=models.CASCADE,
		related_name="my_numberapproxs"
	)
	param = models.BinaryField(
		max_length = 16,
	)
	def __str__(self):
		r = RIF(self.lower,self.upper)
		if r.contains_zero():
			#Relative diameter won't make sense, so just print it normally:
			return r.__str__()
		if r.relative_diameter() < 0.001:
			#Enough relative precision,
			#thus print the number normally:
			return r.__str__()
		else:
			#Not enough relative precision, 
			#thus rather print the number as an interval:
			Rup = RealField(15,rnd='RNDU')
			Rdown = RealField(15,rnd='RNDD')
			return '[%s,%s]' % (Rdown(r.lower()),Rup(r.upper()))
		
		#Bad: RBF(r) for a real interval r is not "centered"!
		#It takes r.lower() as center and r.diameter() as radius!
		#return RBF(r).__str__().strip('[]')
'''

class Number(Searchable):

	NUMBER_TYPE_ZZ = b'z'
	NUMBER_TYPE_QQ = b'q'
	NUMBER_TYPE_RIF = b'r'
	NUMBER_TYPE_RBF = b'b'
	
	NUMBER_TYPES = [
		(NUMBER_TYPE_ZZ, "Integer"),
		(NUMBER_TYPE_QQ, "Rational number"),
		(NUMBER_TYPE_RIF, "Real interval"),
		(NUMBER_TYPE_RBF, "Real ball"),
	]
	
	HALF_BLOB_LENGTH = 8
	
	number_type = models.BinaryField(
		max_length = 1,
		#choices = NUMBER_TYPES,
		default = NUMBER_TYPE_RIF,
	)

	number_blob = models.BinaryField(
		max_length = 2 * HALF_BLOB_LENGTH,
		db_index = True, #Perhaps rather implement search via SearchTerm?
	)
	my_collection = models.ForeignKey(
		Collection, 
		on_delete=models.CASCADE,
		related_name="my_numbers"
	)
	param = models.BinaryField(
		max_length = 16,
	)
	
	def __init__(self, *args, **kwargs):
		
		if not 'sage_number' in kwargs:
			super(Searchable, self).__init__(*args, **kwargs)
			return
			
		#rather do this once in build.sage:
		#self.of_type = Searchable.TYPE_NUMBER

		
		r = kwargs.pop('sage_number')
		super(Searchable, self).__init__(*args, **kwargs)
		
		#print("r:",r)
		if r == None:
			return

		elif r.parent() == ZZ:
			self.number_type = Number.NUMBER_TYPE_ZZ
			self.number_blob = int(r).to_bytes(
				byteorder = 'big',
				length = 2 * Number.HALF_BLOB_LENGTH,
				signed = True,
			)

		elif r.parent() == QQ:
			self.number_type = Number.NUMBER_TYPE_QQ
			b0 = int(r.numerator()).to_bytes(
				byteorder = 'big',
				length = Number.HALF_BLOB_LENGTH,
				signed = True,
			)
			b1 = int(r.denominator()).to_bytes(
				byteorder = 'big',
				length = Number.HALF_BLOB_LENGTH,
				signed = False
			)       
			self.number_blob = b0 + b1

		elif r.parent() == RIF:
			self.number_type = Number.NUMBER_TYPE_RIF
			b0 = np.float64(r.lower()).tobytes()
			b1 = np.float64(r.upper()).tobytes()
			self.number_blob = b0 + b1

		elif r.parent() == RBF:
			self.number_type = Number.NUMBER_TYPE_RBF
			b0 = np.float64(r.center()).tobytes()
			b1 = np.float64(r.rad()).tobytes()
			self.number_blob = b0 + b1

		else:
			raise NotImplementedError("sage_number is of non-implemented type")

	def to_RIF(self):
		return RIF(self.to_sage())

	def lower(self):
		return self.to_RIF().lower()

	def upper(self):
		return self.to_RIF().upper()
    
	def to_RBF(self):
		return RBF(self.to_sage())

	def to_sage(self):
		b = self.number_blob
		
		if self.number_type == Number.NUMBER_TYPE_ZZ:
			i = int.from_bytes(b,byteorder='big',signed=True)
			return ZZ(i)
		
		elif self.number_type == Number.NUMBER_TYPE_QQ:
			b0 = b[:Number.HALF_BLOB_LENGTH]
			b1 = b[Number.HALF_BLOB_LENGTH:]
			p = int.from_bytes(b0,byteorder='big',signed=True)
			q = int.from_bytes(b1,byteorder='big',signed=False)
			return QQ(p)/QQ(q)
			
		elif self.number_type == Number.NUMBER_TYPE_RIF:
			b0 = b[:Number.HALF_BLOB_LENGTH]
			b1 = b[Number.HALF_BLOB_LENGTH:]
			lower = np.frombuffer(b0,dtype=np.float64)[0]
			upper = np.frombuffer(b1,dtype=np.float64)[0]
			return RIF(lower,upper)
		
		elif self.number_type == Number.NUMBER_TYPE_RBF:
			#TODO: Perhaps adjust how many bytes are used for 
			#center and accuracy:
			b0 = b[:Number.HALF_BLOB_LENGTH]
			b1 = b[Number.HALF_BLOB_LENGTH:]
			center = np.frombuffer(b0,dtype=np.float64)[0]
			radius = np.frombuffer(b1,dtype=np.float64)[0]
			return RBF(center,radius)

	def str_as_real_interval(self):
		return my_real_interval_to_string(self.to_RIF())

	def __str__(self):
		r = self.to_sage()
		if r.parent() == ZZ:
			return r.__str__()
			
		elif r.parent() == QQ:
			return r.__str__()
		
		elif r.parent() == RIF:
			return my_real_interval_to_string(r)
		
		elif r.parent() == RBF:
			return r.__str__().strip('[]')
			
		else:
			print("r:",r)
			raise NotImplementedError()

class SearchTerm(models.Model):
	
	MAX_RESULTS = 10
	
	MAX_LENGTH_TERM_FOR_TEXT = 8
	#MAX_LENGTH_TERM_FOR_INTS = 8
	#MAX_LENGTH_TERM_FOR_REAL_EXPONENT = 4
	MAX_LENGTH_TERM_FOR_REAL_FRAC = 8
	NUM_BYTES_REAL_EXPONENT = 4
	NUM_BYTES_REAL_FRAC = 4
	
	#First byte of term stores the type
	TERM_TEXT = b't'
	#TERM_INT = b'i'
	TERM_REAL = b'r'
	
	#We make term the private key, 
	#such that we can bulk_create them faster.
	term = models.BinaryField(
		max_length = 1 + max(
			MAX_LENGTH_TERM_FOR_TEXT, 
			MAX_LENGTH_TERM_FOR_REAL_FRAC,
			NUM_BYTES_REAL_EXPONENT + NUM_BYTES_REAL_FRAC,
		),						
		unique = True,
		primary_key = True, 
		#db_index = True
	)
	searchables = models.ManyToManyField(
		Searchable,
		related_name = '+', #No backward relation
		through='SearchTermValue',
        through_fields=('searchterm', 'searchable'),
	)
	
	def __str__(self):
		return 'Search term %s' % (self.term,)
	
class SearchTermValue(models.Model):

	searchterm = models.ForeignKey(
		SearchTerm, 
		on_delete=models.CASCADE,
        #db_constraint=False,
        related_name="values",
	)
	searchable = models.ForeignKey(
		Searchable, 
		on_delete=models.CASCADE,
        #db_constraint=False,
        related_name="values",
	)
	value = models.IntegerField(
		default = int(0),
		#db_index = True,
	)
	
	def __str__(self):
		return 'Value %s for %s -> %s' % (
			self.value, 
			self.searchterm, 
			self.searchable,
		)

