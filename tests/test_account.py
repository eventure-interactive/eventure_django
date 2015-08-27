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

    def test_create_deactivate_account(self):

        validation_email = self._create_and_send_email()

        # Replace user, client with new account
        self.user = Account.objects.get(email='a@mail.com')
        self.client = APIClient()

        # Get the token
        pattern = re.compile(r'email-validate/(?P<validation_token>[\w|\-]+)/')
        validation_token = pattern.search(validation_email.body).group('validation_token')

        # validate email to activate account
        url = reverse('email-validate', kwargs={'validation_token': validation_token})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        redirect = response.get('location')
        self.assertEqual(redirect, 'http://testserver' + reverse('fe:home'))

        # try to log in with that account
        # response = self.client.login(username=email, password=password)
        # self.assertTrue(response)

        # user is now automatically logged in
        # update phone
        url = reverse('self-detail')
        phone = '+17144595938'
        response = self.client.put(url, {'name': 'Trigger Happy', 'new_phone': phone})
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['name'], 'Trigger Happy')

        # Get validation_token
        comm_channel = CommChannel.objects.filter(comm_endpoint=phone).latest('created')
        validation_token = comm_channel.validation_token

        # Validate phone
        phone_validate_url = reverse('phone-validate', kwargs={'validation_token': validation_token})
        response = self.client.get(phone_validate_url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)

        # Deactivate account
        response = self.client.delete(url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertEqual(response.data['successful'], 'Account has been deactivated.')

    def test_creation_tokens(self):

        self._create_and_send_email()
        self.assertEqual(len(mail.outbox), 1)

        # Shouldn't get multiple emails (mini-spam prevention)
        self._create_and_send_email(validate_mail_sent=False)
        self.assertEqual(len(mail.outbox), 1)

        # should fail if we get the wrong token
        url = reverse('email-validate', kwargs={'validation_token': 'aaaabbbb-2222-3333-4444-000011112222'})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_302_FOUND)
        self.assertEqual(response.get('location'), 'http://testserver' + reverse('fe:bad-channel-validation'))

    def _create_and_send_email(self, validate_mail_sent=True):

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
        self.assertIsNotNone(response.data['url'])

        if validate_mail_sent:
            # see if validation email is sent
            validation_email = mail.outbox[0]
            self.assertEqual(validation_email.subject, 'Eventure Email Verification')
            self.assertEqual(validation_email.to[0], email)

            return validation_email

#EOF
