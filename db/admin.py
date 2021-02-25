from django.contrib import admin


from .models import UserProfile
from .models import Collection
from .models import CollectionData
from .models import CollectionSearch
from .models import Tag
from .models import Number
from .models import OeisNumber
from .models import OeisSequence
from .models import WikipediaNumber

admin.site.register(UserProfile)


class NumberInline(admin.TabularInline):
    model = Number
    extra = 1
    
class CollectionDataInline(admin.StackedInline):
	model = CollectionData
	extra = 0

class CollectionSearchInline(admin.StackedInline):
	model = CollectionSearch
	extra = 0

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
	model = Collection
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
		CollectionDataInline,
		CollectionSearchInline,
	)
	
	'''
	readonly_fields = ('data','search')

	def data(self, obj):
		return obj.data

	def search(self, obj):
		return obj.search
	'''
	
admin.site.register(CollectionData)
admin.site.register(CollectionSearch)
admin.site.register(Tag)
admin.site.register(Number)
admin.site.register(OeisNumber)
admin.site.register(OeisSequence)
admin.site.register(WikipediaNumber)



