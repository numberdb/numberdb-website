from django.contrib import admin


from .models import UserProfile
from .models import Table
from .models import TableData
from .models import TableSearch
from .models import TableCommit
from .models import Contributor
from .models import Tag
from .models import Number
from .models import NumberPAdic
from .models import NumberComplex
from .models import OeisNumber
from .models import OeisSequence
from .models import WikipediaNumber

admin.site.register(UserProfile)


class NumberInline(admin.TabularInline):
    model = Number
    extra = 1

class NumberPAdicInline(admin.TabularInline):
    model = NumberPAdic
    extra = 1

class NumberComplexInline(admin.TabularInline):
    model = NumberComplex
    extra = 1
    
class TableDataInline(admin.StackedInline):
	model = TableData
	extra = 0

class TableSearchInline(admin.StackedInline):
	model = TableSearch
	extra = 0

class TableCommitInTableInline(admin.TabularInline):
	model = TableCommit.tables.through
	verbose_name = u"Commit"
	verbose_name_plural = u"Commits"
	extra = 0

@admin.register(Table)
class TableAdmin(admin.ModelAdmin):
	model = Table
	#inlines = (NumberInline,)

	'''
	fields = (
		'title',
		'title_lowercase',
		'cid',
		'cid_int',
		'url',
		'path',
		'tags',
		'number_count',
	)
	'''

	inlines = (
		NumberInline, 
		NumberPAdicInline, 
		NumberComplexInline, 
		TableDataInline,
		TableSearchInline,
		TableCommitInTableInline,
	)
	
	'''
	readonly_fields = ('data','search')

	def data(self, obj):
		return obj.data

	def search(self, obj):
		return obj.search
	'''

class TableCommitInline(admin.TabularInline):
	model = TableCommit
	verbose_name = u"Commit"
	verbose_name_plural = u"Commits"
	fields = (
		'summary',
	)
	extra = 0

@admin.register(Contributor)
class ContributorAdmin(admin.ModelAdmin):
	model = Contributor
	fields = (
		'author',
		'email',
	)
	inlines = (
		TableCommitInline,
	)

	
admin.site.register(TableData)
admin.site.register(TableSearch)
admin.site.register(TableCommit)
admin.site.register(Tag)
admin.site.register(Number)
admin.site.register(NumberPAdic)
admin.site.register(NumberComplex)
admin.site.register(OeisNumber)
admin.site.register(OeisSequence)
admin.site.register(WikipediaNumber)



