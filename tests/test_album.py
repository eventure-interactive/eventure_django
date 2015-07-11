from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Account


class AlbumTests(APITestCase):
    fixtures = ['core_initial_data_2.json']

    def setUp(self):
        # log in
        self.user = Account.objects.get(email='huy.nguyen@eventure.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_album_list(self):
        url = reverse('album-list')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_custom_album_create_delete(self):
        # Create custom album
        url = reverse('album-list')
        response = self.client.post(url, {'name': 'My custom album', 'description': 'My description', 'event': ''})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # Now delete album
        url = response.data['url']
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)

    def test_event_album_create(self):
        url = reverse('event-list')
        response = self.client.get(url)
        event_url = response.data['results'][0]['url']

        url = reverse('album-list')
        response = self.client.post(url, {'name': 'My event album', 'description': 'My event description', 'event': event_url})
        self.assertEqual(response.data['event'], event_url)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
