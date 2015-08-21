from datetime import datetime, timedelta, date
from rest_framework import status
from rest_framework.test import APITestCase, APIClient
from django.core.urlresolvers import reverse
from django.contrib.contenttypes.models import ContentType
import pytz
from core import models, views
from core.shared.const import choice_types as ct


class TestEventComment(APITestCase):

    fixtures = ['core_accounts']

    def setUp(self):

        # hack to make sure our content_type is correct. Sometimes the ID shifts from the time the module
        # is loaded to the time the test is run (maybe changes as different models are loaded?)
        views.EVENT_CONTENT_TYPE = ContentType.objects.get_for_model(models.Event)

        self.host = models.Account.objects.get(pk=1)        # pk 1 = Huy Nguyen
        self.guest = models.Account.objects.get(pk=2)       # pk 2 = Patrick Lewis

        today = date.today()
        start_dt = datetime(today.year, today.month, today.day, 1, tzinfo=pytz.utc) + timedelta(days=30)
        params = dict(
            title="Event Test for Comments",
            start=start_dt,
            end=start_dt + timedelta(hours=1),
            owner=self.host,
            status=ct.EventStatus.ACTIVE.value,
            privacy=models.Event.PRIVATE,
            timezone="US/Pacific",
        )
        self.event = models.Event.objects.create(**params)
        models.EventGuest.objects.create(guest=self.guest, event=self.event)
        self.event_comment_list_url = reverse('event-comment-list', kwargs={'event_id': self.event.id})

    def test_host_and_guest_can_comment(self):
        "The host and invited guests can comment on an event."

        client = APIClient()

        event_ct = ContentType.objects.get_for_model(models.Event)

        comments = {
            self.host: "I am an awesome host.",
            self.guest: "I am very much looking forward to attending your fine event.",
        }

        count = 0
        for account, message in comments.items():
            client.force_authenticate(user=account)
            response = client.post(self.event_comment_list_url, {'text': message}, format='json')
            self.assertEqual(response.status_code, status.HTTP_201_CREATED)
            self.assertIn('text', response.data)
            self.assertIn('owner', response.data)
            self.assertIn('created', response.data)
            self.assertEqual(response.data['text'], message)
            self.assertEqual(response.data['owner']['name'], account.name)
            self.assertIn('profile_thumbnails', response.data['owner'])

            # it's in the database
            comment = models.Comment.objects.get(object_id=self.event.id, content_type=event_ct, text=message)
            self.assertEqual(comment.content_type.model, 'event')
            self.assertEqual(comment.owner, account)
            self.assertEqual(comment.text, message)

            count += 1
            list_response = client.get(self.event_comment_list_url)
            self.assertEqual(list_response.status_code, status.HTTP_200_OK)
            self.assertEqual(list_response.data['count'], count, (list_response.data, self.event_comment_list_url))

    def test_anonymous_and_uninvited_create_comment(self):
        "Anonymous and non-invited accounts can not comment on an event."

        client = APIClient()
        uninvited = models.Account.objects.get(pk=3)   # pk 3 = Test User

        message = "i hax ur 3v3n7"

        client = APIClient()  # Anonymous

        for _ in range(2):
            response = client.get(self.event_comment_list_url)
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            response = client.post(self.event_comment_list_url, {'text': message}, format='json')
            self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
            client.force_authenticate(user=uninvited)

    def test_edit_comment(self):
        "Comment owner can edit their post (but no one else)."

        comment_url = self._create_comment(self.guest, 'Awwsome')

        # in db?
        comment = models.Comment.objects.get(object_id=self.event.id,
                                             content_type=ContentType.objects.get_for_model(models.Event),
                                             text='Awwsome')
        self.assertEqual(comment.owner, self.guest)

        client = APIClient()
        client.force_authenticate(user=self.guest)
        resp = client.put(comment_url, {'text': 'Awesome'}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK, (comment_url, self.event_comment_list_url))
        self.assertEqual(resp.data['text'], 'Awesome')
        comment.refresh_from_db()
        self.assertEqual(comment.text, "Awesome")

        # Host should not be able to edit (it's not their comment)
        client.force_authenticate(user=self.host)
        resp = client.put(comment_url, {'text': 'How DARE you!'}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        comment.refresh_from_db()
        self.assertEqual(comment.text, "Awesome")

        # Non-guest should not be able to edit
        client.force_authenticate(user=models.Account.objects.get(pk=3))
        resp = client.put(comment_url, {'text': 'I like cheese.'}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        comment.refresh_from_db()
        self.assertEqual(comment.text, "Awesome")

        # Anonymous user should not be able to edit
        client.logout()
        resp = client.put(comment_url, {'text': 'Anon edit'}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
        comment.refresh_from_db()
        self.assertEqual(comment.text, "Awesome")

    def test_delete_comment(self):
        "Comment owner and host can delete a comment (but no one else)."

        # Owner of comment can delete a comment
        comment_url = self._create_comment(self.guest, 'DELETEME')

        client = APIClient()
        client.force_authenticate(user=self.guest)
        resp = client.delete(comment_url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        # check db
        self.assertFalse(models.Comment.objects.filter(object_id=self.event.id).exists())

        # check that host can delete any comment for their event
        comment_url = self._create_comment(self.guest, 'NAUGHTY WORDS & REFERENCES RE: YOUR MOTHER')
        client.force_authenticate(user=self.host)
        resp = client.delete(comment_url)
        self.assertEqual(resp.status_code, status.HTTP_204_NO_CONTENT)

        # check db
        self.assertFalse(models.Comment.objects.filter(object_id=self.event.id).exists())

        # Ensure proper permissions on deletes (can't be deleted by other guests, non-guest accounts, or anonymous)
        text = 'Here is some valuable information'
        comment_url = self._create_comment(self.host, text)

        for user in (self.guest, models.Account.objects.get(pk=3), None):
            # force_authenticate can take a None user
            # https://github.com/tomchristie/django-rest-framework/blob/master/rest_framework/test.py
            client.force_authenticate(user=user)

            resp = client.delete(comment_url)
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
            comment = models.Comment.objects.get(object_id=self.event.id, owner=self.host)
            self.assertEqual(comment.text, text)

    def test_comment_response(self):
        # guest posts a comment
        comment_url = self._create_comment(self.guest, 'So, this is going to be great.')
        client = APIClient()
        client.force_authenticate(user=self.guest)
        resp = client.get(self.event_comment_list_url)
        self.assertEqual(resp.data.get('count'), 1, resp.data)
        response_data = resp.data['results'][0]['responses']
        self.assertIn('url', response_data)
        responses_url = response_data['url']
        self.assertEqual(response_data['count'], 0)

        comment = models.Comment.objects.get(object_id=self.event.id)

        # Host posts a response (could be any guest, nothing special about host)
        client.force_authenticate(user=self.host)
        text = 'Glad you think so!'
        resp = client.post(responses_url, {'text': text}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        resp1_url = resp.data['url']
        resp = client.get(resp1_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data['text'], text)

        # Check the 'responses' url has the right count & content
        resp = client.get(responses_url)
        self.assertEqual(resp.data['count'], 1)
        self.assertEqual(resp.data['results'][0]['url'], resp1_url, resp.data)
        self.assertEqual(resp.data['results'][0]['text'], text, resp.data)

        # Check that the main comment url has the right count for responses to the comment
        resp = client.get(comment_url)
        self.assertEqual(resp.data['responses']['count'], 1)

        # verify the db
        response1 = comment.responses.get()
        self.assertEqual(response1.text, text)
        self.assertEqual(response1.owner, self.host)

        # Test others can't delete/modify
        non_guest = models.Account.objects.get(pk=3)
        for user in (self.guest, non_guest, None):
            client.force_authenticate(user=user)

            # Can't get deleted by others
            resp = client.delete(resp1_url)
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
            response1.refresh_from_db()
            self.assertEqual(response1.text, text)

            # Can't get modified by others
            resp = client.put(resp1_url, {'text': 'BUY rolex knockoff here!'}, format='json')
            self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)
            response1.refresh_from_db()
            self.assertEqual(response1.text, text)

        # Test poster can modify
        client.force_authenticate(user=self.host)
        modified_txt = 'Glad you think so! Please tell others to come.'
        resp = client.put(resp1_url, {'text': modified_txt}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        response1.refresh_from_db()
        self.assertEqual(response1.text, modified_txt)

    def _create_comment(self, user, text):

        client = APIClient()
        client.force_authenticate(user=user)
        resp = client.post(self.event_comment_list_url, {'text': text}, format='json')
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        # Return the local path to the newly created comment
        return resp.data['url'].split('testserver')[-1]
