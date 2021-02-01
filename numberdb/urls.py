"""numberdb URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
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

