from rest_framework.test import APIRequestFactory, APIClient
from core.models import Account, AccountSettings
from django.test import TestCase


class AccountSettingsModelTests(TestCase):

    def setUp(self):
        pass

    def test_account_settings_auto(self):
        "Creating an account automatically creates account settings."

        acct = Account.objects.create_user(phone="+18005551212", password="secret", email="test@example.com",
                                           name="Testy McTesterson")
        # Already saved, can check id
        self.assertIsNotNone(acct.id)

        settings = acct.accountsettings
        self.assertEqual(acct.id, settings.account_id)
