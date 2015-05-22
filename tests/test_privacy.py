from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# from django.contrib.auth.models import User
from rest_framework.authtoken.models import Token
from rest_framework.test import APIRequestFactory, APIClient
from core.models import Account, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest
from core.views import AlbumList
from django.utils import timezone
import datetime

from django.contrib.gis.geos import Point
from django.contrib.gis.measure import D
from geopy.geocoders import GoogleV3
import time
from django.test.utils import override_settings


class PrivacyTests(APITestCase):
    """
    Permission Rules:
    + Event: 
        = Public: all can read, only owner can write
        = Private: only owner or guests can read/write
    + EventGuest: inherit from its Event
    + Album: 
        = Event Album: inherit from its Event, guest, owner can post media
        = Non Event Album: only owner can read/write/create
    + AlbumFile: inherit from its Album, 
    """
    def setUp(self):
        # create new user account
        self.user = Account.objects.create(phone='+17146032364', name='Henry', password='testing')
        self.user.save()

        self.user2 = Account.objects.create(phone='+17148885070', name='Tidus', password='testing')
        self.user2.save()

        self._add_required_data()
        # user log in
        self.user = Account.objects.get(phone='+17146032364')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.user2 = Account.objects.get(phone='+17148885070')
        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)

    def _add_required_data(self):
        ''' Some operations need a certain data '''
        # Event creation will create default Album which needs AlbumType DEFAULT_EVENT
        event_album_type = AlbumType.objects.create(id=5, name='DEFAULT_EVENT', description='Default event album', is_deletable=False, is_virtual=False, sort_order=60)
        event_album_type.save()

    @override_settings(CELERY_ALWAYS_EAGER=True,)
    def testEventPrivacy(self):

        ''' Create event '''
        url = reverse('event-list')

        now = timezone.now()
        data = {'title': 'Private Test Event',
            'start' : (now + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'end'   : (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'location': '3420 Bristol Street, Costa Mesa, CA 92626',
            'privacy': 2, # PRIVATE
            }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        album_url = response.data['albums'][0]
        event_url = response.data['url']

        ''' Upload file to event album '''
        response = self.client.get(album_url)
        files_url = response.data['files']
    
        data = {
            'source_url': '''https://upload.wikimedia.org/wikipedia/commons/8/84/Goiaba_vermelha.jpg'''
        }
        response = self.client.post(files_url, data, format='json')
        file_url = response.data['url']

        # print(file_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ''' User2 cannot access event, album, albumfile since its private '''
        
        response = self.client2.get(event_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        response = self.client2.get(album_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # NEED TO FIX UPLOAD FILE PROBLEM
        # time.sleep(30)
        response = self.client2.get(file_url)
        print(response.data)
        # self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

#EOF
