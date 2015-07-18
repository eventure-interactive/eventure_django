from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# from django.contrib.auth.models import User
from rest_framework.test import APIRequestFactory, APIClient
from core.models import Account, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest, CommChannel
from django.utils import timezone
import datetime
from django.test.utils import override_settings
from django.core import mail
import re


class AccountTests(APITestCase):
    fixtures = ['core_initial_data_2.json']

    def setUp(self):
        # log in
        self.user = Account.objects.get(email='tidushue@gmail.com')
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

    def test_create_account(self):
        # log out of tidushue account
        self.client.logout()
        # create account
        url = reverse('account-list')
        email, password = 'a@mail.com', 'password123'
        data = {
            'email': email,
            'password': password,
        }
        response = self.client.post(url, data)
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['email'], email)

        # Replace user, client with new account
        self.user = Account.objects.get(email=email)
        self.client = APIClient()

        # see if validation email is sent
        validation_email = mail.outbox[0]
        self.assertEqual(validation_email.subject, 'Eventure Email Verification')
        self.assertEqual(validation_email.to[0], email)

        # Get the token
        pattern = re.compile(r'email-validate/(?P<validation_token>[\w|\-]+)/')
        validation_token = pattern.search(validation_email.body).group('validation_token')

        # validate email to activate account
        url = reverse('email-validate', kwargs={'validation_token': validation_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        # try to log in with that account
        # response = self.client.login(username=email, password=password)
        # self.assertTrue(response)

        # user is now automatically logged in
        # update phone
        url = reverse('self-detail')
        phone = '+17144595938'
        response = self.client.put(url, {'name': 'Trigger Happy', 'phone': phone})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Trigger Happy')

        # Get validation_token
        comm_channel = CommChannel.objects.filter(comm_endpoint=phone).latest('created')
        validation_token = comm_channel.validation_token
        # Validate phone
        url = reverse('phone-validate', kwargs={'validation_token': validation_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
    
#EOF
