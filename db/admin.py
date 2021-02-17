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

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
	#fields = ('title',)
	pass
	
admin.site.register(CollectionData)
admin.site.register(CollectionSearch)
admin.site.register(Tag)
admin.site.register(Number)
admin.site.register(OeisNumber)
admin.site.register(OeisSequence)
admin.site.register(WikipediaNumber)



