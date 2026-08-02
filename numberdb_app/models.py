from django.db import models
from django.contrib.auth.models import User
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GistIndex, HashIndex
from django.contrib.postgres.fields import DecimalRangeField
from django.db.backends.postgresql.psycopg_any import NumericRange
from django.dispatch import receiver
from django.db.models.signals import post_save
#from django.contrib.gis.db import models as gis_models

from urllib.parse import quote_plus
from urllib.parse import unquote_plus

import numpy as np
#import pyhash 
import hashlib
import json
import math
from decimal import Decimal

from sage.all import infinity, ceil, log, I
from sage.rings.all import ZZ, QQ, RR, CC, RIF, CIF, RBF, CBF, Qp
from sage.rings.all import RealField, RealIntervalField, RealBallField
from sage.rings.all import ComplexField, ComplexIntervalField, ComplexBallField
from sage.rings.all import PolynomialRing
from utils.utils import is_pAdicField

from .common import type_names

from utils.utils import real_interval_to_pretty_string
from utils.utils import complex_interval_to_pretty_string
from utils.utils import to_bytes
from utils.utils import RIFprec, RBFprec
from utils.utils import CIFprec, CBFprec
from utils.utils import is_polynomial_ring
from utils.utils import polynomial_modulo_variable_names

#--- User data ---------------------------------------------------------

class UserProfile(models.Model):
	user = models.OneToOneField(
		User, 
		on_delete = models.CASCADE,
		related_name = 'profile',
	)
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
    
class Wanted(models.Model):
	user = models.ForeignKey(
		User,
		on_delete = models.CASCADE,
		related_name = 'wanteds',
	)
	title = models.CharField(
		unique = True,
		max_length = 256,
		db_index = True,
	)
	description = models.TextField(
		db_index = False,
	)
	search_vector = SearchVectorField(
	)
	date_updated = models.DateTimeField(auto_now=True)
	date_created = models.DateTimeField(auto_now_add=True)

	def url(self):
		return quote_plus(self.title)
		
	def from_url(url):
		title = unquote_plus(url)
		return Tag.objects.get(title=title)
		
	def __str__(self):
		return 'Wanted entry %s' % (self.title)

#--- Database of numbers etc. ------------------------------------------

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
	table_count = models.IntegerField(
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
		return 'Tag %s (%s/%s)' % (self.name,self.table_count,self.number_count)
		
	def to_serializable_dict(self,order_tables_by='-number_count'):
		return {
			'name': self.name,
			'table_count': self.table_count,
			'number_count': self.number_count,
			'tables': [
				table.to_serializable_dict()
				for table in self.tables.all().order_by(order_tables_by)
			],
		}


class ApiKey(models.Model):
	"""A token that raises a caller's API rate limit.

	Only a hash is stored. A key is shown once, when it is issued, and cannot
	be recovered afterwards -- a leaked database should not hand out working
	credentials, and there is no reason for the server to be able to read one
	back. Lookup is by ``prefix``, which is the first characters of the token
	and safe to display, so a user can tell their keys apart and revoke the
	right one.

	Revoked rather than deleted, so a key that turns up in a log or a shared
	notebook can be traced to when it was issued and last used.
	"""

	user = models.ForeignKey(
		User,
		on_delete = models.CASCADE,
		related_name = 'api_keys',
	)
	label = models.CharField(
		max_length = 64,
		blank = True,
		default = '',
	)
	prefix = models.CharField(
		max_length = 12,
		db_index = True,
	)
	hashed_key = models.CharField(
		max_length = 64,
	)
	created = models.DateTimeField(
		auto_now_add = True,
	)
	last_used = models.DateTimeField(
		null = True,
		blank = True,
	)
	revoked = models.BooleanField(
		default = False,
	)

	class Meta:
		ordering = ['-created']

	def __str__(self):
		return '%s (%s...)' % (self.label or 'API key', self.prefix)

	@staticmethod
	def hash_token(token):
		import hashlib
		return hashlib.sha256(token.encode('utf8')).hexdigest()

	@classmethod
	def issue(cls, user, label=''):
		"""Create a key. Returns (record, token); the token is shown once.

		The token is 256 bits from `secrets`, so it needs no slow hashing --
		there is nothing to guess and nothing to brute force. sha256 keeps the
		lookup cheap enough to do on every API request.
		"""
		import secrets
		token = secrets.token_urlsafe(32)
		record = cls.objects.create(
			user = user,
			label = label,
			prefix = token[:12],
			hashed_key = cls.hash_token(token),
		)
		return record, token

	@classmethod
	def authenticate(cls, token):
		"""The key this token belongs to, or None."""
		import secrets
		if not token or len(token) < 12:
			return None
		expected = cls.hash_token(token)
		for candidate in cls.objects.filter(prefix=token[:12], revoked=False):
			#Compared in constant time: the prefix narrows it to one row, and
			#a timing difference here would leak the stored hash byte by byte.
			if secrets.compare_digest(candidate.hashed_key, expected):
				return candidate
		return None

class Table(models.Model):

	#sub_id = models.AutoField(primary_key=True)
	tid = models.CharField(
		max_length=10, 
		unique=True, 
		#primary_key=True,
		db_index=True,
	)
	tid_int = models.IntegerField(
		db_index=True,
		primary_key=True,
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
		related_name = 'tables',
		#db_constraint=False,
	)
	number_count = models.IntegerField(   
		default = 0,
	)

	def __str__(self):
		return 'Table %s' % (self.title,)
		
	def to_serializable_dict(self):
		return {
			'tid': self.tid,
			'tid_int': self.tid_int,
			'url': self.url,
			'path': self.path,
			'title': self.title,
			'number_count': self.number_count,
		}
		
	def type_str(self, long_form = True):
		j = self.data.json
		if 'Data properties' in j:
			properties = j['Data properties']
			if 'type' in properties:
				t = properties['type']
				if long_form and t in type_names:
					return type_names[t]
				else:
					return t
		return None

class TableData(models.Model):

	table = models.OneToOneField(
		Table,
		related_name="data", 
		on_delete=models.CASCADE,
		#db_constraint=False,
	)
	#Full table data in json:
	json = models.JSONField(
		default = dict,
	)
	#Original content of table.yaml:
	raw_yaml = models.TextField(
		default = '',
	)
	#Normalized yaml of full table:
	full_yaml = models.TextField(
		default = '',
	)
	
	def __str__(self):
		return 'Data for %s' % (self.table,)

class TableSearch(models.Model):
	
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
	table = models.OneToOneField(
		Table,
		on_delete = models.CASCADE,
		related_name = 'search',
	)

	def __str__(self):
		return 'Search vector for %s' % (self.table,)

class Contributor(models.Model):
	
	author_and_email = models.CharField(
		max_length = 300,
		primary_key = True,
	)
	author = models.CharField(
		max_length = 200,
		db_index = True,
	)
	email = models.EmailField(
		db_index = True,
	)
	table_commit_count = models.IntegerField(   
		default = 0,
	)
	
	def __str__(self):
		return '%s (%s)' % (self.author, self.email)

class TableCommit(models.Model):
	
	hexsha = models.CharField(
		max_length = 40,
		#primary_key = True,
		db_index = True,
		unique = True,
	)
	contributor = models.ForeignKey(
		Contributor,
		on_delete=models.CASCADE,
		related_name = "table_commits",
	)	
	datetime = models.DateTimeField(
		auto_now = False,
		auto_now_add = False,
		db_index = True,
	)
	timezone = models.IntegerField(
		default = 0,
	)
	summary = models.CharField(
		max_length = 200,
		default = '',
	)
	message = models.TextField(
		default = '',
	)
	tables = models.ManyToManyField(
		Table,
		related_name = 'commits',
	)
	
	def __str__(self):
		return 'Commit "%s" (%s on %s)' % (
			self.summary,
			self.contributor,
			self.datetime,
		)

def wire_number(value):
	"""A number as JSON the client rebuilds by dispatch, never by unpickling.

	This used to be ``value.dumps()`` -- a Sage pickle, carried as a cp437
	string. Loading it is arbitrary code execution, so every consumer of the
	API had to trust the server completely, and anyone able to answer in its
	place owned the client. It also tied the wire format to Sage: the bytes are
	Sage objects, so no client without Sage could read a number, and the server
	could not stop producing them.

	The encoding is the one the sandbox already speaks (utils/number_json.py),
	so there is one format on both boundaries rather than two.

	None if the value has no wire form. exact_text carries the number in that
	case, and it is the more useful field for anything but Sage.
	"""
	try:
		from utils.number_json import encode_number
		return encode_number(value)
	except Exception:
		return None


def exact_relative_width(exact_text):
	"""How well the stored value is known, relative to its own size.

	Measured on the exact value rather than the float projection, because the
	two come apart in both directions: 101471818419863/165 is an exact rational
	whose projection spans 1.2e-4, and the subnormal entries are known in full
	while their projection keeps about one bit. The projection measures the
	projection; this measures the knowledge.

	Zero for an exactly-known value. None when the text cannot be parsed, which
	is treated downstream as "no reason to hide it" rather than as a defect.
	"""
	if not exact_text:
		return None
	try:
		from utils.numbers import parse_real
		low, high = parse_real(exact_text).bounds()
	except Exception:
		return None
	if high == low:
		return 0.0
	magnitude = max(abs(low), abs(high))
	if magnitude == 0:
		return float('inf')
	return float((high - low) / magnitude)


def findable_by_number(exact_text):
	"""Whether search by number would return a value written like this.

	The tables call this to mark the values it excludes, so that a reader who
	cannot find a number in the search can see why, rather than concluding the
	database does not have it. Search itself uses the stored measurement --
	SQL cannot parse exact_text -- so both must read the same threshold.
	"""
	from django.conf import settings
	width = exact_relative_width(exact_text)
	if width is None:
		return True
	return width <= getattr(settings, 'NUMBERDB_MAX_RELATIVE_WIDTH', 1e-5)


def searchable_range(lower, upper):
	"""The float bounds as one range, for the GiST index to answer overlap on.

	Bounds are inclusive. This is not a detail: psycopg2 does not canonicalise
	client side, so NumericRange(x, x) is built as ``[x, x)`` and reports
	isempty False, while Postgres reads that same range as *empty*. Every
	exactly-known value has lower == upper, so defaulting the bounds would
	silently exclude every integer and rational in the table from search.

	An end is left unbounded where the float projection saturated. 310 stored
	values are past what a double holds, so the projection gives +-inf, which
	is not a numeric and cannot be a numrange bound; unbounded is both what
	Postgres accepts and what is actually known -- the value lies beyond here.
	"""
	def bound(value):
		number = float(value)
		if math.isinf(number) or math.isnan(number):
			return None
		#Decimal(float) is the exact binary value, so the range never narrows
		#what the projection said and containment stays sound.
		return Decimal(number)

	return NumericRange(bound(lower), bound(upper), '[]')


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
	#The faithful value: canonical text in a documented format, as defined by
	#utils/numbers. This is the definition of the number; lower/upper and the
	#other columns below are a lossy projection used only to find candidates.
	#See docs/design/number-datastructures.md.
	exact_text = models.TextField(
		default = '',
		#Deliberately no db_index: a btree index row is capped at about 2704
		#bytes and the Igusa polynomials are longer, so building one fails
		#outright. This column is looked up by equality, so it carries a hash
		#index instead (see Meta below), which hashes the value and has no
		#length limit.
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
	#The searchable projection as a single range, so overlap can be indexed.
	#
	#lower/upper are kept: they are what the range is built from, and other
	#code still reads them. This column exists because a *conjunction* of two
	#btree ranges can only answer containment efficiently -- "stored interval
	#inside the query" -- which misses a coarsely stored value that contains
	#the query. Overlap needs one indexable object, hence a range with GiST.
	#
	#A bound is NULL where the float projection saturated: 310 values exceed
	#what a double can hold, and an unbounded range is the honest
	#representation of "we know it is beyond here". They are indexed normally
	#and score lowest, rather than being dropped from search entirely.
	value_range = DecimalRangeField(
		null = True,
		blank = True,
	)
	#The same treatment for the fractional part, which is searched separately
	#and had the same asymmetry: a fractional part known coarsely cannot sit
	#inside a precise query, so it was never returned.
	#
	#No wrap-around case to handle. Sage's frac() widens an interval straddling
	#an integer to [0,1] rather than splitting it, so the range stays a single
	#interval; those values are simply ones whose fractional part is unknown,
	#and they score last instead of being excluded.
	frac_range = DecimalRangeField(
		null = True,
		blank = True,
	)
	#How well this value is known, relative to its size -- see
	#exact_relative_width. Stored because it cannot be recomputed per query:
	#it needs exact_text parsed, which SQL cannot do.
	#
	#Search by number excludes values known too weakly to identify anything.
	#Kept as the measured quantity rather than a boolean so the cutoff stays a
	#constant in search.py, tunable without a rebuild.
	exact_relative_width = models.FloatField(
		null = True,
		blank = True,
		db_index = True,
	)
	table = models.ForeignKey(
		Table, 
		on_delete=models.CASCADE,
		related_name="numbers"
	)
	param = models.BinaryField(
		max_length = 32,
		db_index = True
	)

	class Meta:
		indexes = [
			HashIndex(fields=['exact_text'],
			          name='number_exact_hash'),
			GistIndex(fields=['value_range'],
			          name='number_range_gist'),
			GistIndex(fields=['frac_range'],
			          name='number_frac_range_gist'),
		]

	def number_type_bytes(self):
		return to_bytes(self.number_type)

	def number_blob_bytes(self):
		return to_bytes(self.number_blob)
	
	def param_bytes(self):
		return to_bytes(self.param)

	def param_str(self):
		return self.param_bytes().decode()

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

		ri_prec = RIFprec(r)
		ri = RIF(r)

		#should use ri here in order to use the correctly rounded number:
		self.lower = ri.lower()
		self.upper = ri.upper()
		self.value_range = searchable_range(self.lower, self.upper)
			
		frac = ri_prec.frac()
		if frac <= 0:
			frac += 1
		self.frac_lower = float(frac.lower())
		self.frac_upper = float(frac.upper())
		self.frac_range = searchable_range(self.frac_lower, self.frac_upper)


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
		return real_interval_to_pretty_string(self.to_RIF())

	def str_short(self):
		'''The uniform search-result view: every kind on the same real line.

		Rendered from exact_text in plain Python, so a page of results no
		longer needs Sage. Falls back to the old path only if exact_text is
		missing, which a rebuilt database does not produce.
		'''
		if self.exact_text:
			try:
				from utils.numbers import parse_real
				from utils.numbers.display import uniform_real_text
				low, high = parse_real(self.exact_text).bounds()
				return uniform_real_text(low, high)
			except Exception:
				pass
		return self.str_as_real_interval()

	def __str__(self):
		r = self.to_sage()
		if r.parent() == ZZ:
			return r.__str__()
			
		elif r.parent() == QQ:
			return r.__str__()
		
		elif r.parent() == RIF:
			return real_interval_to_pretty_string(r)
		
		elif r.parent() == RBF:
			return r.__str__().strip('[]')
			
		else:
			print("r:",r)
			raise NotImplementedError()

	def to_serializable_dict(self):
		return {
			'type': self.number_type_bytes().decode(),
			'param': self.param_str(),
			'number': wire_number(self.to_sage()),
			'exact_text': self.exact_text,
			'str_short': self.str_short(),
			'table_id': self.table.tid,
		}

class NumberPAdic(models.Model):

	#Format of number_string:
	#"<prime>,<valuation>,<digits>"
	#which represents
	#prime^valuation * sum_i digits[i]*prime^i + O(prime^(valuation+len(digits)))
	#Note: 0 is represented as "prime,0,000...000"
	
	NUMBER_TYPE_QP = b'p'
	
	number_type = models.BinaryField(
		max_length = 1,
		#choices = NUMBER_TYPES,
		default = NUMBER_TYPE_QP,
	)
	number_string = models.TextField(
		#max_length = 100,
		db_index = True,
	)
	#The faithful value: canonical text in a documented format, as defined by
	#utils/numbers. This is the definition of the number; lower/upper and the
	#other columns below are a lossy projection used only to find candidates.
	#See docs/design/number-datastructures.md.
	exact_text = models.TextField(
		default = '',
		#Deliberately no db_index: a btree index row is capped at about 2704
		#bytes and the Igusa polynomials are longer, so building one fails
		#outright. This column is looked up by equality, so it carries a hash
		#index instead (see Meta below), which hashes the value and has no
		#length limit.
	)
	prime = models.IntegerField(
		db_index = True,
	)
	valuation = models.IntegerField(
		db_index = True,
	)
	table = models.ForeignKey(
		Table, 
		on_delete=models.CASCADE,
		related_name="p_adic_numbers"
	)
	param = models.BinaryField(
		max_length = 32,
		db_index = True,
	)

	class Meta:
		indexes = [
			HashIndex(fields=['exact_text'],
			          name='numberpadic_exact_hash'),
		]

	def number_type_bytes(self):
		return to_bytes(self.number_type)

	def param_bytes(self):
		return to_bytes(self.param)

	def param_str(self):
		return self.param_bytes().decode()

	def __init__(self, *args, **kwargs):
		
		if not 'sage_number' in kwargs:
			super(NumberPAdic, self).__init__(*args, **kwargs)
			return
			
		r = kwargs.pop('sage_number')
		super(NumberPAdic, self).__init__(*args, **kwargs)
		
		#print("r:",r)
		if r == None:
			return

		elif not is_pAdicField(r.parent()):
			raise NotImplementedError("sage_number is of non-implemented type")
			
		Q_p = r.parent()
		p = Q_p.prime()
		
		if r == 0:
			prec = Q_p.precision_cap()
			valuation = 0
			expansion = [0 for i in range(prec)]
		else:
			prec = r.precision_absolute()
			valuation = r.valuation()
			unit = r.unit_part()
			expansion = unit.expansion()
	
		lenp = ceil(log(p,10))
		digits = '|'.join(
			('%0'+str(lenp)+'d') % (digit,) for digit in expansion
		)			
	
		self.prime = p
		self.valuation = valuation
		self.number_string = '%s,%s,%s' % (
			p,
			valuation,
			digits
		)
		
	def to_Qp(self):
		s = self.number_string
		s_prime, s_valuation, s_digits = s.split(',')
		#prime = ZZ(s_prime)
		#valuation = ZZ(s_valuation)
		prime = self.prime
		valuation = self.valuation
		
		digits = s_digits.split('|')
		Q_p = Qp(prime,prec=len(digits))
		result = Q_p(prime)**valuation * Q_p(sum(
			prime**i * ZZ(digit) for i,digit in enumerate(digits) 
		)).add_bigoh(len(digits))
		return result

	def to_sage(self):
		return self.to_Qp()

	def str_short(self):
		#exact_text is already the documented rendering for this kind.
		if self.exact_text:
			return self.exact_text
		r = self.to_sage()
		return str(r)
		
	def __str__(self):
		r = self.to_sage()
		return str(r)
		
	def to_serializable_dict(self):
		return {
			'type': self.number_type_bytes().decode(),
			'param': self.param_str(),
			'number': wire_number(self.to_sage()),
			'exact_text': self.exact_text,
			'str_short': self.str_short(),
			'table_id': self.table.tid,
		}

class NumberComplex(models.Model):

	NUMBER_TYPE_C = b'c'
	
	number_type = models.BinaryField(
		max_length = 1,
		#choices = NUMBER_TYPES,
		default = NUMBER_TYPE_C,
	)
	number_searchstring = models.TextField(
		#max_length = 32,
		max_length = 128,
		db_index = True,
	)
	#The faithful value: canonical text in a documented format, as defined by
	#utils/numbers. This is the definition of the number; lower/upper and the
	#other columns below are a lossy projection used only to find candidates.
	#See docs/design/number-datastructures.md.
	exact_text = models.TextField(
		default = '',
		#Deliberately no db_index: a btree index row is capped at about 2704
		#bytes and the Igusa polynomials are longer, so building one fails
		#outright. This column is looked up by equality, so it carries a hash
		#index instead (see Meta below), which hashes the value and has no
		#length limit.
	)

	table = models.ForeignKey(
		Table, 
		on_delete=models.CASCADE,
		related_name="complex_numbers"
	)
	param = models.BinaryField(
		max_length = 32,
		db_index = True,
	)
	re_lower = models.FloatField(
		db_index = True,
	)
	re_upper = models.FloatField(
		db_index = True,
	)
	im_lower = models.FloatField(
		db_index = True,
	)
	im_upper = models.FloatField(
		db_index = True,
	)

	class Meta:
		indexes = [
			HashIndex(fields=['exact_text'],
			          name='numbercomplex_exact_hash'),
		]

	def number_type_bytes(self):
		return to_bytes(self.number_type)

	def param_bytes(self):
		return to_bytes(self.param)

	def param_str(self):
		return self.param_bytes().decode()
		
	def _generic_transformation(self, complex_interval):
		return complex_interval * complex_interval.parent()(
			1.342756284106146837969155436776114,
			1.9876592605792759329874556398424
		)

	def __init__(self, *args, **kwargs):
		
		if not 'sage_number' in kwargs:
			super(NumberComplex, self).__init__(*args, **kwargs)
			return
			
		r = kwargs.pop('sage_number')
		super(NumberComplex, self).__init__(*args, **kwargs)
		
		#print("r:",r)
		if r == None:
			return

		elif r.parent() in [CBF, CBFprec, CC]:
			r = CIF(r)
		elif r.parent() in [CIF, CIFprec]:
			pass
		else:
			raise NotImplementedError("sage_number is of non-implemented type")
			
		CIFr = r.parent()
		r0 = CIF(r)
		self.re_lower = r.real().lower()
		self.re_upper = r.real().upper()
		self.im_lower = r.imag().lower()
		self.im_upper = r.imag().upper()
		
		t = self._generic_transformation(r0)
		#print('t:',t)
		exponent = t.abs().log(10).upper().ceil()
		#print('exponent:',exponent)
		t *= CIF(10)**(-exponent)
		#print('t:',t)
		searchstring = '%s%s%s' % (
			exponent,
			'-' if t.real() < 0 else '+',
			'-' if t.imag() < 0 else '+',
		)
		t = CIF(t.real().abs(), t.imag().abs())
		#base, num_digits = 10, 16
		base, num_digits = 2, 53
		for i in range(num_digits):
			t *= base
			try:
				re_digit = t.real().unique_floor()
				im_digit = t.imag().unique_floor()
				searchstring += '%s%s' % (
					re_digit,
					im_digit,
				)
				t -= re_digit + I*im_digit
			except ValueError:
				break
		self.number_searchstring = searchstring
	
	def to_CIF(self):
		return CIF(
			RIF(self.re_lower, self.re_upper),
			RIF(self.im_lower, self.im_upper),
		)

	def to_sage(self):
		return self.to_CIF()

	def str_short(self):
		'''The uniform view, capped the same way as reals.

		Not exact_text: stored complex values carry up to a hundred digits per
		component, which is right for the faithful value and unreadable in a
		column of results.
		'''
		if self.exact_text:
			try:
				from utils.numbers import parse_complex
				from utils.numbers.display import uniform_complex_text
				value = parse_complex(self.exact_text)
				return uniform_complex_text(value.real().bounds(),
				                            value.imag().bounds())
			except Exception:
				pass
		return complex_interval_to_pretty_string(self.to_sage())

	def __str__(self):
		return complex_interval_to_pretty_string(self.to_sage())

	def to_serializable_dict(self):
		return {
			'type': self.number_type_bytes().decode(),
			'param': self.param_str(),
			'number': wire_number(self.to_sage()),
			'exact_text': self.exact_text,
			'str_short': self.str_short(),
			'table_id': self.table.tid,
		}

class Polynomial(models.Model):

	#Format of number_string:
	#"<#variables>,<polynomial>"
	#which represents
	#polynomial in #variables variables.
	
	NUMBER_TYPE_POLYNOMIAL = b'['
	
	number_type = models.BinaryField(
		max_length = 1,
		#choices = NUMBER_TYPES,
		default = NUMBER_TYPE_POLYNOMIAL,
	)
	number_string = models.TextField(
		#max_length = 100,
		db_index = False, #use number_string_hash to search!
	)
	#128 bits, hex. Wide enough for a lookup that sends only a hash: the
	#server's own query filters on the full key as well, and a client's cannot.
	canonical_hash = models.CharField(
		max_length = 32,
		db_index = True,
		default = '',
	)
	number_string_hash = models.BigIntegerField(
		db_index = True,
	)
	#The faithful value: canonical text in a documented format, as defined by
	#utils/numbers. This is the definition of the number; lower/upper and the
	#other columns below are a lossy projection used only to find candidates.
	#See docs/design/number-datastructures.md.
	exact_text = models.TextField(
		default = '',
		#Deliberately no db_index: a btree index row is capped at about 2704
		#bytes and the Igusa polynomials are longer, so building one fails
		#outright. This column is looked up by equality, so it carries a hash
		#index instead (see Meta below), which hashes the value and has no
		#length limit.
	)

	variable_count = models.IntegerField(
		db_index = True,
	)
	table = models.ForeignKey(
		Table, 
		on_delete=models.CASCADE,
		related_name="polynomials"
	)
	param = models.BinaryField(
		max_length = 32,
		db_index = True,
	)

	class Meta:
		indexes = [
			HashIndex(fields=['exact_text'],
			          name='polynomial_exact_hash'),
		]

	def number_type_bytes(self):
		return to_bytes(self.number_type)

	def param_bytes(self):
		return to_bytes(self.param)

	def param_str(self):
		return self.param_bytes().decode()

	def __init__(self, *args, **kwargs):
		
		if not 'sage_polynomial' in kwargs:
			super(Polynomial, self).__init__(*args, **kwargs)
			return
			
		p = kwargs.pop('sage_polynomial')
		super(Polynomial, self).__init__(*args, **kwargs)
		
		#print("p:",p)
		if p == None:
			return

		if not is_polynomial_ring(p.parent()):
			raise NotImplementedError("sage_polynomial is of non-implemented type")

		self.variable_count = len(p.variables())

		#One canonicalisation, in plain Python, because a client has to be able
		#to compute this key too -- a polynomial of 58866 characters cannot be
		#sent in a URL, so a lookup sends a hash of the key instead, and both
		#sides must produce the same bytes.
		#
		#It replaces the Sage polynomial_modulo_variable_names, which grouped
		#polynomials identically across the whole corpus but wrote the key in a
		#format only Sage could reproduce. See the canonical-keys management
		#command, which checks the grouping against the real database.
		from utils.numbers.polynomial import parse_polynomial
		written = str(p).replace(' ', '')
		self.number_string = parse_polynomial(written).canonical_text()

		#The faithful value, so the object can be read back without depending
		#on another field having been filled in elsewhere. The builder
		#overwrites this with the documented rendering; until it does, this is
		#what the polynomial actually is.
		if not self.exact_text:
			self.exact_text = written
		
		#Python's hash()-function uses seeds that are randomly chosen during each session,
		#thus the following does not work:
		#self.number_string_hash = hash(self.number_string)
		#
		#We'd rather use pyhash, however it's currently not maintained:
		#self.number_string_hash = pyhash.fnv1_64()(self.number_string)-9223372036854775808
		#
		#Thus we use hashlib:
		blake = hashlib.blake2s(
			#data = bytes(self.number_string,encoding='cp437'),
			digest_size = 8,
			#usedforsecurity = False, #is not always supported!
		)
		self.canonical_hash = hashlib.blake2s(
			self.number_string.encode('utf8'), digest_size=16).hexdigest()
		blake.update(bytes(self.number_string,encoding='cp437'))
		polynomial_hash = int.from_bytes(
			blake.digest(),
			byteorder = 'big',
			signed = True,
		)
		#print('hash:',h)
		self.number_string_hash = polynomial_hash
		
	def to_sage(self):
		"""The polynomial itself, rebuilt from exact_text.

		Not from number_string, which is the *search key*: canonicalised under
		renaming of variables, so it identifies an equivalence class rather
		than this polynomial. It used to be read back this way, which quietly
		coupled the key's spelling to the ability to reconstruct a value --
		changing the key format broke reconstruction, which is how this came to
		light. exact_text is the faithful form and keeps the names the author
		wrote.
		"""
		from utils.numbers.polynomial import parse_polynomial
		text = self.exact_text.replace(' ', '')
		names = parse_polynomial(text).variables() or ['x']
		R = PolynomialRing(QQ, len(names), names)
		return R(text)

	def __str__(self):
		r = self.to_sage()
		return str(r)

	def str_short(self):
		#exact_text is already the documented rendering for this kind.
		if self.exact_text:
			return self.exact_text
		r = self.to_sage()
		return str(r)
		
	def to_serializable_dict(self):
		return {
			'type': self.number_type_bytes().decode(),
			'param': self.param_str(),
			'number': wire_number(self.to_sage()),
			'exact_text': self.exact_text,
			'str_short': self.str_short(),
			'table_id': self.table.tid,
		}

#--- External data -----------------------------------------------------

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
