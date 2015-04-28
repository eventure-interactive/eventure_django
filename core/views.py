# from django.shortcuts import render

from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework import filters
from core.models import Account, Album, AlbumType, AlbumFile, Event, EventGuest
from core.serializers import AccountSerializer, AlbumSerializer, AlbumFileSerializer, EventSerializer, \
    EventGuestSerializer, EventGuestUpdateSerializer, AlbumUpdateSerializer
from core.permissions import IsAccountOwnerOrReadOnly, IsAlbumUploadableOrReadOnly, IsGrantedAccessToEvent, IsGrantedAccessToAlbum
from django.db.models import Q
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext as _
from django.contrib.gis.geos import Point
from geopy.geocoders import GoogleV3
from django.contrib.gis.measure import D
import logging
logger = logging.getLogger(__name__)


@api_view(('GET',))
def api_root(request, format=None):
    return Response({
        'accounts': reverse('account-list', request=request, format=format),
        'albums': reverse('album-list', request=request, format=format),
        'events': reverse('event-list', request=request, format=format),
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


class AccountDetail(generics.RetrieveUpdateAPIView):
    "Show detailed information for the given account."
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, IsAccountOwnerOrReadOnly)


class AlbumList(generics.ListCreateAPIView):
    "Shows the current account's active albums and albums of events he is a guest of"

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

    serializer_class = AlbumSerializer
    permission_classes = (permissions.IsAuthenticated,)


class AlbumDetail(generics.RetrieveUpdateDestroyAPIView):

    queryset = Album.active.all()
    serializer_class = AlbumUpdateSerializer
    permission_classes = (permissions.IsAuthenticated,  IsGrantedAccessToAlbum)


class AlbumFileDetail(generics.RetrieveUpdateAPIView):

    queryset = AlbumFile.active.all()
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


class EventList(generics.ListCreateAPIView):
    ''' Show all public events or private events that you are member (guest or own)
            OR
        Show all events that is in a certain distance to a location
        e.g: Find events in 100 miles radius of Costa Mesa CA
        /events?vicinity='costa mesa'&miles=100
            OR
        Show events that has title or location contains string(s)
        e.g: Find events that has location or title contains 'pasadena'
        /events?search='pasadena'
    '''
    URL_PARAM_VICINITY = 'vicinity'
    URL_PARAM_MILES    = 'miles'

    permission_classes = (permissions.IsAuthenticated,)
    serializer_class = EventSerializer
    paginate_by = 20

    filter_backends = (filters.SearchFilter,)
    search_fields = ('title', 'location')

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
        else:
            # No private events that user dont own or guest of should be shown
            owner_guest = ~Q(owner=self.request.user) & ~Q(eventguest__guest=self.request.user)
            return Event.objects.exclude(Q(privacy=Event.PRIVATE), owner_guest)


class EventDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticated, IsGrantedAccessToEvent,)

    queryset = Event.objects.all()
    serializer_class = EventSerializer


class EventGuestList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticated, IsGrantedAccessToEvent,)

    # queryset = EventGuest.objects.all()  # EventGuest.objects.none()
    serializer_class = EventGuestSerializer
    paginate_by = 20

    def get_serializer_context(self):
        context = super().get_serializer_context()
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


