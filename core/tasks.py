"Module for async celery tasks."

from datetime import datetime
import json
import logging
import os
import tempfile
import uuid

import boto.s3
from celery import shared_task, chord
from django.conf import settings
from PIL import Image

from core.models import AlbumFile, Thumbnail, InAppNotification, Stream, Event
from core.email_sender import send
from django.contrib.contenttypes.models import ContentType

logger = logging.getLogger('core.tasks')


###################### STREAM #####################
def async_add_to_stream(stream_type, sender_id, recipient_id, obj_model_class, obj_id):
    addstream = add_to_stream.s(stream_type, sender_id, recipient_id, obj_model_class, obj_id)
    return addstream.delay()

@shared_task
def add_to_stream(stream_type, sender_id, recipient_id, obj_model_class, obj_id):
    content_type = ContentType.objects.get(app_label=AlbumFile._meta.app_label, model=obj_model_class)
    content_object = content_type.get_object_for_this_type(pk=obj_id)

    stream = Stream.objects.create(stream_type=stream_type, sender_id=sender_id, recipient_id=recipient_id, content_object=content_object)


################### NOTIFICATIONS ##################
def send_notifications(notification_type, sender_id, recipient_id, obj_model_class, obj_id):
    "Send out notifications: email, inapp, push, sms"

    inapp_ntf = send_inapp_notification.s(notification_type, sender_id, recipient_id, obj_model_class, obj_id)
    return inapp_ntf.delay()


def send_email(notification_type, to_email, data):
    se = send.s(notification_type, to_email, data)
    return se.delay()


@shared_task
def send_inapp_notification(notification_type, sender_id, recipient_id, obj_model_class, obj_id):
    content_type = ContentType.objects.get(app_label=AlbumFile._meta.app_label, model=obj_model_class)
    content_object = content_type.get_object_for_this_type(pk=obj_id)
    ntf = InAppNotification.objects.create(notification_type=notification_type, sender_id=sender_id, recipient_id=recipient_id, content_object=content_object)
    ntf.save()


############### ALBUMFILE PROCESSING ##############
@shared_task
def add(x, y):
    "Test async function."
    return x + y


@shared_task
def finalize_s3_thumbnails(json_data):
    """Store s3 thubmnail information from AWS lambda into the DB.


    This function isn't actully called from Django, but a message is insereted
    by AWS lambda into the message queue and then executed by celery.
    """

    data = json.loads(json_data)

    logger.info('Got json_data %s', json_data)

    bucket_name = data.get('srcBucket')
    key_name = data.get('srcKey')

    try:
        albumfile = AlbumFile.objects.get(s3_bucket=bucket_name, s3_key=key_name)
    except AlbumFile.DoesNotExist:
        logger.error('AlbumFile not found for bucket: %r key: %r', bucket_name, key_name)
        return

    thumb_results = data.get('thumbnailResults')
    if not thumb_results:
        logger.error('Got no thumbnail results with key: %s, json: %s', key_name, json_data)
        return

    exist_thumb = dict((str(t.size_type), t) for t in albumfile.thumbnails.all())

    logger.info('exist_thumb %s', exist_thumb)

    for size, new_data in thumb_results.items():
        logger.info('Looking for size %r', size)
        thumb = exist_thumb.get(size) or Thumbnail()

        logger.info('Using thumb %r', thumb)

        bucket_name = new_data['Bucket']
        key_name = new_data['Key']

        thumb.file_url = new_data['Url']

        thumb.size_type = size
        thumb.width = new_data.get('Width', 0)
        thumb.height = new_data.get('Height', 0)
        thumb.size_bytes = new_data.get('SizeBytes', 0)
        thumb.albumfile_id = albumfile.id
        thumb.save()

    if albumfile.status == AlbumFile.PROCESSING:
        albumfile.status = AlbumFile.ACTIVE
        albumfile.save()

