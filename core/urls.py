from django.conf.urls import patterns, url
from rest_framework.urlpatterns import format_suffix_patterns
from core import views

urlpatterns = [
    url(r'$^', views.api_root, name='api-root'),
    url(r'^accounts/$', views.AccountList.as_view(), name='account-list'),
    url(r'^accounts/(?P<pk>[0-9]+)/$', views.AccountDetail.as_view(), name='account-detail'),
    url(r'^accounts/(?P<pk>[0-9]+)/followings/$', views.FollowingList.as_view(), name='following-list'),
    url(r'^accounts/(?P<pk>[0-9]+)/followers/$', views.FollowerList.as_view(), name='follower-list'),
    url(r'^accounts/(?P<followee_id>[0-9]+)/followers/(?P<follower_id>[0-9]+)/$', views.FollowerDetail.as_view(), name='follower-detail'),
    # url(r'^accounts/(?P<pk>[0-9]+)/connections/$', views.ConnectionList.as_view(), name='connection-list'),
    # url(r'^accounts/(?P<followee_id>[0-9]+)/connections/(?P<follower_id>[0-9]+)/$', views.ConnectionDetail.as_view(), name='connection-detail'),
    url(r'^notifications/$', views.NotificationList.as_view(), name='notification-list'),
    url(r'^accounts/(?P<pk>[0-9]+)/streams/$', views.StreamList.as_view(), name='stream-list'),
    url(r'^albums/$', views.AlbumList.as_view(), name='album-list'),
    url(r'^albums/(?P<pk>[0-9]+)/$', views.AlbumDetail.as_view(), name='album-detail'),
    url(r'^albums/(?P<pk>[0-9]+)/files/$', views.AlbumFilesList.as_view(), name='albumfiles-list'),
    url(r'^albumfile/(?P<pk>[0-9]+)/$', views.AlbumFileDetail.as_view(), name='albumfile-detail'),
    url(r'^events/$', views.EventList.as_view(), name='event-list'),
    url(r'^events/(?P<pk>[0-9]+)/$', views.EventDetail.as_view(), name='event-detail'),
    url(r'^events/(?P<pk>[0-9]+)/guests/$', views.EventGuestList.as_view(), name='eventguest-list'),
    url(r'^events/(?P<event_id>[0-9]+)/guests/(?P<guest_id>[0-9]+)/$', views.EventGuestDetail.as_view(), name='eventguest-detail'),
    url(r'^self/$', views.AccountSelfDetail.as_view(), name='self-detail'),
    url(r'^self/settings/$', views.AccountSettingsDetail.as_view(), name='self-settings'),
    url(r'^authentication/login/', views.Login.as_view(), name='login'),
    url(r'^email-validate/(?P<validation_token>[\w|\-]+)/$', views.email_validate, name='email-validate'),
    url(r'^phone-validate/(?P<validation_token>[\w|\-]+)/$', views.phone_validate, name='phone-validate'),
]

urlpatterns = format_suffix_patterns(urlpatterns)
