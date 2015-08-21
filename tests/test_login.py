from rest_framework.test import APITestCase
from rest_framework.test import APIRequestFactory, APIClient
from rest_framework import status
from django.core.urlresolvers import reverse
from django.core import mail
from django.utils import timezone
from core.models import Account, AccountStatus, PasswordReset
from datetime import timedelta
from core import tasks


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
                self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.data)
                for k in errkey:
                    self.assertIn(k, response.data)

        def test_logout(self):

            self.client.force_authenticate(user=self.user)
            response = self.client.delete(self.login_url)
            self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)


class PasswordResetTests(APITestCase):

    def setUp(self):
        self.user = Account.objects.create_user(email="test@eventure.com", phone='18006032364',
                                                password='iforgotit', status=AccountStatus.ACTIVE,
                                                last_login=timezone.now())
        self.client = APIClient()

    def test_reset_step_one(self):
        url = reverse('send-password-reset')
        response = self.client.post(url, {'email': self.user.email})
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)

    def test_reset_sends_email(self):
        url_template = "http://foo.eventure.com/e/finish-reset/{pw_reset_id}/{token}"
        resp = tasks.send_password_reset_email(self.user.email, url_template)
        self.assertTrue(resp)

        self.assertEqual(len(mail.outbox), 1)
        token = self._get_token()
        sent_email = mail.outbox[0]
        self.assertEqual("Eventure Password Reset Request", sent_email.subject)
        self.assertIn(token, sent_email.body)

    def test_reset_validate_token(self):

        pr = PasswordReset(email=self.user.email, account=self.user, message_sent_date=timezone.now())
        pr.save()

        url = reverse("verify-password-reset")
        password = 'mynewpassword'
        resp = self.client.post(url, {'email': self.user.email,
                                      'password': password,
                                      'token': pr.get_password_reset_token()})
        self.assertEqual(resp.status_code, status.HTTP_200_OK, resp.data)
        self.user.refresh_from_db()
        self.assertTrue(self.user.check_password(password))

    def test_cannot_use_stale_token(self):

        sent_dt = timezone.now() - timedelta(days=1, hours=1)
        pr = PasswordReset(email=self.user.email, account=self.user, message_sent_date=sent_dt)

        url = reverse("verify-password-reset")
        password = 'imexpired'
        resp = self.client.post(url, {'email': self.user.email,
                                      'password': password,
                                      'token': pr.get_password_reset_token()})
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(resp.data.get('error', '').startswith('Token not valid'))

    def _get_token(self):
        pwreset = PasswordReset.objects.get(email=self.user.email)
        return pwreset.get_password_reset_token()
