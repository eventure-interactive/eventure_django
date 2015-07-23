# from django.shortcuts import render

from django.shortcuts import get_object_or_404, redirect
from django.http import Http404
import django_filters
from rest_framework import status, permissions, generics, pagination
from rest_framework.decorators import api_view
from rest_framework.parsers import JSONParser, FormParser
from rest_framework.response import Response
from rest_framework.reverse import reverse
from rest_framework.renderers import JSONRenderer
from rest_framework.compat import OrderedDict
from rest_framework.views import APIView
from rest_framework import filters
from core.models import (
    Account, AccountSettings, AccountStatus, Album, AlbumType, AlbumFile, Event, EventGuest,
    Follow, CommChannel, InAppNotification, PasswordReset, GoogleCredentials)
from core.serializers import (
    AccountSerializer, AccountSettingsSerializer, AlbumSerializer, AlbumFileSerializer, EventSerializer,
    EventGuestSerializer, EventGuestUpdateSerializer, AlbumUpdateSerializer, InAppNotificationSerializer,
    FollowingSerializer, FollowerSerializer, FollowerUpdateSerializer, StreamSerializer, AccountSelfSerializer,
    LoginFormSerializer, LoginResponseSerializer, GoogleAuthorizationSerializer, PasswordResetFormSerializer, VerifyPasswordResetFormSerializer)
from core.permissions import IsAccountOwnerOrReadOnly, IsAlbumUploadableOrReadOnly, IsGrantedAccessToEvent,\
    IsGrantedAccessToAlbum, IsAccountOwnerOrDenied, IsAuthenticatedOrReadOnly
from core import common
from core import tasks
from django.db.models import Q
from django.db import transaction
from django.contrib.auth.models import AnonymousUser
from django.utils.translation import ugettext as _
from django.contrib.gis.geos import Point
from geopy.geocoders import GoogleV3
from django.contrib.gis.measure import D
from django.contrib.auth import authenticate, login, logout
from django.utils import timezone
from django.contrib.auth import login
from django.conf import settings
from oauth2client.client import FlowExchangeError, OAuth2WebServerFlow, AccessTokenRefreshError
from oauth2client.django_orm import Storage
from googleapiclient.errors import HttpError
import httplib2
from apiclient.discovery import build
import datetime
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
        'self-google-connect': reverse('google-connect', request=request, format=format),
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


class AccountList(generics.ListCreateAPIView):
    "Provides a list of active Accounts."
    queryset = Account.actives.filter()
    serializer_class = AccountSerializer
    # permission_classes = (permissions.IsAuthenticated, )


class AccountDetail(generics.RetrieveAPIView):
    "Show detailed information for the given account."
    queryset = Account.objects.all()
    serializer_class = AccountSerializer
    permission_classes = (permissions.IsAuthenticated, )


class AccountSelfDetail(generics.RetrieveUpdateAPIView):
    "Show account information for the logged-in user."

    serializer_class = AccountSelfSerializer
    permission_classes = (permissions.IsAuthenticated, )
    queryset = Account.actives.filter()

    def get_object(self):
        qs = self.get_queryset()
        return get_object_or_404(qs, id=self.request.user.id)

    def delete(self, request):
        ''' Deactivate account '''
        account = self.get_object()
        account.status = AccountStatus.DEACTIVE_FORCEFULLY
        account.save()
        return Response({'successful': 'Account has been deactivated.'}, status=status.HTTP_204_NO_CONTENT)


class AccountSettingsDetail(generics.RetrieveUpdateAPIView):

    serializer_class = AccountSettingsSerializer
    permission_classes = (permissions.IsAuthenticated, )
    queryset = AccountSettings.objects.filter(account__status=AccountStatus.ACTIVE)

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

    permission_classes = (IsAuthenticatedOrReadOnly,)
    serializer_class = EventSerializer
    paginate_by = 20

    # filter_backends = (filters.SearchFilter,)
    # search_fields = ('title', 'location')

    # queryset = Event.objects.all()
    filter_class = EventFilter

    def perform_create(self, serializer):
        self.check_object_permissions(self.request, None)

        instance = serializer.save(owner=self.request.user)

        # create a default album
        Album.objects.create(
            owner=self.request.user,
            event=instance,
            name='%s Album' % (instance.title),
            description='Default Album for Event',
            album_type=AlbumType.objects.get(name="DEFAULT_EVENT"))

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


class Login(APIView):
    "Authenticate user."

    parser_classes = (JSONParser, FormParser)
    render_classes = (JSONRenderer, )

    serializer_class = LoginFormSerializer

    _msg = 'Unable to authenticate with the given login_id and password combination'

    @staticmethod
    def _get_user(login_id):
        try:
            user = Account.actives.get(Q(phone=login_id) | Q(email=login_id))
        except Account.DoesNotExist:
            logger.info('User with login_id "{}" not found'.format(login_id))
            return None

        return user

    @staticmethod
    def do_login(request, login_id, password):
        "Returns the user's Account if we logged in the user successfully, otherwise None."

        user = Login._get_user(login_id)
        if not user:
            return False

        auth_user = authenticate(email=user.email, password=password)
        if auth_user:
            login(request, auth_user)
        else:
            logger.info('Unable to authenticate user: {}'.format(user))

        return auth_user

    def post(self, request):
        serializer = LoginFormSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        login_id = serializer.data['login_id']
        password = serializer.data['password']

        auth_user = self.do_login(request, login_id, password)

        if not auth_user:
            return Response({'authentication_error': self._msg}, status=422)

        account_url = reverse('account-detail', kwargs={'pk': auth_user.id}, request=request)
        serializer = LoginResponseSerializer({'account': account_url, 'logged_in': True})
        return Response(serializer.data)

    def delete(self, request):

        logout(request)
        return Response(None, status=204)


class SendPasswordReset(APIView):

    parser_classes = (JSONParser, FormParser)
    render_classes = (JSONRenderer, )

    serializer_class = PasswordResetFormSerializer

    def post(self, request):
        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        common.send_password_reset(serializer.data, request)

        return Response({'status': 'sending verification email (maybe)'}, status=202)


class VerifyPasswordReset(APIView):

    parser_classes = (JSONParser, FormParser)
    render_classes = (JSONRenderer, )

    serializer_class = VerifyPasswordResetFormSerializer

    @transaction.atomic
    def post(self, request):

        serializer = self.serializer_class(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        # Find the candidate reset(s)
        pwresets = PasswordReset.objects.filter(
            email=serializer.data['email'],
            reset_date=None,
            message_sent_date__gt=(timezone.now() - PasswordReset.TOKEN_EXPIRY_TIMEDELTA))

        recovery_pwr = None
        for pwr in pwresets:
            if pwr.get_password_reset_token() == serializer.data['token']:
                recovery_pwr = pwr
                break

        if not recovery_pwr:
            # No token
            return Response({'error': 'Token not valid or expired'}, status=403)

        recovery_pwr.update_password(serializer.data['password'])

        return Response({'status': 'New password set'}, status=200)


@api_view(('GET',))
def email_validate(request, validation_token, format=None):
    return comm_channel_validate(CommChannel.EMAIL, request, validation_token, format)


@api_view(('GET',))
def phone_validate(request, validation_token, format=None):
    return comm_channel_validate(CommChannel.PHONE, request, validation_token, format)


def comm_channel_validate(comm_type, request, validation_token, format=None):
    # Check if validation_token is valid, validation_token not yet expired, validation_date has not been set.
    TOKEN_EXPIRATION_IN_DAYS = 10
    try:
        comm_channel = CommChannel.objects.get(comm_type=comm_type, validation_token=validation_token, validation_date__isnull=True, created__gte=timezone.now() - datetime.timedelta(days=TOKEN_EXPIRATION_IN_DAYS))
    except CommChannel.DoesNotExist:
        logger.error('Token %s not exist or already expired' % (validation_token))
        # Redirect to invalid token page
        return redirect('fe:bad-channel-validation')
    else:
        account = comm_channel.account
        if comm_type == CommChannel.EMAIL:
            account.status = AccountStatus.ACTIVE
        elif comm_type == CommChannel.PHONE:
            # any account has the same phone number will have to forfeit to guarantee phone uniqueness
            for acc in Account.objects.filter(phone=comm_channel.comm_endpoint).exclude(status=AccountStatus.CONTACT):
                acc.phone = None
                acc.save()
            # CONSOLIDATE DATA: find all account with same phone and status=CONTACT (account shell created during event invitation), 
            # replace shell account with the current account in core_inappnofitication, core_eventguest
            try:
                shell_account = Account.objects.get(phone=comm_channel.comm_endpoint, status=AccountStatus.CONTACT)
            except Account.DoesNotExist:
                pass
            else:
                for eventguest in EventGuest.objects.filter(guest=shell_account):
                    eventguest.guest = account
                    eventguest.save()

                for ntf in InAppNotification.objects.filter(recipient=shell_account):
                    ntf.recipient = account
                    ntf.save()

                shell_account.delete()  # this can potentially cause relational errors
            
            account.phone = comm_channel.comm_endpoint
        account.save()

        comm_channel.validation_date = timezone.now()
        comm_channel.save()

        # log in user
        account.backend = 'django.contrib.auth.backends.ModelBackend'  # fake this so we don't need to authenticate before login
        login(request, account)
        # Redirect to success validation page
        return redirect('fe:set-profile')


class GoogleApiAuthorization(APIView):
    ''' Show if user has connected his google account, and url to authorize if not.
    Also, input the (one-time use) scope & code parameters get from the returned URL so back-end can save the credentials'''

    serializer_class = GoogleAuthorizationSerializer
    permission_classes = (permissions.IsAuthenticated, )

    CALENDAR_SCOPE = 'https://www.googleapis.com/auth/calendar'  # read & write
    CONTACT_SCOPE = 'https://www.googleapis.com/auth/contacts.readonly'  # read only

    def get_flow(self, scope):
        scope = scope.replace('+', ' ')
        return OAuth2WebServerFlow(client_id=settings.GOOGLE_API_CLIENT_ID,
                                   client_secret=settings.GOOGLE_API_CLIENT_SECRET,
                                   scope=scope,
                                   redirect_uri=settings.GOOGLE_API_REDIRECT_URL,
                                   include_granted_scopes='true',
                                   access_type='offline',
                                   approval_prompt='force')

    def get_authorize_uri(self, scope):
        auth_uri = self.get_flow(scope).step1_get_authorize_url()
        return auth_uri

    def is_connected_with_google_account(self, user, scope):
        ''' Test that the user has connected his google account'''

        storage = Storage(GoogleCredentials, 'account', user, 'credentials')
        credentials = storage.get()

        if credentials is None:
            return False

        if scope == self.CALENDAR_SCOPE:
            try:
                http = credentials.authorize(httplib2.Http())
                service = build('calendar', 'v3', http=http)
                response = service.events().list(calendarId='primary').execute()
            except (HttpError, AccessTokenRefreshError):  # these errors mean this scope is not authorized
                return False
            else:
                return True
        return False

    def get(self, request, format=None):
        data = {'is_connected_with_google_calendar': self.is_connected_with_google_account(request.user, self.CALENDAR_SCOPE),
                # 'google_contact_authorize_uri': self.get_authorize_uri(self.CONTACT_SCOPE),
                'google_calendar_authorize_url': self.get_authorize_uri(self.CALENDAR_SCOPE),

                }
        return Response(data)

    def post(self, request, format=None):
        serializer = GoogleAuthorizationSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=400)

        code = serializer.data['code']
        scope = serializer.data['scope']

        flow = self.get_flow(scope)

        try:
            credentials = flow.step2_exchange(code)
        except FlowExchangeError as e:
            return Response({'error': str(e)})

        storage = Storage(GoogleCredentials, 'account', request.user, 'credentials')
        storage.put(credentials)

        data = {'is_connected_with_google_calendar': self.is_connected_with_google_account(request.user, self.CALENDAR_SCOPE),
                }

        return Response(data)

#EOF
