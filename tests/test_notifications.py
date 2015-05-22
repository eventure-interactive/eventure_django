from django.core.urlresolvers import reverse, resolve
from rest_framework import status
from rest_framework.test import APITestCase

# from django.contrib.auth.models import User
from rest_framework.test import APIClient
from core.models import Account, AlbumType, Event
from django.utils import timezone
import datetime
from django.test.utils import override_settings
from django.utils.six.moves.urllib.parse import urlparse
from django.contrib.contenttypes.models import ContentType


class FollowTests(APITestCase):
    # to create this fixtures
    # python manage.py dumpdata core > core/fixtures/core_initial_data.json --natural-foreign --indent=4 -e contenttypes -e auth.Permission
    fixtures = ['core_initial_data', ]

    # def create_fixtures(self):
    #     # create new user account
    #     self.user = Account.objects.create(phone='+17146032364', name='Henry', password='testing')
    #     self.user.save()

    #     self.user2 = Account.objects.create(phone='+17148885070', name='Tidus', password='testing')
    #     self.user2.save()

    #     event_album_type = AlbumType.objects.create(id=5, name='DEFAULT_EVENT', description='Default event album', is_deletable=False, is_virtual=False, sort_order=60)
    #     event_album_type.save()

    def setUp(self):
        # self.create_fixtures()
        # log in
        self.user = Account.objects.get(phone='+17146032364')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.user2 = Account.objects.get(phone='+17148885070')
        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)

    def create_event(self):
        url = reverse('event-list')

        now = timezone.now()
        data = {'title': 'Test Event Follow 1',
                'start': (now + datetime.timedelta(seconds=10)).strftime("%Y-%m-%dT%H:%M:%SZ"),
                'end': (now + datetime.timedelta(hours=1)).strftime("%Y-%m-%dT%H:%M:%SZ")}

        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        return response

    @override_settings(CELERY_EAGER_PROPAGATES_EXCEPTIONS=True,
                       CELERY_ALWAYS_EAGER=True,
                       # BROKER_BACKEND='memory'
                       )
    def test_notifications(self):
        # user creates event
        response = self.create_event()
        event_url = response.data['url']
        event_id = int(resolve(urlparse(event_url).path).kwargs['pk'])
        # user invites user2
        url = response.data['guests']
        data = {
            'guest': reverse('account-detail', kwargs={'pk': self.user2.id}),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        # user2 must have event notification
        url = reverse('notification-list')
        response = self.client2.get(url)

        ntf = response.data['results'][0]
        self.assertEqual(ntf['object_id'], event_id)
        self.assertEqual(ntf['content_type'], 'event')
        self.assertEqual(ntf['notification_type'], 1)  # EVENT_INVITE

# EOF
