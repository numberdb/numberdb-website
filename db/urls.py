from django.urls import path, re_path

from . import views

app_name = 'db'
urlpatterns = [
    path('', views.home, name='home'),
    path('about', views.about, name='about'),
    path('help', views.help, name='help'),

    path('suggestions', views.suggestions, name='suggestions'),
    path('properties/<str:number>', views.properties, name='properties'),
    path('properties/<str:numerator>/<str:denominator>', views.properties_of_rational, name='properties'),

    path('advanced-search', views.advanced_search, name='advanced-search'),
    path('advanced-suggestions', views.advanced_suggestions, name='advanced-suggestions'),

    path('collections', views.collections, name='collections'),
    re_path(r'^(?P<cid>(C\d+))$', views.collection_by_cid, name='collection'),
    
    re_path(r'^history/(?P<cid>(C\d+))$', views.collection_history, name='collection-history'),

    path('tags', views.tags, name='tags'),
    path('tags/<str:tag_url>', views.tag, name='tag'),

    path('preview', views.preview, name='preview'),
    re_path(r'^preview/(?P<cid>(C\d+))$', views.preview, name='preview-collection'),

    path('profile', views.show_own_profile, name='profile'),
    path('profile/<int:other_user_id>/', views.show_other_profile, name='show-other-profile'),
    path('profile/edit/', views.edit, name='profile-edit'),
    path('profile/update/<int:user_id>/', views.update, name='profile-update'),

    path('debug', views.debug, name='debug'),

    re_path(r"^(?P<url>([\w'()-]+))$", views.collection_by_url, name='collection_by_url'),
]
