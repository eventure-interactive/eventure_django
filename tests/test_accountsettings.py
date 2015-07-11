from pprint import pformat
from django.core.urlresolvers import reverse
from django.test import TestCase
from rest_framework import status
from rest_framework.test import APIRequestFactory, APIClient, APITestCase

from core.models import Account, AccountSettings, AccountStatus, EventPrivacy


class AccountSettingsModelTests(TestCase):
    "AccountSettings model test cases."

    def test_account_settings_auto(self):
        "Creating an account automatically creates account settings."

        acct = Account.objects.create_user(phone="+18005551212", password="secret", email="test@example.com",
                                           name="Testy McTesterson")
        # Already saved, can check id
        self.assertIsNotNone(acct.id)

        settings = acct.accountsettings
        self.assertEqual(acct.id, settings.account_id)


class AccountSettingsAPITests(APITestCase):

    def setUp(self):
        # log in
        self.user = Account.objects.create_user(phone="+18005551212", password="secret", email="test@example.com",
                                                name="Testy McTesterson", status=AccountStatus.ACTIVE)
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def testAccessTypes(self):
        "AccountSettings should only allow PUT and GET (not DELETE or POST)."
        url = reverse('self-settings')

        # GET OK
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # POST NOT ALLOWED
        response = self.client.post(url, {'email_promotions': False})
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data)

        # PUT OK
        response = self.client.put(url, {'email_promotions': False})
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)

        # DELETE NOT ALLOWED
        response = self.client.delete(url, format='json')
        self.assertEqual(response.status_code, status.HTTP_405_METHOD_NOT_ALLOWED, response.data)

    def testSaveAccountSettings(self):
        url = reverse('self-settings')

        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        expect = response.data

        test_params = (
            {'email_rsvp_updates': False},
            {'email_rsvp_updates': True},
            {'email_social_activity': False},
            {'email_promotions': False},
            {'text_rsvp_updates': False},
            {'text_rsvp_updates': True},
            {'text_social_activity': True},
            {'text_promotions': True},
            {'default_event_privacy': EventPrivacy.PRIVATE},
            {'default_event_privacy': EventPrivacy.PUBLIC},
            {'profile_privacy': Account.PRIVATE},
            {'profile_privacy': Account.PUBLIC},
            {'email_rsvp_updates': False, 'email_social_activity': False,
             'profile_privacy': Account.PRIVATE},
        )

        for params in test_params:
            expect.update(params)
            response = self.client.put(url, params)

            self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
            self.assertEqual(expect, response.data,
                             "\nExpect: \n{}\nResponse: \n{}\nparams: {}".format(pformat(expect),
                                                                                 pformat(response.data),
                                                                                 pformat(params)))
