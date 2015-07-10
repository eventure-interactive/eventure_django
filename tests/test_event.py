from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Account, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest
from django.utils import timezone
import datetime
from django.test.utils import override_settings
import time
import json
from core.tasks import finalize_s3_thumbnails
from django.core import mail


class EventTests(APITestCase):
    fixtures = ['core_initial_data_2']

    def setUp(self):
        # log in
        self.user = Account.objects.get(email='huy.nguyen@eventure.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.user2 = Account.objects.get(phone='+17148885070')
        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)

        self.user2.email = 'tidushue@gmail.com'
        self.user2.save()

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
            'start' : (now + datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'end'   : (now - datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['non_field_errors'], ['End Date must be later than Start Date'])

        data = {'title': 'Test Event 2',
            'start' : (now - datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            'end'   : (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['start'], ['Start Date must not be in the past'])

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True, CELERY_ALWAYS_EAGER=True,)
    def test_create_update_event_add_guest(self):
        '''
        Ensure test created successful
        '''
        # Create event
        url = reverse('event-list')

        now = timezone.now()
        event_title = 'Test Event for Create Update Event Add Guest'
        data = {'title': event_title,
                'start': (now + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end': (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'location': '3420 Bristol Street, Costa Mesa, CA 92626',
                }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        album_url = response.data['albums'][0]
        event_url = response.data['url']
        guests_url = response.data['guests']

        ''' Invite guest user2. user2 should have notifications'''
        url = response.data['guests']
        data = {
            'guest': reverse('account-detail', kwargs={'pk': self.user2.id}),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ''' Check user2 has invite email '''
        invite_mail = mail.outbox[0]
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(invite_mail.subject, 'You have been invited to %s' % (event_title))
        self.assertIn(self.user2.email, invite_mail.to)
        # print(invite_mail.body)
        # print(invite_mail.alternatives)


        ''' Check guest list and first guest detail'''
        response = self.client.get(guests_url)
        eventguest_url = response.data['results'][0]['url']
        response = self.client.get(eventguest_url)
        self.assertEqual(response.data['guest'], 'http://testserver' + reverse('account-detail', kwargs={'pk': self.user2.id}))

        ''' Update guest reservation '''
        response = self.client.put(eventguest_url, {'rsvp': 2})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['rsvp'], 2)

        ''' Upload file to event album '''
        response = self.client.get(album_url)
        files_url = response.data['files']

        data = {
            'source_url': '''https://upload.wikimedia.org/wikipedia/commons/thumb/3/38/Shopping_Center_Magna_Plaza_Amsterdam_2014.jpg/1280px-Shopping_Center_Magna_Plaza_Amsterdam_2014.jpg''',
            'name': 'half dome 2',
        }
        response = self.client.post(files_url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        ''' Make sure file is uploaded and thumbnails proccessed. '''
        # NEED TO FIX CELERY PROBLEM: daemon's database is not test runner's database
        # response = self.client.get(files_url)
        # self.assertTrue(response.data['count'] > 0)

        # ALTERNATIVE: assume AWS lambda does it job, just check the celery thumbnail task
        last_af = AlbumFile.objects.latest('created')

        thumbnails_data = self.create_thumbnails_fixtures(last_af.s3_key, last_af.s3_bucket)
        finalize_s3_thumbnails.delay(json.dumps(thumbnails_data))

        ''' Make sure AlbumFile is done processing '''
        last_af = AlbumFile.objects.get(pk=last_af.id) # refresh the albumfile data
        self.assertEqual(last_af.status, AlbumFile.ACTIVE)

        ''' Make sure all thumbnails are saved '''
        self.assertTrue(Thumbnail.objects.filter(albumfile_id=last_af.id).count() == 7)

        ''' Update event '''
        new_title = 'New title'
        new_start = (now + datetime.timedelta(minutes=5)).strftime("%Y-%m-%dT%H:%M:%SZ")

        response = self.client.patch(event_url, {'title': new_title, 'start': new_start})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['title'], new_title)
        self.assertEqual(response.data['start'], new_start)

    def test_find_events(self):
        # Create event
        url = reverse('event-list')

        now = timezone.now()
        data = {'title': 'Event Crazy',
                'start': (now + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end': (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'location': '3420 Bristol Street, Costa Mesa, CA 92626',
                }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event_url = response.data['url']

        ''' Find all events in a radius of 100 miles of a random location '''
        url = reverse('event-list')
        miles = '100'
        vicinity = 'costa mesa'
        url += '?miles=%s&vicinity=%s' % (miles, vicinity)

        response = self.client.get(url)
        found_events = list(filter(lambda ev: ev['url'] == event_url, response.data['results']))
        self.assertTrue(len(found_events) > 0)

        ''' Find events using title '''
        url = reverse('event-list') + "?title=Event Crazy"
        response = self.client.get(url)
        self.assertEqual(response.data['count'], 1)

    def create_thumbnails_fixtures(self, image_key, bucket):
        image_key = image_key.replace(".jpeg", "")
        data = {
            "srcKey": image_key + ".jpeg",
            "srcBucket": bucket,
            'thumbnailResults': {},
        }

        for size in ["48", "100", "144", "205", "320", "610", "960"]:
            thumbnail_data = {
                size: {
                    "Bucket": bucket + "-thumbnail",
                    "Key":  "%s_S%s.jpeg" % (image_key, size),
                    "SizeBytes": 1277,
                    "Width": int(size),
                    "Height": 31,
                    "Url": "https://%s-thumbnail.s3.amazonaws.com/%s_S%s.jpeg" % (bucket, image_key, size)
                }
            }
            data["thumbnailResults"].update(thumbnail_data)

        return data

    def test_add_guest_in_bulk(self):
        self.user3 = Account.objects.get(phone='+16572001110')
        # Create event
        url = reverse('event-list')

        now = timezone.now()
        data = {'title': 'Event Crazy',
                'start': (now + datetime.timedelta(minutes=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end': (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'location': '3420 Bristol Street, Costa Mesa, CA 92626',
                }

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        event_url = response.data['url']
        guests_url = response.data['guests']

        # Invite multiple guests
        data = [{'guest': reverse('account-detail', kwargs={'pk': self.user2.id})},
                {'guest': reverse('account-detail', kwargs={'pk': self.user3.id})}
                ]
        response = self.client.post(guests_url, json.dumps(data), content_type='application/json')

        # assert returned guests are correct
        all_guests = ['http://testserver' + g['guest'] for g in data]
        for guest in response.data[0]:
            self.assertIn(guest['guest'], all_guests)

    def test_anonymous_user_searches_event(self):
        # Get events
        url = reverse('event-list')
        self.anonymous_client = APIClient()
        response = self.anonymous_client.get(url)

        # assert Only PUBLIC events returned
        for event in response.data['results']:
            self.assertEqual(event['privacy'], Event.PUBLIC)
# EOF
