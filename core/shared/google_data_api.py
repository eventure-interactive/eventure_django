from oauth2client.django_orm import Storage
from core.models import GoogleCredentials, Account
from oauth2client.client import AccessTokenRefreshError
import requests
import httplib2


class Error(Exception):
    pass


class AccountNotExistError(Error):
    pass


class CredentialNotExistError(Error):
    pass


class RequestError(Error):
    pass


class PermissionError(Error):
    pass


class GDataClient(object):
    """
    Call Google Data APIs using pre-existing google credentials.
    Use /api/self/google-connect to get and save credentials.
    Sample usage: Get all Google contacts of account with id=3
        g = GDataClient(account_id=3)
        response = g.get_json_response('get', 'https://www.google.com/m8/feeds/contacts/default/full', {'max-results': 10000})
    """
    account = None
    credentials = None

    def __init__(self, account_id):
        "Create GDataClient connecting to an account_id. This account must have google credentials."
        try:
            self.account = Account.actives.get(pk=account_id)
        except Account.DoesNotExist:
            raise AccountNotExistError("Account ID %s does not exist or not active" % (account_id))
        else:
            storage = Storage(GoogleCredentials, 'account', self.account, 'credentials')
            self.credentials = storage.get()

            if self.credentials is None:
                raise CredentialNotExistError("Account ID %s does not have google credentials yet. Go to /api/self/google-connect to update." % (account_id))

    def get_access_token(self):
        "Returns access_token. Refresh if access_token has already expired."
        if self.credentials.access_token_expired:
            self.credentials.refresh(httplib2.Http())

        return self.credentials.access_token

    def get_json_response(self, method, api_end_point, urlparams={}):
        "Sends request to api_end_point and returns result in JSON format."
        assert method.lower() in ("get", "put", "post", "patch", "delete"), "%s is not a valid request method" % (method.lower())

        urlparams.update({'alt': 'json',
                         'access_token': self.get_access_token(),
                          })
        r = getattr(requests, method.lower())(api_end_point, params=urlparams)

        json_data = r.json()
        if 'error' in json_data:
            error = json_data['error']
            error_message = error['message']
            if error_message == 'Insufficient Permission':
                raise PermissionError(error_message)
            else:
                raise RequestError("Error code [%s] message '%s'" % (error['code'], error['message']))
        else:
            return json_data
