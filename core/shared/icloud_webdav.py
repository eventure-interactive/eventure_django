from icalendar import Calendar, Event as iEvent
from icalendar import vCalAddress, vText
from .lib import caldav
from core.models import AppleCredentials, EventGuest
import re
import phonenumbers
from urllib import parse
from .lib.caldav.lib.error import AuthorizationError
import logging
logger = logging.getLogger(__name__)


def to_ical_event(ev):
    """
    Convert Eventure Event to ical (CalDAV) string format
    Params: ev: core.models.event
    """
    cal = Calendar()
    cal.add('prodid', '-//Eventure Interactive.//CalDAV Client//EN')
    cal.add('version', '2.0')

    event = iEvent()
    event.add('summary', ev.title)
    event.add('dtstart', ev.start)
    event.add('dtend', ev.end)
    event.add('dtstamp', ev.created)
    event.add('uid', 'EVENTURE-' + str(ev.id))
    event['location'] = vText(ev.location)

    # Add Guests
    for guest in ev.guests.all():
        attendee = vCalAddress('MAILTO:%s' % (guest.email))
        attendee.params['cn'] = vText(guest.name)
        attendee.params['ROLE'] = vText('REQ-PARTICIPANT')
        event.add('attendee', attendee, encode=0)

    cal.add_component(event)

    return cal.to_ical()


def export_to_icloud(ical_event, account, rsvp, apple_credentials):
    """
    Create or Update an event on user's icloud Calendar
    Params: ical_event: event in ical format
            account: core.models.account
            apple_credentials: core.models.AppleCredentials of account
            rsvp: core.models.EventGuest.rsvp RSVP status of account for this event. Remove from calendar if RSVP NO/UNDECIDED
    """

    url = "https://%s:%s@p01-caldav.icloud.com/" % (apple_credentials.credentials.apple_id, apple_credentials.credentials.apple_password)

    client = caldav.DAVClient(url)
    principal = client.principal()

    calendars = principal.calendars()

    # Default to put event in Home calendar, ASSUMING everyone has Home Calendar!
    calendar = next((x for x in calendars if '/calendars/home/' in str(x)), None)
    if calendar is not None:
        event = calendar.add_event(ical_event)

        if rsvp == EventGuest.NO or rsvp == EventGuest.UNDECIDED:
            event.delete()

            logger.info('An icloud calendar event has been deleted for Account ID %d: %s' % (account.id, event))

        logger.info('An icloud calendar event has been created/updated for Account ID %d: %s' % (account.id, event))

        return event
    else:
        logger.error('No Home calendar for Account ID %d' % (account.id))


# FOR CARDDAV

def parse_vcard(vcard):
    '''Simple parser for vcard format string using regex '''
    # Get all things look like phone
    phones = []
    # for match in phonenumbers.PhoneNumberMatcher(vcard, 'US'):
    #     phones.append(match.number)
    phone_pattern = re.compile(r'TEL;(type=(?P<label>\w+);*)*:(?P<field>[+()0-9\xc2\xa0 a-z-]+)', re.I)  # \xc2\xa0 are special space characters
    for match in phone_pattern.finditer(vcard):
        phones.append({'field': match.group('field'), 'label': match.group('label')})

    # Get all things look like email
    emails = []
    email_pattern = re.compile(r'EMAIL;(type=(?P<label>\w+);*)*:(?P<field>[A-Za-z0-9\.\+_-]+@[A-Za-z0-9\._-]+\.[a-zA-Z]+)', re.I)
    for match in email_pattern.finditer(vcard):
        emails.append({'field': match.group('field'), 'label': match.group('label')})

    # Get string after FN:
    fullname = ''
    fullname_pattern = re.compile(r'(?<=FN:)[a-zA-Z 0-9_-]+', re.I)
    fullname_match = fullname_pattern.search(vcard)
    if fullname_match is not None:
        fullname = fullname_match.group(0)

    return {'fullname': fullname, 'phones': phones, 'emailAddresses': emails}


def get_contacts(account):
    """ Get all icloud contacts using App Specific Password
    THIS NEEDS TO MOVE TO FRONT-END
    """
    try:
        apple_credentials = account.apple_credentials
    except AppleCredentials.DoesNotExist:
        logger.info('Account ID %d does not have apple_credentials.' % (account.id))
    else:
        url = "https://%s:%s@contacts.icloud.com" % (apple_credentials.credentials.apple_id, parse.quote(apple_credentials.credentials.apple_password))

        client = caldav.DAVClient(url)
        try:
            principal = client.principal()
        except AuthorizationError as e:
            return {'error': str(e)}

        addressbook = principal.addressbook()

        contacts = addressbook.contacts()

        contact_list = []
        for contact in contacts:
            vcard = contact.extra_init_options['data']
            contact_dict = parse_vcard(vcard)
            contact_list.append(contact_dict)

        return contact_list
