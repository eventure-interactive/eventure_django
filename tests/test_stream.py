from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
import unittest
from core.models import Account


class StreamTests(APITestCase):
    fixtures = ['core_initial_data_2.json']

    def setUp(self):
        # log in
        self.user = Account.objects.get(email='huy.nguyen@eventure.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    @unittest.skip("Going to strip out stream soon.")
    def test_stream_list(self):
        # Get account
        url = reverse('account-detail', kwargs={'pk': self.user.id})
        response = self.client.get(url)
        # Get stream
        stream_url = response.data['streams']
        response = self.client.get(stream_url)
        # Stream is empty
        self.assertEqual(response.data['count'], 0)

        # user2 follow user
        # user creates event
        # user2's stream gets new item
