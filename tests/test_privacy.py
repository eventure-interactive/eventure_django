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
    fixtures = ['core_initial_data.json']
    def setUp(self):
        # user log in
        self.user = Account.objects.get(phone='+17146032364')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.user2 = Account.objects.get(phone='+17148885070')
        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)


    @override_settings(CELERY_ALWAYS_EAGER=True,)
    def test_event_privacy(self):

        # Create event
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

        
        response = self.client2.get(files_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

        # NEED TO FIX CELERY PROBLEM: daemon's database is not test runner's database
        # time.sleep(30)
        # response = self.client.get(files_url)
        # print(response.data)
        # print(response.status_code)

#EOF
