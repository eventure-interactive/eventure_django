from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Account


class AlbumFileTests(APITestCase):
    fixtures = ['core_initial_data.json']

    def setUp(self):
        # log in
        self.user = Account.objects.get(phone='+17146032364')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_albumfile_list(self):
        # Get album
        url = reverse('album-list')
        response = self.client.get(url)

        # Get files
        files_url = response.data['results'][0]['files']
        response = self.client.get(files_url)
        self.assertTrue(response.data['count'] > 0)

        # Get a file detail
        file_url = response.data['results'][0]['url']
        response = self.client.get(file_url)
        self.assertTrue(response.data['url'], file_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
