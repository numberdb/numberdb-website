from django.contrib import admin

from .models import UserProfile
from .models import Collection
from .models import CollectionData
from .models import Tag
from .models import Number
from .models import SearchTerm
#from .models import Number


admin.site.register(UserProfile)

admin.site.register(Collection)
admin.site.register(CollectionData)
admin.site.register(Tag)
admin.site.register(Number)
admin.site.register(SearchTerm)


