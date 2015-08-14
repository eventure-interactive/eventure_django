from __future__ import absolute_import
from datetime import datetime, timedelta
from calendar import monthrange
import time

import pytz

import json
class CalendarService(object):
    """
    The 'Calendar' iCloud service, connects to iCloud and returns events.
    """
    def __init__(self, service_root, session, params):
        self.session = session
        self.params = params
        self._service_root = service_root
        self._calendar_endpoint = '%s/ca' % self._service_root
        self._calendar_refresh_url = '%s/events' % self._calendar_endpoint
        self._calendar_event_detail_url = '%s/eventdetail' % (
            self._calendar_endpoint,
        )

    def get_all_possible_timezones_of_local_machine(self):
        """
        Return all possible timezones in Olson TZ notation
        This has been taken from
        http://stackoverflow.com/questions/7669938
        """
        local_names = []
        if time.daylight:
            local_offset = time.altzone
            localtz = time.tzname[1]
        else:
            local_offset = time.timezone
            localtz = time.tzname[0]

        local_offset = timedelta(seconds=-local_offset)

        for name in pytz.all_timezones:
            timezone = pytz.timezone(name)
            if not hasattr(timezone, '_tzinfos'):
                continue
            for (utcoffset, daylight, tzname), _ in timezone._tzinfos.items():
                if utcoffset == local_offset and tzname == localtz:
                    local_names.append(name)
        return local_names

    def get_system_tz(self):
        """
        Retrieves the system's timezone from a list of possible options.
        Just take the first one
        """
        return self.get_all_possible_timezones_of_local_machine()[0]

    def get_event_detail(self, pguid, guid):
        """
        Fetches a single event's details by specifying a pguid
        (a calendar) and a guid (an event's ID).
        """
        host = self._service_root.split('//')[1].split(':')[0]
        self.session.headers.update({'host': host})
        params = dict(self.params)
        params.update({'lang': 'en-us', 'usertz': self.get_system_tz()})
        url = '%s/%s/%s' % (self._calendar_event_detail_url, pguid, guid)
        req = self.session.get(url, params=params)
        self.response = req.json()
        return self.response['Event'][0]

    def refresh_client(self, from_dt=None, to_dt=None):
        """
        Refreshes the CalendarService endpoint, ensuring that the
        event data is up-to-date. If no 'from_dt' or 'to_dt' datetimes
        have been given, the range becomes this month.
        """
        today = datetime.today()
        first_day, last_day = monthrange(today.year, today.month)
        if not from_dt:
            from_dt = datetime(today.year, today.month, first_day)
        if not to_dt:
            to_dt = datetime(today.year, today.month, last_day)
        host = self._service_root.split('//')[1].split(':')[0]
        self.session.headers.update({'host': host})
        params = dict(self.params)
        params.update({
            'lang': 'en-us',
            'usertz': self.get_system_tz(),
            'startDate': from_dt.strftime('%Y-%m-%d'),
            'endDate': to_dt.strftime('%Y-%m-%d')
        })
        req = self.session.get(self._calendar_refresh_url, params=params)
        self.response = req.json()

    def events(self, from_dt=None, to_dt=None):
        """
        Retrieves events for a given date range, by default, this month.
        """
        self.refresh_client(from_dt, to_dt)
        return self.response['Event']

    '''
    def add_event(self, event):
        """ Create / Update Event on icloud Calendar """
        today = datetime.today()
        first_day, last_day = monthrange(today.year, today.month)
        from_dt = datetime(today.year, today.month, first_day)
        to_dt = datetime(today.year, today.month, last_day)

        host = self._service_root.split('//')[1].split(':')[0]
        self.session.headers.update({'host': host})  # 'p03-calendarws.icloud.com'

        params = dict(self.params)
        params.update({
            'lang': 'en-us',
            'usertz': self.get_system_tz(),
            'startDate': from_dt.strftime('%Y-%m-%d'),
            'endDate': to_dt.strftime('%Y-%m-%d')
        })
        guid = "777309F2-23FB-4677-B82B-980FB0CCB09D"  # event_id
        url = 'https://p03-calendarws.icloud.com/ca/events/work/%s' % guid

        # Update session cookies to have user_id & token
        # self.session.cookies.set(name='X-APPLE-WEBAUTH-USER',value='"v=1:s=1:d=281313898"',domain='.icloud.com', path='/')
        # self.session.cookies.set(name='X-APPLE-WEBAUTH-TOKEN', value='"v=2:t=AQAAAABVw89uo5YaGmFqjeX4ZEdYVTRYWzHNrqw~"', domain='.icloud.com', path='/')
        # Request Payload

        payload = {"Event":{"pGuid":"work","extendedDetailsAreIncluded":True,"title":"E3","location":"","localStartDate":[20150807,2015,8,7,12,0,720],"localEndDate":[20150807,2015,8,7,13,0,660],"startDate":[20150807,2015,8,7,12,0,720],"endDate":[20150807,2015,8,7,13,0,660],"allDay":False,"duration":60,"guid":guid,"tz":"US/Pacific","recurrenceMaster":False,"recurrenceException":False,"icon":0,"hasAttachments":False,"changeRecurring":None}}
        # Send Request
        req = self.session.post(url, params=params, data=json.dumps(payload),)
        self.response = req.json()

        return self.response
    '''
    
