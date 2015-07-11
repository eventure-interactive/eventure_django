from django.core.urlresolvers import reverse
from rest_framework import status
from rest_framework.test import APITestCase

# from django.contrib.auth.models import User
from rest_framework.test import APIClient
from core.models import Account


class FollowTests(APITestCase):
    fixtures = ['core_initial_data_2.json']
    def setUp(self):
        # create new user account
        # self.user = Account.objects.create(phone='+17146032364', name='Henry', password='testing')
        # self.user.save()

        # self.user2 = Account.objects.create(phone='+17148885070', name='Tidus', password='testing')
        # self.user2.save()

        # log in
        self.user = Account.objects.get(email='huy.nguyen@eventure.com')
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

        self.user2 = Account.objects.get(email='tidushue@gmail.com')
        self.client2 = APIClient()
        self.client2.force_authenticate(user=self.user2)

    def test_follow(self):
        # user follows user 2
        url = reverse('following-list', kwargs={'pk': self.user.id})
        data = {
            'followee': reverse('account-detail', kwargs={'pk': self.user2.id}),
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        # user 2 approves
        url = reverse('follower-detail', kwargs={'followee_id': self.user2.id, 'follower_id': self.user.id})
        data = {
            'status': 1
        }
        response = self.client2.put(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        # check that user is on user2's followers
        url = reverse('follower-list', kwargs={'pk': self.user2.id})
        response = self.client2.get(url)
        followers = [f['follower'] for f in response.data['results']]
        self.assertIn('http://testserver' + reverse('follower-detail', kwargs={'followee_id': self.user2.id, 'follower_id': self.user.id}), followers)

        # check that user2 is in user's followings
        url = reverse('following-list', kwargs={'pk': self.user.id})
        response = self.client.get(url)
        followings = [f['followee'] for f in response.data['results']]

        self.assertIn('http://testserver' + reverse('account-detail', kwargs={'pk': self.user2.id}), followings)

# EOF
