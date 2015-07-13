from datetime import datetime
from django.conf import settings
import requests
from core.models import CommChannel
from celery import shared_task
import logging
logger = logging.getLogger(__name__)


twillio_url = "https://api.twilio.com/2010-04-01/Accounts/{api_key}/Messages.json".format(api_key=settings.SMS_API_KEY)


class SMSSendException(Exception):
    pass


def send_sms(to, text):
    # Short circuit test case numbers; do not actually send SMS to these numbers
    if settings.IN_TEST_MODE:
        logger.info('TESTING: Got SMS to:{} text:{}'.format(to, text))
        return _test_sms_response(to, text)

    post_body = {
        "To": to,
        "From": settings.SMS_FROM,
        "Body": text,
    }

    resp = requests.post(twillio_url, data=post_body, auth=(settings.SMS_API_KEY, settings.SMS_API_SECRET))

    if resp.status_code != requests.codes.created:
        msg = "Problem with request to phone number, code: {}, text: {}".format(resp.status_code, resp.text)
        logger.error(msg)
        raise SMSSendException(msg)

    data = resp.json()
    if data.get('error_code') is not None:
        msg = "Got an error sending SMS, response: {}".format(resp.text)
        logger.error(msg)
        raise SMSSendException(msg)

    logger.info('Got twillo response: {}'.format(resp.text))

    return data


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


def _test_sms_response(to, text):
    sid = "SMb01f0c63c6a945e384ac4d03994ed4d1"
    datestamp = datetime.utcnow().strftime("%a, %d %b %Y %H:%M:%S +0000")

    return {
        'body': text,
        'date_created': datestamp,
        'date_updated': datestamp,
        'date_sent': None,
        'num_segments': '1',
        'direction': 'outbound-api',
        'price': None,
        'uri': '/2010-04-01/Accounts/{}/Messages/{}.json'.format(settings.SMS_API_KEY, sid),
        'sid': sid,
        'error_code': None,
        'subresource_uris': {
            'media': '/2010-04-01/Accounts/{}/Messages/{}/Media.json'.format(settings.SMS_API_KEY, sid)},
        'to': to,
        'price_unit': 'USD',
        'from': settings.SMS_FROM,
        'status': 'queued',
        'num_media': '0',
        'account_sid': settings.SMS_API_KEY,
        'api_version': '2010-04-01',
        'error_message': None
    }
