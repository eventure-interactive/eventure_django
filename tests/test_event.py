from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APIClient
from core.models import Account, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest
from django.utils import timezone
import datetime
from django.test.utils import override_settings


class EventTests(APITestCase):
    fixtures = ['core_initial_data.json']
    # def create_fixtures(self):
    #     self.user = Account.objects.create(phone='+17146032364', name='Henry', password='testing')
    #     self.user.save()

    #     self.user2 = Account.objects.create(phone='+17148885070', name='Tidus', password='testing')
    #     self.user2.save()

    #     event_album_type = AlbumType.objects.create(id=5, name='DEFAULT_EVENT', description='Default event album', is_deletable=False, is_virtual=False, sort_order=60)
    #     event_album_type.save()

    def setUp(self):
        # log in
        self.user = Account.objects.get(phone='+17146032364')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.user2 = Account.objects.get(phone='+17148885070')
        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)

    def test_create_event_start_date_in_the_future(self):
        '''
        Ensure event createion with start date in the past (compared to current UTC time) will fail
        '''
        url = reverse('event-list')
        data = {'title': 'Test Event 1',
            'start' : "2015-04-07T17:04:00Z",
            'end'   : "2015-04-07T17:04:00Z"}
        response = self.client.post(url, data, format='json')
        
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('Start Date must not be in the past', response.data['start'])

    def test_create_event_end_date_later_than_start_date(self):
        '''
        Ensure if end date is ealier than start date, test will fail
        '''
        url = reverse('event-list')

        now = timezone.now()
        data = {'title': 'Test Event 2',
            'start' : now.strftime("%Y-%m-%dT%H:%M:%SZ"),
            'end'   : (now - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}

        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True,)
    def test_create_event_success_add_guest_find_events(self):
        '''
        Ensure test created successful
        '''
        # Create event
        url = reverse('event-list')

        now = timezone.now()
        data = {'title': 'Test Event 3',
                'start': (now + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end': (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'location': '3420 Bristol Street, Costa Mesa, CA 92626',
                }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        album_url = response.data['albums'][0]
        event_url = response.data['url']

        ''' Invite guest'''
        url = response.data['guests']
        data = {
            'guest': reverse('account-detail', kwargs={'pk': self.user2.id}),
        }
        response = self.client.post(url, data, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ''' Find all events in a radius of 100 miles of a random location '''
        url = reverse('event-list')
        miles = '100'
        vicinity = 'costa mesa'
        url += '?miles=%s&vicinity=%s' % (miles, vicinity)

        response = self.client.get(url)
        found_events = list(filter(lambda ev: ev['url'] == event_url, response.data['results']))
        self.assertTrue(len(found_events) > 0)

        ''' Upload file to event album '''
        response = self.client.get(album_url)
        files_url = response.data['files']

        data = {
            'source_url': '''https://upload.wikimedia.org/wikipedia/commons/8/84/Goiaba_vermelha.jpg'''
        }
        response = self.client.post(files_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        photos = AlbumFile.objects.all()
        self.assertTrue(len(photos) > 0)

        # print(photos[0].status)
        # print(photos[0].tmp_filename)
        response = self.client.get(files_url)
        print(response.data)


# EOF
