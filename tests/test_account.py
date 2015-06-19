from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APIClient
from core.models import Account, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest
from django.utils import timezone
import datetime
from django.test.utils import override_settings


class AccountTests(APITestCase):
    fixtures = ['core_initial_data.json']

    def setUp(self):
        # log in
        self.user = Account.objects.get(phone='+17146032364')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_account_list(self):
        url = reverse('account-list')
        response = self.client.get(url)

        self.assertTrue(response.data['count'] > 0)

    def test_account_detail(self):
        url = reverse('account-detail', kwargs={'pk': self.user.id})
        response = self.client.get(url)

        self.assertEqual('http://testserver' + url, response.data['url'])

    def test_account_self_detail(self):
        url = reverse('self-detail')
        response = self.client.get(url)

        account_detail_url = reverse('account-detail', kwargs={'pk': self.user.id})
        self.assertEqual('http://testserver' + account_detail_url, response.data['url'])
#EOF
