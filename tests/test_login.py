from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework import status
from django.core.urlresolvers import reverse
from core.models import Account, AccountStatus


class LoginTests(APITestCase):

        def setUp(self):
            self.password = 'i-am-$ecret'
            self.user = Account.objects.create_user(email="test@eventure.com", phone='18006032364',
                                                    password=self.password, status=AccountStatus.ACTIVE)
            self.client = APIClient()
            self.login_url = reverse('login')

        def test_login_email(self):
            "User can login using email."

            tests = (
                dict(login_id="test@eventure.com", password=self.password),
                dict(login_id='test@EVENTURE.com', password=self.password)
            )

            for t in tests:
                response = self.client.post(self.login_url, t)
                self.assertEqual(response.status_code, status.HTTP_200_OK,
                                 "test: {} response: {}".format(t, response.data))
                self.assertTrue(response.data.get('logged_in'))

        def test_login_phone(self):
            "User can login via phone."

            tests = (
                dict(login_id='8006032364', password=self.password),
                dict(login_id='18006032364', password=self.password),
                dict(login_id='+18006032364', password=self.password)
            )

            for t in tests:
                response = self.client.post(self.login_url, t)
                self.assertEqual(response.status_code, status.HTTP_200_OK, response.data)
                self.assertTrue(response.data.get('logged_in'))

        def test_login_fails(self):
            "Login fails with wrong credentials."

            tests = (
                dict(login_id='18006032364', password='dontknowit'),
                dict(login_id='1800603', password=self.password),
                dict(login_id='test@eventure.com', password="foolish"),
            )

            for t in tests:
                response = self.client.post(self.login_url, t)
                self.assertEqual(response.status_code, 422, response.data)
                self.assertIn('authentication_error', response.data)

        def test_required_fields(self):
            "Login must receive both username and password."

            tests = (
                (dict(login_id='18006032364', password=''), ['password']),
                (dict(login_id='', password=self.password), ['login_id']),
                (dict(login_id='', password=''), ['password', 'login_id']),
            )

            for t, errkey in tests:
                response = self.client.post(self.login_url, t)
                self.assertEqual(response.status_code, 400, response.data)
                for k in errkey:
                    self.assertIn(k, response.data)

        def test_logout(self):

            self.client.force_authenticate(user=self.user)
            response = self.client.delete(self.login_url)
            self.assertEqual(response.status_code, 204)
