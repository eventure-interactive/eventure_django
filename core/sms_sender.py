from django.conf import settings
import urllib.parse
import httplib2
import json
from core.models import CommChannel
from celery import shared_task
import logging
logger = logging.getLogger(__name__)


_url = 'https://rest.nexmo.com/sms/json'


def send_sms(to, text):
    params = {"api_key": settings.SMS_API_KEY, "api_secret": settings.SMS_API_SECRET, "from": settings.SMS_FROM, "to": to, "text": text}
    params = urllib.parse.urlencode(params)
    headers = {"Content-type": "application/x-www-form-urlencoded", "Accept": "application/json"}

    h = httplib2.Http()
    resp, content = h.request(_url, "POST", body=params, headers=headers)

    isJson = False
    try:
        charset = 'utf-8'
        contenttype = resp.get('content-type')
        if contenttype:
            for dt in contenttype.split(';'):
                if dt == 'application/json':
                    isJson = True
                if dt.startswith('charset='):
                    charset = dt[8:]
        data = str(content, charset)
    except:
        data = str(content)

    if resp["status"] != '200':
        # raise err.ProblemInSubservice(resp["status"], data)
        logger.error("Problem sending sms status %s data %s" % (resp["status"], data))

    if isJson:
        return json.loads(data)
    else:
        return None


@shared_task
def async_send_validation_phone(commchannel_id):
    ''' Send validation link to phone to confirm ownership '''
    try:
        comm_channel = CommChannel.objects.get(pk=commchannel_id)
    except CommChannel.DoesNotExist:
        raise ValueError('No object with ID %s is found in core_commchannel' % (commchannel_id))
    else:
        validation_token = comm_channel.validation_token
        site_url = 'http://eventure.com/api/'
        link = '%sphone-validate/%s/' % (site_url, validation_token)
        message = 'Follow this link %s to validate your phone. Ignore if you think you receive this by mistake.' % (link)

        result = send_sms(comm_channel.comm_endpoint, message)
        logger.debug(result)
        logger.debug(' MESSAGE: ' + message)

        return result
