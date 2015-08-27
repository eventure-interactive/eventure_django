import os
from datetime import datetime, timedelta
import tempfile
from six.moves.urllib.parse import unquote
from django.conf import settings
from django.utils.translation import ugettext as _
from PIL import Image
from rest_framework import serializers
from .models import Account, AccountSettings, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest, InAppNotification, Follow,\
    CommChannel, EventPrivacy, ALBUM_TYPE_MAP, Comment, AppleCredentials, AppleTokens
from django.utils import timezone
import pytz
import requests
from .tasks import async_send_notifications
from core.shared.const.choice_types import NotificationTypes, EventStatus
from core.sms_sender import async_send_validation_phone
from core import common
from core.validators import EventGuestValidator
from django.core.validators import RegexValidator
from core.shared import icloud_http
import re
import logging
logger = logging.getLogger(__name__)


class FileFieldAllowEmpty(serializers.FileField):
    "Work-around for fact that normal FileField has trouble with empty values."

    def to_internal_value(self, data):
        if not data and not self.required:
            return data

        return super(FileFieldAllowEmpty, self).to_internal_value(data)


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    profile_albumfile = serializers.HyperlinkedRelatedField(read_only=True, view_name='albumfile-detail')
    email = serializers.CharField(write_only=True)
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Account
        fields = ('url', 'name', 'email', 'password', 'profile_albumfile')
        read_only_fields = ('name',)

    def create(self, validated_data):
        return common.create_account(validated_data, self.context['request'])


def _validate_image_file(imgfile):
    "Bare validation to make sure what was uploaded is a parseable image."

    imgfile.seek(0)

    try:
        img = Image.open(imgfile)
        w, h = img.size
        format_ = img.format
    except IOError:
        raise serializers.ValidationError('Does not appear to be a valid image.')

    imgfile.seek(0)

    return TempImageFileData(width=w, height=h, format=format_, file=imgfile)


class AccountSelfSerializer(serializers.HyperlinkedModelSerializer):
    profile_photo_file = FileFieldAllowEmpty(allow_empty_file=True, required=False)
    profile_albumfile = serializers.HyperlinkedRelatedField(read_only=True, view_name='albumfile-detail')
    new_phone = serializers.CharField(allow_null=True, max_length=40, required=False, validators=[RegexValidator(r'\+?[0-9(). -]')])
    full_size_photo_url = serializers.CharField(source='profile_albumfile.file_url', read_only=True)

    class Meta:
        model = Account
        fields = ('url', 'name', 'email', 'phone', 'profile_photo_file', 'profile_albumfile', 'new_phone', 'full_size_photo_url')
        read_only_fields = ('email', 'phone')

    def validate_profile_photo_file(self, data):

        if not data:
            return data

        if data.content_type.startswith('video/'):
            raise serializers.ValidationError(_("Uploading videos not yet supported."))

        if not (data.content_type.startswith('image/') or data.content_type.startswith('video/')):
            msg = _("Source file needs to be an image.")  # TODO: Or a video
            raise serializers.ValidationError(msg)

        img_data = _validate_image_file(data)
        img_data.original_name = data.name

        self.context['img_data'] = img_data

        return data

    def save_profile_photo(self):
        img_data = self.context.get('img_data')
        profile_album, created = Album.objects.get_or_create(owner=self.context['request'].user,
                                                             album_type_id=ALBUM_TYPE_MAP['DEFAULT_PROFILE'].id,
                                                             defaults={'name': 'Profile Photo Album',
                                                                       'description': 'Default Profile Photo Album'})
        if img_data:
            # create image data
            af = AlbumFile(
                owner=self.context['request'].user,
                name=img_data.original_name.rsplit('.', 1)[0],
                description="Profile photo",
                width=img_data.width,
                height=img_data.height,
                size_bytes=img_data.size_bytes,
                file_type=AlbumFile.PHOTO_TYPE,
                status=AlbumFile.PROCESSING,
                )

            af.upload_s3_photo(img_data.file, img_data.format)
            af.save()
            profile_album.albumfiles.add(af)

            return af

    def update(self, instance, validated_data):
        # Don't save new phone until phone validated (in phone-validate view)
        if validated_data.get('name') and instance.name != validated_data['name']:
            instance.name = validated_data['name']
            instance.save()

        if validated_data.get('new_phone') and instance.phone != validated_data['new_phone']:
            comm_channel = CommChannel.objects.create(account=instance, comm_type=CommChannel.PHONE, comm_endpoint=validated_data['new_phone'])

            async_send_validation_phone(comm_channel.id)

        if validated_data.get('profile_photo_file'):
            profile_af = self.save_profile_photo()
            if profile_af is not None:
                instance.profile_albumfile = profile_af
                instance.save()

        return instance


class MiniAccountProfileSerializer(serializers.HyperlinkedModelSerializer):

    profile_thumbnails = serializers.SerializerMethodField()

    def __init__(self, *args, thubmnail_max=Thumbnail.SIZE_205, **kwargs):
        super().__init__(*args, **kwargs)
        self.thumbnail_max = thubmnail_max

    class Meta:
        model = Account
        fields = ('url', 'name', 'profile_thumbnails')

    def get_profile_thumbnails(self, obj):

        if not obj.profile_albumfile:
            return {}

        thumbs = obj.profile_albumfile.thumbnails.filter(
            size_type__lte=self.thumbnail_max).values('size_type', 'file_url')
        return dict((t['size_type'], t['file_url']) for t in thumbs)


class SettingsProfilePrivacyField(serializers.ChoiceField):

    def to_representation(self, value):
        return value


class AccountSettingsSerializer(serializers.HyperlinkedModelSerializer):

    account = serializers.HyperlinkedIdentityField(read_only=True, view_name='account-detail')
    profile_privacy = SettingsProfilePrivacyField(source='account.profile_privacy', choices=Account.PRIVACY_CHOICES,
                                                  required=False)

    class Meta:
        model = AccountSettings
        fields = ('account', 'email_rsvp_updates', 'email_social_activity', 'email_promotions',
                  'text_rsvp_updates', 'text_social_activity', 'text_promotions',
                  'default_event_privacy', 'profile_privacy')

    def update(self, instance, validated_data):
        normal_fields = set(self.Meta.fields) - set(['profile_privacy', 'account'])

        for field in normal_fields:
            val = validated_data.get(field, getattr(instance, field))
            setattr(instance, field, val)
        instance.save()

        # raise ValueError(validated_data)

        current_privacy = instance.account.profile_privacy
        new_privacy = validated_data.get('account', {}).get('profile_privacy', current_privacy)
        if current_privacy != new_privacy:
            acct = instance.account
            acct.profile_privacy = new_privacy
            acct.save()

        return instance


class ThumbnailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Thumbnail
        fields = ('size_type', 'file_url', 'width', 'height', 'size_bytes')


class AlbumTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AlbumType
        fields = ('id', 'name', 'description')


class TempImageFileData(object):

    def __init__(self, **kw):
        self.file = kw.get('file')
        self.original_name = kw.get('original_name')
        self.width = kw.get('width')
        self.height = kw.get('height')
        self.format = kw.get('format', '')
        self.size_bytes = kw.get('size_bytes')


class AlbumFileSerializer(serializers.HyperlinkedModelSerializer):

    thumbnails = ThumbnailSerializer(many=True, read_only=True)
    source_url = serializers.URLField(write_only=True, required=False, allow_blank=True)
    source_file = FileFieldAllowEmpty(write_only=True, allow_empty_file=True, required=False)

    class Meta:
        model = AlbumFile
        fields = ('url', 'name', 'description', 'file_url', 'width', 'height', 'size_bytes', 'thumbnails',
                  'source_url', 'source_file', 'albums', 'owner')
        read_only_fields = ('width', 'height', 'size_bytes', 'file_url', 'albums', 'owner')

    def validate_source_url(self, data):
        """Validate that the url contains an image or video.

        If valid, the context will contain a new TempFileData object (key='img_data').
        """
        if not data:
            return data

        try:
            resp = requests.get(data, stream=True)
        except requests.RequestException as err:
            raise serializers.ValidationError("Error getting url: %s" % err)

        content_type = resp.headers.get('Content-Type', '')

        if content_type.startswith('video/'):
            raise serializers.ValidationError(_("Uploading videos not yet supported."))

        if not (content_type.startswith('image/') or content_type.startswith('video/')):
            msg = _("Url needs to contain an image.")  # TODO: Or a video
            raise serializers.ValidationError(msg)

        tmp = tempfile.TemporaryFile()

        for chunk in resp.iter_content(65536):  # 64K
            tmp.write(chunk)

        img_data = self._validate_img_file(tmp)
        img_data.original_name = unquote(data.split('/')[-1])
        img_data.size_bytes = resp.headers['content-length']

        self.context['img_data'] = img_data

        return data

    def validate_source_file(self, data):

        if not data:
            return data

        if data.content_type.startswith('video/'):
            raise serializers.ValidationError(_("Uploading videos not yet supported."))

        if not (data.content_type.startswith('image/') or data.content_type.startswith('video/')):
            msg = _("Source file needs to be an image.")  # TODO: Or a video
            raise serializers.ValidationError(msg)

        img_data = self._validate_img_file(data)
        img_data.original_name = data.name

        self.context['img_data'] = img_data

        return data

    # def _get_tmpfile(self):
    #     return tempfile.NamedTemporaryFile(dir=settings.TEMP_ALBUMFILE_DIR, prefix='img', delete=False)

    def _validate_img_file(self, imgfile):
        "Bare validation to make sure what was uploaded is a parseable image."

        imgfile.seek(0)

        try:
            img = Image.open(imgfile)
            w, h = img.size
            format_ = img.format
        except IOError:
            raise serializers.ValidationError('Does not appear to be a valid image.')

        imgfile.seek(0)

        return TempImageFileData(width=w, height=h, format=format_, file=imgfile)

    def validate(self, data):
        "Check that we have source_url or source_file, but not both."
        source_url = data.get('source_url')
        source_file = data.get('source_file')

        if not (source_url or source_file):
            raise serializers.ValidationError(_("A source_url or a source_file is required."))

        if source_url and source_file:
            raise serializers.ValidationError(_("Provide a source_url or source_file (but not both)."))

        return data

    def create(self, validated_data):

        img_data = self.context.get('img_data')
        album = self.context['album']

        if img_data:
            # create image data
            af = AlbumFile(
                owner=self.context['request'].user,
                name=validated_data.get('name') or img_data.original_name.rsplit('.', 1)[0],
                description=validated_data.get('description', ''),
                width=img_data.width,
                height=img_data.height,
                size_bytes=img_data.size_bytes,
                file_type=AlbumFile.PHOTO_TYPE,
                status=AlbumFile.PROCESSING,
                )

            af.upload_s3_photo(img_data.file, img_data.format)
            af.save()
            album.albumfiles.add(af)

            # send out in-app notifications to all guests
            guests = album.event.guests.all()
            self.send_notifications(guests, af)

            return af

    def send_notifications(self, guests, albumfile):
        notification_type = NotificationTypes.ALBUMFILE_UPLOAD.value
        sender = self.context['request'].user
        for guest in guests:
            async_send_notifications(notification_type, sender.id, guest.id, 'albumfile', albumfile.id)


class DateTimeFieldUTC(serializers.DateTimeField):
    "Converts a non-UTC time to UTC."

    def to_internal_value(self, value):
        utc = pytz.utc
        value = super().to_internal_value(value)
        if value.tzinfo.utcoffset(value) != timedelta(0):
            # logger.info('Converting {} to UTC'.format(value.tzinfo))
            value = utc.normalize(value.astimezone(utc))
        return value


class EventSerializer(serializers.HyperlinkedModelSerializer):

    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='account-detail')
    albums = serializers.HyperlinkedRelatedField(many=True, view_name='album-detail', read_only=True)
    guests = serializers.HyperlinkedIdentityField(view_name='eventguest-list')
    comments = serializers.HyperlinkedIdentityField(view_name='event-comment-list', lookup_field='id',
        lookup_url_kwarg='event_id')
    start = DateTimeFieldUTC(default_timezone=pytz.utc)
    end = DateTimeFieldUTC(default_timezone=pytz.utc)
    start_local_time = serializers.SerializerMethodField()
    end_local_time = serializers.SerializerMethodField()
    lat = serializers.FloatField(allow_null=True, required=False)
    lon = serializers.FloatField(allow_null=True, required=False)

    featured_image = FileFieldAllowEmpty(allow_empty_file=True, required=False, write_only=True)
    featured_albumfile = serializers.HyperlinkedRelatedField(read_only=True, view_name='albumfile-detail')

    class Meta:
        model = Event
        fields = ('url', 'title', 'start', 'start_local_time', 'end', 'end_local_time', 'timezone', 'owner', 'guests',
                  'comments', 'albums', 'featured_albumfile', 'location', 'lat', 'lon', 'is_all_day', 'status',
                  'calendar_type', 'privacy', 'featured_image', )

    def validate(self, data):
        ''' End Date must be later than Start Date '''
        if data['start'] >= data['end']:
            raise serializers.ValidationError('End Date must be later than Start Date')
        return data

    def validate_start(self, value):
        ''' Start date must be in future '''
        if value < timezone.now():
            raise serializers.ValidationError('Start Date must not be in the past')
        return value

    def validate_featured_image(self, data):

        if not data:
            return data

        if not data.content_type.startswith('image/'):
            msg = _("Source file needs to be an image.")
            raise serializers.ValidationError(msg)

        img_data = _validate_image_file(data)
        img_data.original_name = data.name

        self.context['featured_img_data'] = img_data

        return data

    def update(self, instance, validated_data):
        self._set_all_day_times(validated_data)
        if self.context.get('featured_img_data'):
            event_af = self.save_featured_image(instance)
            if event_af is not None:
                instance.featured_albumfile = event_af

        instance = super().update(instance, validated_data)
        self.send_notifications(instance)
        return instance

    def create(self, validated_data):
        # self._replace_tz(validated_data)
        self._set_all_day_times(validated_data)

        # Need to save the event so the album has somewhere to attach...
        validated_data.pop('featured_image', None)
        event = super().create(validated_data)

        if self.context.get('featured_img_data'):
            self.save_featured_image(event)
            event.save()

        return event

    def send_notifications(self, event):
        if event.status == EventStatus.DRAFT.value:
            return

        notification_type = NotificationTypes.EVENT_UPDATE.value
        sender = self.context['request'].user
        guests = event.guests.all()
        for guest in guests:
            async_send_notifications(notification_type, sender.id, guest.id, 'event', event.id)

    def get_start_local_time(self, obj):
        return self._localized_dt(obj, obj.start)

    def get_end_local_time(self, obj):
        return self._localized_dt(obj, obj.end)

    def _localized_dt(self, event, date_time):
        if event.is_all_day:
            return None

        tz = pytz.timezone(event.timezone)
        local = tz.normalize(date_time.astimezone(tz))
        return local.isoformat()

    def _set_all_day_times(self, validated_data):
        "Strip off times if the event is an all day event."
        is_all_day = validated_data.get('is_all_day', False)
        validated_data['is_all_day'] = is_all_day

        to_convert = {}
        if is_all_day:
            to_convert['start'] = validated_data['start']
            to_convert['end'] = validated_data['end']

        for key, dt in to_convert.items():
            validated_data[key] = datetime(dt.year, dt.month, dt.day, tzinfo=pytz.utc)

    def save_featured_image(self, event):
        """Save the context 'featured_img data' as an albumfile, and add to the event.

        Saves the Album (if created) and the AlbumFile, but not the event.
        """
        img_data = self.context.get('featured_img_data')

        if img_data:
            event_album, created = Album.objects.get_or_create(
                owner=self.context['request'].user,
                album_type=ALBUM_TYPE_MAP['DEFAULT_EVENT'],
                event=event,
                defaults={'name': '{} Event Album'.format(event.title),
                          'description': 'Default album for the {} event'.format(event.title)})
            # create image data
            af = AlbumFile(
                owner=self.context['request'].user,
                name=img_data.original_name.rsplit('.', 1)[0],
                width=img_data.width,
                height=img_data.height,
                size_bytes=img_data.size_bytes,
                file_type=AlbumFile.PHOTO_TYPE,
                status=AlbumFile.PROCESSING)

            af.upload_s3_photo(img_data.file, img_data.format)
            af.save()
            event_album.albumfiles.add(af)

            event.featured_albumfile = af


class MultiKeyHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    """Create an identity field based on multiple url kwargs and object attributes.

    Expects to receive an 'identity_args' dict with keys of url kwargs (should match the url kwargs)
    and values containing the object property name for the value.
    """

    identity_args = {}

    def get_url(self, obj, view_name, request, format):

        if obj.pk is None:
            return None

        kwargs = dict((url_kw, getattr(obj, prop)) for url_kw, prop in self.identity_args.items())
        return self.reverse(view_name, kwargs=kwargs, request=request, format=format)


class EventGuestHyperlinkedIdentityField(MultiKeyHyperlinkedIdentityField):

    identity_args = {
        'guest_id': 'guest_id',
        'event_id': 'event_id'
    }


class GuestListSerializer(serializers.HyperlinkedModelSerializer):

    url = EventGuestHyperlinkedIdentityField(view_name='eventguest-detail', read_only=True)
    name = serializers.SerializerMethodField()

    class Meta:
        model = EventGuest
        fields = ('url', 'name', 'rsvp')

    def get_name(self, obj):
        return obj.name or obj.guest.name or None


class EventGuestSerializer(serializers.HyperlinkedModelSerializer):
    event = serializers.HyperlinkedRelatedField(read_only=True, view_name='event-detail', )
    # event = serializers.HiddenField(default=None,)
    # guest = serializers.HyperlinkedRelatedField(queryset=Account.objects.all(), view_name='account-detail')
    guest = serializers.CharField(allow_blank=False, trim_whitespace=True,
                                  validators=[EventGuestValidator(Account=Account)])
    url = EventGuestHyperlinkedIdentityField(view_name='eventguest-detail')

    class Meta:
        model = EventGuest
        fields = ('url', 'event', 'guest', 'rsvp')


class EventGuestUpdateSerializer(serializers.HyperlinkedModelSerializer):
    ''' to be used with Event Guest Detail view '''
    guest = serializers.HyperlinkedRelatedField(view_name='account-detail', read_only=True)
    name = serializers.SerializerMethodField()
    event = serializers.HyperlinkedRelatedField(read_only=True, view_name='event-detail')
    url = EventGuestHyperlinkedIdentityField(view_name='eventguest-detail')

    class Meta:
        model = EventGuest
        fields = ('url', 'event', 'guest', 'name', 'rsvp')

    def update(self, instance, validated_data):
        instance.rsvp = validated_data.get('rsvp')
        instance.save()

        self.send_notifications(instance)

        return instance

    def send_notifications(self, eventguest):
        notification_type = NotificationTypes.EVENTGUEST_RSVP.value
        sender = self.context['request'].user
        event = eventguest.event
        recipient = event.owner

        async_send_notifications(notification_type, sender.id, recipient.id, 'eventguest', eventguest.id)  # async

    def get_name(self, obj):
        return obj.name or obj.guest.name or None


class EventCommentHyperlinkedIdentityField(MultiKeyHyperlinkedIdentityField):

    identity_args = {
        'event_id': 'object_id',
        'pk': 'pk',
    }


class EventCommentResponsesHyperlinkedIdentityField(MultiKeyHyperlinkedIdentityField):

    identity_args = {
        'event_id': 'object_id',
        'comment_id': 'pk',
    }


class EventCommentResponseHyperlinkedIdentityField(MultiKeyHyperlinkedIdentityField):

    identity_args = {
        'event_id': 'object_id',
        'comment_id': 'parent_id',
        'pk': 'pk',
    }


class CommentResponsesSummarySerializer(serializers.Serializer):

    # receives a Comment object

    url = EventCommentResponsesHyperlinkedIdentityField(read_only=True, view_name='event-comment-response-list')
    count = serializers.SerializerMethodField()

    def get_count(self, obj):
        return obj.responses.count()


class EventCommentListSerializer(serializers.HyperlinkedModelSerializer):

    url = EventCommentHyperlinkedIdentityField(view_name='event-comment-detail')
    owner = MiniAccountProfileSerializer(read_only=True)
    responses = serializers.SerializerMethodField()

    class Meta:
        fields = ('url', 'owner', 'created', 'text', 'responses')
        model = Comment

    def get_responses(self, obj):
        s = CommentResponsesSummarySerializer(obj, context=self.context)
        return s.data


class EventCommentSerializer(EventCommentListSerializer):

    pass


class EventCommentResponseSerializer(serializers.HyperlinkedModelSerializer):

    url = EventCommentResponseHyperlinkedIdentityField(read_only=True, view_name='event-comment-response-detail')
    owner = MiniAccountProfileSerializer(read_only=True)

    class Meta:
        fields = ('url', 'owner', 'text')
        model = Comment


class AlbumSerializer(serializers.HyperlinkedModelSerializer):

    album_type = AlbumTypeSerializer(read_only=True, default=0)
    files = serializers.HyperlinkedIdentityField(view_name='albumfiles-list')
    event = serializers.HyperlinkedRelatedField(queryset=Event.objects.all(), view_name='event-detail', allow_null=True)
    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='account-detail',
                                                default=serializers.CurrentUserDefault())

    class Meta:
        model = Album
        fields = ('id', 'url', 'name', 'description', 'album_type', 'files', 'event', 'owner')

    def validate_event(self, value):
        ''' ONLY OWNER OF EVENT SHOULD BE ABLE TO CREATE EVENT ALBUM '''
        if value is not None and value.owner != self.context['request'].user:
            raise serializers.ValidationError('Cannot create album for event that you do not own')
        return value


class AlbumUpdateSerializer(AlbumSerializer):
    ''' When updating album, should not allow update event '''
    event = serializers.HyperlinkedRelatedField(read_only=True, view_name='event-detail', allow_null=True)


class InAppNotificationSerializer(serializers.HyperlinkedModelSerializer):
    content_type = serializers.CharField()
    # content_object = NotificationObjectRelatedField(read_only=True)

    class Meta:
        model = InAppNotification
        fields = ('sender', 'recipient', 'notification_type', 'content_type', 'object_id', )


class FollowingSerializer(serializers.HyperlinkedModelSerializer):
    status = serializers.IntegerField(read_only=True)
    follower = serializers.HyperlinkedRelatedField(read_only=True, view_name='account-detail')

    class Meta:
        model = Follow
        fields = ('follower', 'followee', 'status')

    def create(self, validated_data):
        follower = self.context['request'].user
        follow = Follow.objects.create(follower=follower, **validated_data)
        return follow

    def validate(self, data):
        ''' For creation: Unique together (follower, followee). Work-around for unique_together wont work with read-only fields (need value to validate) '''
        if self.instance is None:  # create not update
            follower = self.context['request'].user
            if Follow.objects.filter(follower=follower, followee=data.get('followee')).exists():
                raise serializers.ValidationError('Cannot follow same account more than once')
        return data


class FollowerHyperlinkedIdentityField(MultiKeyHyperlinkedIdentityField):

    identity_args = {
        'follower_id': 'follower_id',
        'followee_id': 'followee_id',
    }


class FollowerSerializer(serializers.HyperlinkedModelSerializer):
    follower = FollowerHyperlinkedIdentityField(view_name='follower-detail')

    class Meta:
        model = Follow
        fields = ('follower', 'status')


class FollowerUpdateSerializer(serializers.HyperlinkedModelSerializer):
    follower = serializers.HyperlinkedRelatedField(read_only=True, view_name='account-detail')

    class Meta:
        model = Follow
        fields = ('follower', 'status',)


class EmailOrPhoneField(serializers.CharField):

    def to_internal_value(self, data):
        data = data.strip()

        if '@' in data:
            data = Account.objects.normalize_email(data)
        else:
            try:
                data = Account.normalize_phone(data)
            except ValueError:
                data = ''

        return data


class LoginFormSerializer(serializers.Serializer):

    login_id = EmailOrPhoneField()
    password = serializers.CharField(style={'input_type': 'password'})


class LoginResponseSerializer(serializers.Serializer):

    account = serializers.URLField()
    logged_in = serializers.BooleanField()


class GoogleAuthorizationSerializer(serializers.Serializer):

    scope = serializers.CharField()
    code = serializers.CharField()


class PasswordResetFormSerializer(serializers.Serializer):

    email = serializers.EmailField()


class VerifyPasswordResetFormSerializer(serializers.Serializer):

    email = serializers.EmailField()
    token = serializers.CharField()
    password = serializers.CharField()

from core.shared.lib.pyicloud.exceptions import PyiCloudFailedLoginException
from core.shared.lib.pyicloud import PyiCloudService

class AppleCredentialsSerializer(serializers.ModelSerializer):
    apple_id = serializers.CharField(source='credentials.apple_id')
    apple_password = serializers.CharField(source='credentials.apple_password')

    x_apple_webauth_user = serializers.CharField(source='credentials.x_apple_webauth_user', read_only=True)
    x_apple_webauth_token = serializers.CharField(source='credentials.x_apple_webauth_token', read_only=True)

    class Meta:
        model = AppleCredentials
        fields = ('apple_id', 'apple_password', 'x_apple_webauth_user', 'x_apple_webauth_token')

    def save(self, **kwargs):
        # Subtitude for both create(), update()
        validated_data = dict(
            list(self.validated_data.items()) +
            list(kwargs.items())
        )
        return self.save_apple_credentials(**validated_data)

    def save_apple_credentials(self, credentials, account):
        """Convert apple_id, apple_password to a set of 2 apple tokens.
        These tokens are later used to authorize requests to icloud
        THIS NEEDS TO MOVE TO FRONT-END
        """
        apple_id = credentials['apple_id']
        apple_password = credentials['apple_password']
        app_specific_password_pattern = re.compile(r'^[a-z]{4}-[a-z]{4}-[a-z]{4}-[a-z]{4}$')

        tokens = None
        # If password provided is an app specific password
        if app_specific_password_pattern.match(apple_password) is not None:
            tokens = AppleTokens(
                apple_id=apple_id,
                apple_password=apple_password
                )
        else:
            api = PyiCloudService(apple_id, apple_password)
            try:
                tokens = AppleTokens(
                    apple_id=apple_id,
                    x_apple_webauth_user=api.session.cookies['X-APPLE-WEBAUTH-USER'],
                    x_apple_webauth_token=api.session.cookies['X-APPLE-WEBAUTH-TOKEN'],
                    )
            except KeyError as e:  # No token in response cookies means this account has 2 step verification
                raise PyiCloudFailedLoginException('Your account has 2-step verification. Need to provide app-specific password')

        apple_credentials, created = AppleCredentials.objects.update_or_create(account=account, defaults={'credentials': tokens, })
        return apple_credentials
