import requests
import json
from .lib import pyicloud
from requests.cookies import RequestsCookieJar
from datetime import datetime
from core.models import AppleCredentials, AppleTokens
from .lib.pyicloud import PyiCloudService
from .lib.pyicloud.services.calendar import monthrange
from .lib.pyicloud.exceptions import PyiCloudFailedLoginException
import re
import logging
logger = logging.getLogger(__name__)


def to_ical_time(date_time):
    "Convert datetime value to icloud datetime list format"
    return [int(x) for x in date_time.strftime('%Y%m%d %Y %m %d %H %M 0').split()]


def to_datetime(ical_time):
    "Convert ical datetime back to datetime value"
    if len(ical_time) >= 6:
        return datetime(ical_time[1], ical_time[2], ical_time[3], ical_time[4], ical_time[5], 0)


def to_ical_event(event):
    """
    Convert core.models.event to event dict in icloud format
    """
    event_dict = {
    "Event":
        {"pGuid": "home", ###
         "extendedDetailsAreIncluded": True,
         "title": event.title,
         "location": event.location or "",
         "localStartDate": to_ical_time(event.start),
         "localEndDate": to_ical_time(event.end),
         "startDate": to_ical_time(event.start),
         "endDate": to_ical_time(event.end),
         "allDay": False,
         "duration": (event.end - event.start).seconds//60,
         "guid": 'EVENTURE-' + str(event.id),
         "tz": event.timezone,
         "recurrenceMaster": False,
         "recurrenceException": False,
         "icon": 0,
         "hasAttachments": False,
         "changeRecurring": None
        }
    }
    return event_dict


def export_to_icloud(ical_event, account):
    """ Create/Update icloud calendar event for account using Apple Tokens
    Params: ical_event: event in icloud format
            account: core.models.account
    """
    try:
        ac = AppleCredentials.objects.get(account=account)
    except AppleCredentials.DoesNotExist:
        logger.debug('Account ID %s does not have apple credentials. No event exported.' % account.id)
    else:
        # Get end date and start date of the month of event start
        event_start = to_datetime(ical_event['Event']['startDate'])
        first_day, last_day = monthrange(event_start.year, event_start.month)
        from_dt = datetime(event_start.year, event_start.month, first_day)
        to_dt = datetime(event_start.year, event_start.month, last_day)

        # URL params api.params
        dsid_pattern = re.compile(r'd=(?P<dsid>[0-9]+)')
        dsid = dsid_pattern.search(ac.credentials.x_apple_webauth_user).group('dsid')
        params = {
            'clientBuildNumber': '15D108',  # faking icloud.com
            'clientId': '21999DC1-E51B-4165-8E27-3A94AD328CF6',
            'clientVersion': '5.1',
            'dsid': dsid,
            'lang': 'en-us',
            'usertz': ical_event['Event']['tz'],
            'startDate': from_dt.strftime('%Y-%m-%d'),
            'endDate': to_dt.strftime('%Y-%m-%d'),
            }

        # Request Payload/body
        payload = ical_event

        # Request Url
        guid = payload['Event']['guid']
        # Default to put event in Home Calendar, ASSUMTION: everyone has Home Calendar!
        pguid = 'home'
        host = 'p36-calendarws.icloud.com'  # any pxx host is fine
        url = '%s/%s/%s' % ('https://' + host + '/ca/events', pguid, guid)

        # Session Request
        session = requests.Session()

        # Session Headers session.headers
        headers = {
            'origin': 'https://www.icloud.com',
            'host': host,
            'Accept': '*/*',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'User-Agent': 'Opera/9.52 (X11; Linux i686; U; en)',
            'referer': 'https://www.icloud.com/'
            }

        # Session Cookies
        session.cookies = RequestsCookieJar()
        session.cookies.set(name='X-APPLE-WEBAUTH-USER', value=ac.credentials.x_apple_webauth_user, domain='.icloud.com', path='/')
        session.cookies.set(name='X-APPLE-WEBAUTH-TOKEN', value=ac.credentials.x_apple_webauth_token, domain='.icloud.com', path='/')

        # POST request
        response = session.post(url, params=params, data=json.dumps(payload), headers=headers)

        # if response.status_code == 421:
        #     raise PyiCloudFailedLoginException('Invalid tokens')

        return response


def to_icloud(event):
    """
    Create or Update an event on owner & guests' icloud Calendar
    Params: event: core.models.event
    """
    # TODO: need to check that event status is not draft
    ical_event = to_ical_event(event)
    # Combine event's owner with event's guests
    accounts = [event.owner] + list(event.guests.all())

    for account in accounts:
        response = export_to_icloud(ical_event, account)
        # Log if error
        if response is not None and response.status_code != 200:
            logger.error(response.json())


def save_apple_credentials(apple_id, apple_password, account):
    """Convert apple_id, apple_password to a set of 2 apple tokens.
    These tokens are later used to authorize requests to icloud
    THIS NEEDS TO MOVE TO FRONT-END
    """
    api = PyiCloudService(apple_id, apple_password)

    tokens = AppleTokens(
        x_apple_webauth_user=api.session.cookies['X-APPLE-WEBAUTH-USER'],
        x_apple_webauth_token=api.session.cookies['X-APPLE-WEBAUTH-TOKEN'],  #TODO: Account with 2 step verification will not have this
        )

    apple_credentials, created = AppleCredentials.objects.update_or_create(account=account, defaults={'credentials': tokens, })
    return apple_credentials


def get_contacts(account):
    """ Get all icloud contacts using Apple Tokens
    THIS NEEDS TO MOVE TO FRONT-END
    """
    try:
        ac = AppleCredentials.objects.get(account=account)
    except AppleCredentials.DoesNotExist:
        logger.debug('Account ID %s does not have apple credentials. No contacts retrieved.' % account.id)
    else:
        url_startup = 'https://p03-contactsws.icloud.com:443/co/startup'
        headers = {'User-Agent': 'Opera/9.52 (X11; Linux i686; U; en)', 'origin': 'https://www.icloud.com', 'Accept-Encoding': 'gzip, deflate', 'Accept': '*/*', 'referer': 'https://www.icloud.com/', 'Connection': 'keep-alive', 'host': 'p03-contactsws.icloud.com'}

        # Session Request
        session = requests.Session()
        session.headers = headers
        # Session Cookies
        session.cookies = RequestsCookieJar()
        session.cookies.set(name='X-APPLE-WEBAUTH-USER', value=ac.credentials.x_apple_webauth_user, domain='.icloud.com', path='/')
        session.cookies.set(name='X-APPLE-WEBAUTH-TOKEN', value=ac.credentials.x_apple_webauth_token, domain='.icloud.com', path='/')

        dsid_pattern = re.compile(r'd=(?P<dsid>[0-9]+)')
        dsid = dsid_pattern.search(ac.credentials.x_apple_webauth_user).group('dsid')

        params_contacts = {'locale': 'en_US', 'clientBuildNumber': '14E45', 'clientId': 'B2C97B52-412E-11E5-847C-685B35BC211C', 'id': '54AAA009701E85B06D14FDF994B5DD423D820244', 'order': 'last,first', 'dsid': dsid, 'clientVersion': '2.1'}

        req = session.get(
            url_startup,
            params=params_contacts,
        )

        if req.status_code == 421:
            raise PyiCloudFailedLoginException('Invalid tokens')

        response = req.json()
        params_refresh = params_contacts
        params_refresh.update({
            'prefToken': req.json()["prefToken"],
            'syncToken': req.json()["syncToken"],
        })

        url_changeset = 'https://p03-contactsws.icloud.com:443/co/changeset'
        session.post(url_changeset, params=params_refresh)
        req = session.get(
            url_startup,
            params=params_contacts
        )
        response = req.json()
        return response['contacts']
