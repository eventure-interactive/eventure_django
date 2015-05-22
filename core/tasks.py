"Module for async celery tasks."

from datetime import datetime
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


###################### STREAM #####################
def async_add_to_stream(stream_type, sender_id, recipient_id, obj_model_class, obj_id):
    addstream = add_to_stream.s(stream_type, sender_id, recipient_id, obj_model_class, obj_id)
    return addstream.delay()

@shared_task(queue=settings.HOST_NAME)
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


@shared_task(queue=settings.HOST_NAME)
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


def store_albumfile_and_thumbnails_s3(albumfile_id):
    "Execute all tasks involved with thubmnailing and storing on S3."

    # This runs the store on the main albumfile, then all the thubmnailing as a celery group,
    # and then the finalize task at the end.

    store_af = store_albumfile_s3.s(albumfile_id)
    thumb_sizes = (size for size, label in Thumbnail.SIZE_CHOICES)
    store_thumbnails = (store_thumbnail_s3.s(albumfile_id, size) for size in thumb_sizes)
    finalize = finalize_albumfile.si(albumfile_id)

    return (store_af | chord(store_thumbnails, finalize)).delay()


@shared_task(queue=settings.HOST_NAME)
def store_albumfile_s3(albumfile_id):
    af = AlbumFile.objects.get(pk=albumfile_id)

    if af.file_type == AlbumFile.VIDEO_TYPE:
        raise NotImplementedError('Videos are unsupported')
    try:
        img = Image.open(af.tmp_filename)
    except IOError:
        af.status = AlbumFile.ERROR
        af.save()
        raise

    img_format = img.format.lower()
    img.close()

    datepart = datetime.utcnow().strftime("%Y/%m/%d")
    fname = uuid.uuid4()
    s3_key = "img/{datepart}/{filename}.{ext}".format(datepart=datepart, filename=fname, ext=img_format)
    url = _do_upload_s3(af.tmp_filename, settings.S3_MEDIA_UPLOAD_BUCKET, s3_key)

    af.file_url = url
    af.save()

    return s3_key


@shared_task(queue=settings.HOST_NAME)
def store_thumbnail_s3(main_s3_key, albumfile_id, size):
    af = AlbumFile.objects.get(pk=albumfile_id)

    try:
        img = Image.open(af.tmp_filename)
    except IOError:
        af.status = AlbumFile.ERROR
        af.save()
        raise

    keypart = main_s3_key.rsplit(".", 1)[0]
    s3_key = "{}_S{}.jpeg".format(keypart, size)

    img.thumbnail((size, size))
    w, h = img.size
    with tempfile.NamedTemporaryFile(suffix='.jpeg') as img_f:
        img.save(img_f, 'JPEG')
        img_f.flush()
        url = _do_upload_s3(img_f.name, settings.S3_MEDIA_UPLOAD_BUCKET, s3_key, reduced_redundancy=True)
        size_bytes = os.path.getsize(img_f.name)
        thumbnail = Thumbnail(
            albumfile=af,
            file_url=url,
            size_type=size,
            width=w,
            height=h,
            size_bytes=size_bytes)

    thumbnail.save()
    return thumbnail.pk


def _do_upload_s3(filepath, bucket_name, s3_key, replace=False, reduced_redundancy=False):
    "Upload a file to s3, and return the url the file was saved at."
    conn = boto.s3.connect_to_region(settings.S3_MEDIA_REGION,
                                     aws_access_key_id=settings.AWS_MEDIA_ACCESS_KEY,
                                     aws_secret_access_key=settings.AWS_MEDIA_SECRET_KEY)

    bucket = conn.get_bucket(bucket_name, validate=False)
    if not replace:
        k = bucket.new_key(s3_key)
    else:
        k = bucket.get_key(s3_key)
    k.set_contents_from_filename(filepath, reduced_redundancy=reduced_redundancy)
    k.set_acl('public-read')
    return k.generate_url(expires_in=0, query_auth=False)


@shared_task(queue=settings.HOST_NAME)
def finalize_albumfile(albumfile_id):
    "Mark the albumfile as acitve and delete any local files."

    af = AlbumFile.objects.get(pk=albumfile_id)

    tmp_filename = af.tmp_filename

    af.tmp_filename = None
    af.tmp_hostname = None
    af.status = AlbumFile.ACTIVE
    af.save()

    os.remove(tmp_filename)
    return af.pk
