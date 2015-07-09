# from django.shortcuts import render

from django.shortcuts import get_object_or_404
from django.http import Http404
import django_filters
from rest_framework import status, permissions, generics, pagination
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.compat import OrderedDict
from rest_framework import filters
from core.models import Account, AccountSettings, Album, AlbumType, AlbumFile, Event, EventGuest, Follow
from core.serializers import (
    AccountSerializer, AccountSettingsSerializer, AlbumSerializer, AlbumFileSerializer,
    EventSerializer, EventGuestSerializer, EventGuestUpdateSerializer, AlbumUpdateSerializer,
    InAppNotificationSerializer, FollowingSerializer, FollowerSerializer, FollowerUpdateSerializer, StreamSerializer)
from core.permissions import IsAccountOwnerOrReadOnly, IsAlbumUploadableOrReadOnly, IsGrantedAccessToEvent,\
    IsGrantedAccessToAlbum, IsAccountOwnerOrDenied
from django.db.models import Q
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext as _
from django.contrib.gis.geos import Point
from geopy.geocoders import GoogleV3
from django.contrib.gis.measure import D
from django.utils import timezone
import logging
logger = logging.getLogger(__name__)


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'accounts': reverse('account-list', request=request, format=format),
        'albums': reverse('album-list', request=request, format=format),
        'events': reverse('event-list', request=request, format=format),
        'notifications': reverse('notification-list', request=request, format=format),
        'self': reverse('self-detail', request=request, format=format),
        'settings': reverse('self-settings', request=request, format=format),
    })


class MultipleFieldLookupMixin(object):
    """
    Apply this mixin to any view or viewset to get multiple field filtering
    based on a `lookup_fields` attribute, instead of the default single field filtering.
    """
    def get_object(self):
        queryset = self.get_queryset()             # Get the base queryset
        queryset = self.filter_queryset(queryset)  # Apply any filter backends
        filter = {}
        for field in self.lookup_fields:
            filter[field] = self.kwargs[field]
        obj = get_object_or_404(queryset, **filter)
        self.check_object_permissions(self.request, obj)
        return obj


class AccountList(generics.ListAPIView):
    "Provides a list of active Accounts."
    queryset = Account.objects.filter(status=Account.ACTIVE)
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, )


class AccountDetail(generics.RetrieveAPIView):
    "Show detailed information for the given account."
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, )


class AccountSelfDetail(generics.RetrieveUpdateAPIView):
    "Show account information for the logged-in user."

    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, )
    queryset = Account.objects.filter(status=Account.ACTIVE)

    def get_object(self):
        qs = self.get_queryset()
        return get_object_or_404(qs, id=self.request.user.id)


class AccountSettingsDetail(generics.RetrieveUpdateAPIView):

    serializer_class = AccountSettingsSerializer
    permission_classes = (permissions.IsAuthenticated, )
    queryset = AccountSettings.objects.filter(account__status=Account.ACTIVE)

    def get_object(self):
        qs = self.get_queryset()
        return get_object_or_404(qs, account_id=self.request.user.id)


class AlbumFilter(django_filters.FilterSet):
    name = django_filters.CharFilter(name='name', lookup_type='icontains')
    album_type = django_filters.NumberFilter(name='album_type__id')

    class Meta:
        model = Album
        fields = ['name', 'album_type']


class AlbumList(generics.ListCreateAPIView):
    """Shows the current account's active albums and albums of events he is a guest of
        OR
        Search album by name: /albums/?name=celebrate
        Search album by type: /albums/?album_type=5
    """
    serializer_class = AlbumSerializer
    permission_classes = (permissions.IsAuthenticated,)

    filter_class = AlbumFilter

    def get_queryset(self):
        ''' Include only albums user owns or event albums that user owns or guest of'''
        user = self.request.user
        return Album.active.filter(Q(owner=user)
                                   | Q(event__owner=user)
                                   | Q(event__eventguest__guest=user)).select_related('album_type').distinct()

    def perform_create(self, serializer):
        # If event is specified, AlbumType is set to DEFAULT_EVENT, else AlbumType is CUSTOM
        event = serializer.initial_data.get('event')
        if not event:
            custom_type = AlbumType.objects.get(name='CUSTOM')
            serializer.save(album_type=custom_type)
        else:
            event_album_type = AlbumType.objects.get(name='DEFAULT_EVENT')
            serializer.save(album_type=event_album_type)


class AlbumDetail(generics.RetrieveUpdateDestroyAPIView):

    queryset = Album.active.all()
    serializer_class = AlbumUpdateSerializer
    permission_classes = (permissions.IsAuthenticated,  IsGrantedAccessToAlbum)


class AlbumFileDetail(generics.RetrieveUpdateAPIView):

    queryset = AlbumFile.active.all().prefetch_related('thumbnails', 'albums')
    serializer_class = AlbumFileSerializer
    permission_classes = (permissions.IsAuthenticated, IsGrantedAccessToAlbum)  # TODO: Permissions on this

    def get_object(self):
        queryset = self.filter_queryset(self.get_queryset())
        filter_kwargs = {'pk': self.kwargs['pk']}
        albumfile = get_object_or_404(queryset, **filter_kwargs)

        self.check_object_permissions(self.request, albumfile)
        return albumfile


class AlbumFilesList(generics.ListCreateAPIView):
    "List the files in the album."

    permission_classes = (permissions.IsAuthenticated, IsAlbumUploadableOrReadOnly, IsGrantedAccessToAlbum)  # TODO
    serializer_class = AlbumFileSerializer

    def get_serializer_context(self):
        context = super(AlbumFilesList, self).get_serializer_context()
        context['album'] = self.get_album()
        return context

    def get_album(self):
        try:
            album = Album.active.select_related('album_type').get(pk=self.kwargs['pk'])
        except Album.DoesNotExist:
            raise Http404(_('Album does not exist'))
        return album

    def get_queryset(self):
        album = self.get_album()
        self.check_object_permissions(self.request, album)
        return album.albumfiles_queryset(album.owner)


class EventFilter(django_filters.FilterSet):
    title = django_filters.CharFilter(name='title', lookup_type='icontains')
    location = django_filters.CharFilter(name='location', lookup_type='icontains')
    min_start = django_filters.DateTimeFilter(name='start', lookup_type='gte')
    owner = django_filters.CharFilter(name='owner__name', lookup_type='icontains')
    owner_phone = django_filters.CharFilter(name='owner__phone', lookup_type='icontains')

    class Meta:
        model = Event
        fields = ['title', 'location', 'min_start', 'privacy', 'owner']


class EventList(generics.ListCreateAPIView):
    ''' Show all public events or private events that you are member (guest or own)
            OR
        Show all events that is in a certain distance to a location
        e.g: Find events in 100 miles radius of Costa Mesa CA
        api/events?vicinity='costa mesa'&miles=100
            OR
        Search events using query parameters
        api/events?min_start=2015-06-01 01:00:00
        api/events?title=party
        api/events?location=park
        api/events?privacy=1
        api/events?owner=henry
        api/events?owner_phone=888
    '''
    URL_PARAM_VICINITY = 'vicinity'
    URL_PARAM_MILES = 'miles'

    # permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EventSerializer
    paginate_by = 20

    # filter_backends = (filters.SearchFilter,)
    # search_fields = ('title', 'location')

    # queryset = Event.objects.all()
    filter_class = EventFilter

    def perform_create(self, serializer):
        instance = serializer.save(owner=self.request.user)

        # create a default album
        new_album = Album.objects.create(
            owner=self.request.user,
            event=instance,
            name='%s Album' % (instance.title),
            description='Default Album for Event',
            album_type=AlbumType.objects.get(name="DEFAULT_EVENT"))
        new_album.save()

    def get_queryset(self):
        miles = self.request.QUERY_PARAMS.get(self.URL_PARAM_MILES)
        vicinity = self.request.QUERY_PARAMS.get(self.URL_PARAM_VICINITY)

        events = Event.objects.all()

        if miles and vicinity:
            geolocator = GoogleV3()
            location = geolocator.geocode(vicinity)
            point = Point(location.longitude, location.latitude)
            events = Event.objects.filter(mpoint__dwithin=(point, D(mi=miles)))            

        # No private events what user dont own or guest of should be shown
        if isinstance(self.request.user, AnonymousUser):
            events = events.filter(privacy=Event.PUBLIC)
        else:
            events = events.exclude(Q(privacy=Event.PRIVATE),
                                    ~Q(owner=self.request.user) & ~Q(eventguest__guest=self.request.user))
        return events


class EventDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, IsGrantedAccessToEvent,)

    queryset = Event.objects.all().select_related('owner')
    serializer_class = EventSerializer

    def update(self, request, *args, **kwargs):
        ''' Update or partial update '''
        partial = kwargs.pop('partial', False)
        instance = self.get_object()

        # Update request.data with the existing data from instance,
        # Note: set partial=True on get_serializer does not work
        if partial:
            for att in instance.__dict__.keys():
                if att not in request.data.dict().keys():
                    request.data[att] = instance.__dict__[att]

        return super().update(request, *args, **kwargs)


class EventGuestList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, IsGrantedAccessToEvent,)

    # queryset = EventGuest.objects.all()  # EventGuest.objects.none()
    serializer_class = EventGuestSerializer
    paginate_by = 20

    def get_serializer_context(self):
        context = super(EventGuestList, self).get_serializer_context()
        context['event'] = self.get_event()
        return context

    def get_event(self):
        try:
            event = Event.objects.get(pk=self.kwargs['pk'])
        except Event.DoesNotExist:
            raise Http404(_('Event does not exist'))
        return event

    def get_queryset(self):
        event = self.get_event()
        self.check_object_permissions(self.request, event)
        return EventGuest.objects.filter(event=event)

    def create(self, request, *args, **kwargs):
        # Check  for Bulk creation
        many = isinstance(request.data, list)
        serializer = self.get_serializer(data=request.data, many=many)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)

        if many:
            return Response([serializer.data], status=status.HTTP_201_CREATED, headers=headers)
        else:
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class EventGuestDetail(MultipleFieldLookupMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                          IsGrantedAccessToEvent,)

    queryset = EventGuest.objects.all()
    serializer_class = EventGuestUpdateSerializer
    lookup_fields = ('event_id', 'guest_id')


class NotificationCustomPagination(pagination.PageNumberPagination):
    def get_paginated_response(self, data):
        return Response(OrderedDict([
            ('count', self.page.paginator.count),
            ('new', self.request.new_ntfs_count),
            ('next', self.get_next_link()),
            ('previous', self.get_previous_link()),
            ('results', data)
        ]))


class NotificationList(generics.ListAPIView):
    '''
    List of all received in-app notifications
    '''
    serializer_class = InAppNotificationSerializer
    permission_classes = (permissions.IsAuthenticated,)
    paginate_by = 20
    pagination_class = NotificationCustomPagination
    filter_backends = (filters.OrderingFilter,)
    ordering = ('-created',)

    def get_queryset(self):
        account = self.request.user
        # Get ntfs before updating last_ntf_checked
        received_ntfs = account.received_ntfs.all()
        # Sneak in the new ntfs count to be used in paginator
        self.request.new_ntfs_count = self.get_ntfs_since_last_check_count(account, received_ntfs)
        # Update account.last_ntf_checked
        account.last_ntf_checked = timezone.now()
        account.save()

        return received_ntfs

    def get_ntfs_since_last_check_count(self, account, received_ntfs):
        last_check = account.last_ntf_checked
        if last_check is not None:
            return received_ntfs.filter(created__gt=last_check).count()
        else:
            return received_ntfs.count()


class FollowingList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, IsAccountOwnerOrDenied)

    serializer_class = FollowingSerializer
    paginate_by = 20

    def get_account(self):
        try:
            account = Account.objects.get(pk=self.kwargs['pk'])
        except Account.DoesNotExist:
            raise Http404(_('Account does not exist'))
        else:
            return account

    def get_queryset(self):
        account = self.get_account()
        self.check_object_permissions(self.request, account)
        return account.followings.all()


class FollowerList(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated, IsAccountOwnerOrDenied)

    serializer_class = FollowerSerializer
    paginate_by = 20

    def get_account(self):
        try:
            account = Account.objects.get(pk=self.kwargs['pk'])
        except Account.DoesNotExist:
            raise Http404(_('Account does not exist'))
        else:
            return account

    def get_queryset(self):
        account = self.get_account()
        self.check_object_permissions(self.request, account)
        return account.followers.all()


class FollowerDetail(MultipleFieldLookupMixin, generics.RetrieveUpdateAPIView):
    permission_classes = (permissions.IsAuthenticated, IsAccountOwnerOrDenied)

    queryset = Follow.objects.all()
    serializer_class = FollowerUpdateSerializer
    lookup_fields = ('follower_id', 'followee_id')


class StreamList(generics.ListAPIView):
    permission_classes = (permissions.IsAuthenticated, IsAccountOwnerOrDenied)

    serializer_class = StreamSerializer
    paginate_by = 20

    def get_account(self):
        try:
            account = Account.objects.get(pk=self.kwargs['pk'])
        except Account.DoesNotExist:
            raise Http404(_('Account does not exist'))
        else:
            return account

    def get_queryset(self):
        account = self.get_account()
        self.check_object_permissions(self.request, account)
        return account.streams.all()

#EOF
