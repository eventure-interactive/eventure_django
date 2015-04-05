from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from core import views

urlpatterns = [
    url(r'$^', views.api_root, name='api-root'),
    url(r'^accounts/$', views.AccountList.as_view(), name='account-list'),
    url(r'^accounts/(?P<pk>[0-9]+)/$', views.AccountDetail.as_view(), name='account-detail'),
    url(r'^albums/$', views.AlbumList.as_view(), name='album-list'),
    url(r'^albums/(?P<pk>[0-9]+)/$', views.AlbumDetail.as_view(), name='album-detail'),
    url(r'^albums/(?P<pk>[0-9]+)/files/$', views.AlbumFilesList.as_view(), name='albumfiles-list'),
    url(r'^albumfile/(?P<pk>[0-9]+)/$', views.AlbumFileDetail.as_view(), name='albumfile-detail'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
