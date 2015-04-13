# from django.shortcuts import render

from django.shortcuts import get_object_or_404
from django.http import Http404
from rest_framework import status, permissions, generics
from rest_framework.decorators import api_view
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.views import APIView
from core.models import Account, Album, AlbumType, AlbumFile, Event, EventGuest
from core.serializers import AccountSerializer, AlbumSerializer, AlbumFileSerializer, EventSerializer, EventGuestSerializer, EventGuestUpdateSerializer, AlbumUpdateSerializer
from core.permissions import IsAccountOwnerOrReadOnly, IsAlbumOwnerAndDeleteCustom, IsOwner, IsEventOwnerOrReadOnly, IsAlbumUploadableOrReadOnly
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
        # 'guests': reverse('eventguest-list', request=request, format=format),
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
        return get_object_or_404(queryset, **filter)  # Lookup the object

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
    "Shows the current account's active albums."

    def get_queryset(self):
        user = self.request.user
        return Album.active.filter(owner=user).select_related('album_type')  # TODO: will need to add in Event albums


    def perform_create(self, serializer):
        # If event is specified, AlbumType is set to DEFAULT_EVENT
        custom_type = AlbumType.objects.get(name='CUSTOM')
        try:
            event = Event.objects.get(pk=self.request.data.get('event'))
        except Event.DoesNotExist:
            serializer.save(owner=self.request.user, album_type=custom_type)
        else:
            event_album_type = AlbumType.objects.get(name='DEFAULT_EVENT')
            serializer.save(owner=self.request.user, album_type=event_album_type, event=event)

    serializer_class = AlbumSerializer
    permission_classes = (permissions.IsAuthenticated,)


class AlbumDetail(generics.RetrieveUpdateDestroyAPIView):

    def get_queryset(self):
        return Album.active.filter(owner=self.request.user).select_related('album_type')

    def get_object(self):
        album = super().get_object()
        album.files = list(album.albumfiles_queryset(self.request.user))
        return album

    serializer_class = AlbumUpdateSerializer
    permission_classes = (permissions.IsAuthenticated, IsAlbumOwnerAndDeleteCustom)


class AlbumFileDetail(generics.RetrieveUpdateAPIView):

    queryset = AlbumFile.active.all()
    serializer_class = AlbumFileSerializer
    permission_classes = (permissions.IsAuthenticated, )  # TODO: Permissions on this


class AlbumFilesList(generics.ListCreateAPIView):
    "List the files in the album."

    permission_classes = (permissions.IsAuthenticated, IsAlbumUploadableOrReadOnly)  # TODO
    serializer_class = AlbumFileSerializer
    # queryset = Album.active.all().select_related('album_type')

    def get_serializer_context(self):
        context = super().get_serializer_context()
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
        return album.albumfiles_queryset(self.request.user)
        # serializer = self.get_serializer(files, many=True)
        # return Response(serializer.data)

class EventList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    queryset = Event.objects.all()
    serializer_class = EventSerializer

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

class EventDetail(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                            IsEventOwnerOrReadOnly,)

    queryset = Event.objects.all()
    serializer_class = EventSerializer



class EventGuestList(generics.ListCreateAPIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)

    # queryset = EventGuest.objects.all() #replaced by list()
    serializer_class = EventGuestSerializer
    paginate_by = 20
    
    def perform_create(self, serializer):
        event_id = self.kwargs['event_id']
        event = Event.objects.get(pk=event_id)
        serializer.save(event=event)
    
    def get_queryset(self):
        event_id = self.kwargs['event_id']
        guests = EventGuest.objects.filter(event=event_id)
        return guests
    

class EventGuestDetail(MultipleFieldLookupMixin, generics.RetrieveUpdateDestroyAPIView):
    permission_classes = (permissions.IsAuthenticatedOrReadOnly,
                            IsEventOwnerOrReadOnly,)

    queryset = EventGuest.objects.all()
    serializer_class = EventGuestUpdateSerializer
    lookup_fields = ('event_id', 'guest_id')

    def perform_udpate(self, serializer):
        logger.debug('HERE ==========')

        # event_id = self.kwargs['event_id']
        # guest_id = self.kwargs['guest_id']
        # # eventguest = EventGuest.objects.get()

        serializer.save(event_id=event_id, guest_id=guest_id,rsvp=3)


class EvensAroundList(generics.ListCreateAPIView):
    ''' 
    Show all events that is in a certain distance to a location 
    Example: Find events in 100 miles radius of Costa Mesa CA
    /events_around?vicinity='costa mesa CA'&miles=100
    '''
    URL_PARAM_VICINITY = 'vicinity'
    URL_PARAM_MILES    = 'miles'

    permission_classes = (permissions.IsAuthenticatedOrReadOnly,)
    serializer_class = EventSerializer
    paginate_by = 20

    def get_queryset(self):
        miles = self.request.QUERY_PARAMS.get(self.URL_PARAM_MILES)#self.request.GET.get(self.URL_PARAM_MILES)
        vicinity = self.request.QUERY_PARAMS.get(self.URL_PARAM_VICINITY)#self.request.GET.get(self.URL_PARAM_VICINITY)

        geolocator = GoogleV3()
        location = geolocator.geocode(vicinity)
        point = Point(location.longitude, location.latitude)
        events = Event.objects.filter(mpoint__dwithin=(point, D(mi=miles)))
        
        return events


