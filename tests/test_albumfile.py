from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from core.models import Account


class AlbumFileTests(APITestCase):
    fixtures = ['core_initial_data_2.json']

    def setUp(self):
        # log in
        self.user = Account.objects.get(email='huy.nguyen@eventure.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)
    

    def test_upload_albumfile_fail(self):
        # Get album
        url = reverse('album-list') + '?album_type=5'  # get event albums
        response = self.client.get(url)

        # Get upload url for the first album returned
        files_url = response.data['results'][0]['files']

        # Upload with url, not image
        video_url = '''https://upload.wikimedia.org/wikipedia/commons/3/34/1961-04-13_Tale_Of_Century_-_Eichmann_Tried_For_War_Crimes.ogv'''
        response = self.client.post(files_url, {'source_url': video_url})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['source_url'], ['Url needs to contain an image.'])

        # Upload with file, video
        with open('tests/testvideo.ogv', 'rb') as video:
            response = self.client.post(files_url, {'source_file': video})
        self.assertEqual(response.data['source_file'], ['Uploading videos not yet supported.'])
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        # Upload with file, text file
        with open('tests/test_albumfile.py', 'rb') as text:
            response = self.client.post(files_url, {'source_file': text})
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(response.data['source_file'], ['Source file needs to be an image.'])

        response = self.client.post(files_url, {'source_url': ''})
        self.assertEqual(response.data['non_field_errors'], ['A source_url or a source_file is required.'])

        # Upload with both file & url
        image_url = '''https://upload.wikimedia.org/wikipedia/commons/f/f3/Bocian_biely_%28_Chr%C3%A1nen%C3%A9_vt%C3%A1%C4%8Die_%C3%BAzemie_Poiplie%29.jpg'''
        with open('tests/testimage.jpg', 'rb') as image:
            response = self.client.post(files_url, {'source_file': image, 'source_url': image_url})
        self.assertEqual(response.data['non_field_errors'], ['Provide a source_url or source_file (but not both).'])

    def test_upload_albumfile(self):
        url = reverse('album-list') + '?album_type=5'  # get event albums
        response = self.client.get(url)

        files_url = response.data['results'][0]['files']

        with open('tests/testimage.jpg', 'rb') as image:
            response = self.client.post(files_url, {'source_file': image})
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # test_albumfile_list
        response = self.client.get(files_url)
        self.assertTrue(response.data['count'] > 0)

        # Get a file detail
        file_url = response.data['results'][0]['url']
        response = self.client.get(file_url)
        self.assertTrue(response.data['url'], file_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
