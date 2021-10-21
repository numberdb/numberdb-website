"""
numberdb URL Configuration
"""

from django.contrib import admin
from django.urls import path, include
from django.contrib.auth.decorators import login_required

from . import views
from db import views as db_views
from django.conf import settings

DEBUG = settings.DEBUG


admin.site.login = login_required(admin.site.login)

urlpatterns = [
    #path('', db_views.home, name='home'),
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path('welcome/', db_views.welcome, name='welcome'),

    path('', include('db.urls',namespace='db')),
    #path('' if DEBUG else 'db/', include('db.urls',namespace='db')),
    #path('' if DEBUG else 'db', include('db.urls')),

    #path('', views.maintenance_in_progress, name='maintenance-in-progress')
    path('', views.in_development, name='in_development')

    #path('profile/', include('userprofile.urls',namespace='profile')),
]

