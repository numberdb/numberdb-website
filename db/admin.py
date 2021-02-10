from django.contrib import admin


from .models import UserProfile
from .models import Collection
from .models import CollectionData
from .models import CollectionSearch
from .models import Tag
from .models import Number

admin.site.register(UserProfile)

@admin.register(Collection)
class CollectionAdmin(admin.ModelAdmin):
	#fields = ('title',)
	pass
	
admin.site.register(CollectionData)
admin.site.register(CollectionSearch)
admin.site.register(Tag)
admin.site.register(Number)



