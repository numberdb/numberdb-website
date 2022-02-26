from django.urls import path, re_path

from . import views
from . import api

app_name = 'db'
urlpatterns = [
    path('', views.home, name='home'),
    path('about', views.about, name='about'),
    path('help', views.help, name='help'),

    path('api/search', api.advanced_search_results, name='api-search'),
    path('api/table', api.table, name='api-table'),
    path('api/tag', api.tag, name='api-tag'),
    
    path('suggestions', views.suggestions, name='suggestions'),
    path('properties/<str:number>', views.properties, name='properties'),
    path('properties/<str:numerator>/<str:denominator>', views.properties_of_rational, name='properties'),

    path('advanced-search', views.advanced_search, name='advanced-search'),

    path('tables', views.tables, name='tables'),
    re_path(r'^(?P<tid>(T\d+))$', views.table_by_tid, name='table'),
    
    re_path(r'^history/(?P<tid>(T\d+))$', views.table_history, name='table-history'),

    path('tags', views.tags, name='tags'),
    path('tags/<str:tag_url>', views.tag, name='tag'),

    path('preview', views.preview, name='preview'),
    re_path(r'^preview/(?P<tid>(T\d+))$', views.preview, name='preview-table'),

    path('profile', views.show_own_profile, name='profile'),
    path('profile/<int:other_user_id>/', views.show_other_profile, name='show-other-profile'),
    path('profile/edit/', views.edit, name='profile-edit'),
    path('profile/update/<int:user_id>/', views.update, name='profile-update'),

    path('wanted', views.wanteds, name='wanteds'), #note: for the url we use the singular

    path('debug', views.debug, name='debug'),

    re_path(r"^(?P<url>([\w'()-]+))$", views.table_by_url, name='table_by_url'),
]
