from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField
from django.dispatch import receiver
from django.db.models.signals import post_save

from urllib.parse import quote_plus
from urllib.parse import unquote_plus

import numpy as np

from sage import *
from sage.rings.all import *

from utils.utils import my_real_interval_to_string
from utils.utils import to_bytes
from utils.utils import RIFprec, RBFprec

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
    

class Tag(models.Model):

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
	collection_count = models.IntegerField(
		default = 0,
	)
	number_count = models.IntegerField(
		default = 0,
	)
	search_vector = SearchVectorField(
	)
	
	def url(self):
		return quote_plus(self.name)
		#return self.name
		
	def from_url(url):
		name = unquote_plus(url)
		return Tag.objects.get(name=name)
		
	def __str__(self):
		return 'Tag %s (%s/%s)' % (self.name,self.collection_count,self.number_count)
		

class Collection(models.Model):

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
	tags = models.ManyToManyField(
		Tag,
		related_name = 'collections',
		#db_constraint=False,
	)
	number_count = models.IntegerField(   
		default = 0,
	)

	def __str__(self):
		return 'Collection %s' % (self.title,)

class CollectionData(models.Model):

	collection = models.OneToOneField(
		Collection,
		related_name="data", 
		on_delete=models.CASCADE,
		#db_constraint=False,
	)
	#Full collection data in json:
	json = models.JSONField(
		default = dict,
	)
	#Original content of collection.yaml:
	raw_yaml = models.TextField(
		default = '',
	)
	#Normalized yaml of full collection:
	full_yaml = models.TextField(
		default = '',
	)
	
	def __str__(self):
		return 'Data for %s' % (self.collection,)

class CollectionSearch(models.Model):
	
	weight_A_text = models.TextField(
		default = '',
	)
	weight_B_text = models.TextField(
		default = '',
	)
	weight_C_text = models.TextField(
		default = '',
	)
	weight_D_text = models.TextField(
		default = '',
	)
	search_vector = SearchVectorField(
	)
	collection = models.OneToOneField(
		Collection,
		on_delete = models.CASCADE,
	)

	def __str__(self):
		return 'Search vector for %s' % (self.collection,)


class Number(models.Model):

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
		db_index = True, #Should rather have a constrained postgres hash index for integers!
	)
	lower = models.FloatField(
		db_index = True,
	)
	upper = models.FloatField(
		db_index = True,
	)
	frac_lower = models.FloatField(
		db_index = True,
	)
	frac_upper = models.FloatField(
		db_index = True,
	)
	collection = models.ForeignKey(
		Collection, 
		on_delete=models.CASCADE,
		related_name="numbers"
	)
	param = models.BinaryField(
		max_length = 16,
	)

	def number_type_bytes(self):
		return to_bytes(self.number_type)

	def number_blob_bytes(self):
		return to_bytes(self.number_blob)
	
	def param_bytes(self):
		return to_bytes(self.param)

	def __init__(self, *args, **kwargs):
		
		if not 'sage_number' in kwargs:
			super(Number, self).__init__(*args, **kwargs)
			return
			
		r = kwargs.pop('sage_number')
		super(Number, self).__init__(*args, **kwargs)
		
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

		elif r.parent() in (RIF, RIFprec):
			self.number_type = Number.NUMBER_TYPE_RIF
			b0 = np.float64(r.lower()).tobytes()
			b1 = np.float64(r.upper()).tobytes()
			self.number_blob = b0 + b1

		elif r.parent() in (RBF, RBFprec):
			self.number_type = Number.NUMBER_TYPE_RBF
			b0 = np.float64(r.center()).tobytes()
			b1 = np.float64(r.rad()).tobytes()
			self.number_blob = b0 + b1

		else:
			raise NotImplementedError("sage_number is of non-implemented type")
			
		ri = RIFprec(r)
		self.lower = ri.lower()
		self.upper = ri.upper()
		
		frac = ri.frac()
		if frac <= 0:
			frac += 1
		self.frac_lower = float(frac.lower())
		self.frac_upper = float(frac.upper())


	def to_RIF(self):
		return RIF(self.to_sage())
	
	def to_RBF(self):
		return RBF(self.to_sage())

	def to_sage(self):
		b = self.number_blob_bytes()
		number_type = self.number_type_bytes()
		
		if number_type == Number.NUMBER_TYPE_ZZ:
			i = int.from_bytes(b,byteorder='big',signed=True)
			return ZZ(i)
		
		elif number_type == Number.NUMBER_TYPE_QQ:
			b0 = b[:Number.HALF_BLOB_LENGTH]
			b1 = b[Number.HALF_BLOB_LENGTH:]
			p = int.from_bytes(b0,byteorder='big',signed=True)
			q = int.from_bytes(b1,byteorder='big',signed=False)
			return QQ(p)/QQ(q)
			
		elif number_type == Number.NUMBER_TYPE_RIF:
			b0 = b[:Number.HALF_BLOB_LENGTH]
			b1 = b[Number.HALF_BLOB_LENGTH:]
			lower = np.frombuffer(b0,dtype=np.float64)[0]
			upper = np.frombuffer(b1,dtype=np.float64)[0]
			return RIF(lower,upper)
		
		elif number_type == Number.NUMBER_TYPE_RBF:
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

class OeisNumber(models.Model):
	
	number = models.BigIntegerField(
		primary_key = True,
	)
	sequence_count = models.IntegerField(
		default = 0,
	)

class OeisSequence(models.Model):
	
	a_number = models.IntegerField(
		primary_key = True,
	)
	name = models.TextField(
		default = '',
	)
	numbers = models.ManyToManyField(
		OeisNumber,
		related_name = 'sequences',
	)

class WikipediaNumber(models.Model):
	
	number = models.BigIntegerField(
		primary_key = True,
	)
	url = models.URLField(
		default = '',
	)
