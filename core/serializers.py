import os
import tempfile
from six.moves.urllib.parse import unquote
from django.conf import settings
from django.utils.translation import ugettext as _
from PIL import Image
from rest_framework import serializers
from .models import Account, AccountSettings, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest, InAppNotification, Follow,\
    Stream, CommChannel, EventPrivacy
from django.utils import timezone
import requests
from .tasks import async_send_notifications, async_add_to_stream
from core.shared.const.NotificationTypes import NotificationTypes
from core.sms_sender import async_send_validation_phone
from core import common
from django.core.validators import RegexValidator
import logging
logger = logging.getLogger(__name__)


class FileFieldAllowEmpty(serializers.FileField):
    "Work-around for fact that normal FileField has trouble with empty values."

    def to_internal_value(self, data):
        if not data and not self.required:
            return data

        return super(FileFieldAllowEmpty, self).to_internal_value(data)


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    followers = serializers.HyperlinkedIdentityField(read_only=True, view_name='follower-list')
    followings = serializers.HyperlinkedIdentityField(read_only=True, view_name='following-list')
    streams = serializers.HyperlinkedIdentityField(read_only=True, view_name='stream-list')
    profile_albumfile = serializers.HyperlinkedRelatedField(read_only=True, view_name='albumfile-detail')
    password = serializers.CharField(write_only=True, style={'input_type': 'password'})

    class Meta:
        model = Account
        fields = ('url', 'email', 'profile_albumfile', 'followers', 'followings', 'streams', 'password')

    def create(self, validated_data):
        return common.create_account(validated_data, self.context['request'])


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

        img_data = self._validate_img_file(data)
        img_data.original_name = data.name

        self.context['img_data'] = img_data

        return data

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

    def save_profile_photo(self):
        img_data = self.context.get('img_data')
        profile_album, created = Album.objects.get_or_create(owner=self.context['request'].user, album_type_id=4, defaults={'name': 'Profile Photo Album', 'description': 'Default Profile Photo Album'})

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


# def get_default_event_privacy(account):
#     default_event_privacy = Event.PUBLIC
#     try:
#         account_settings = AccountSettings.objects.get(account=account)
#     except AccountSettings.DoesNotExist:
#         pass
#     else:
#         default_event_privacy = account_settings.default_event_privacy
#     return default_event_privacy


class EventSerializer(serializers.HyperlinkedModelSerializer):

    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='account-detail')
    albums = serializers.HyperlinkedRelatedField(many=True, view_name='album-detail', read_only=True)
    # guests = serializers.HyperlinkedRelatedField(many=True, view_name='account-detail', read_only=True)
    guests = serializers.HyperlinkedIdentityField(view_name='eventguest-list')
    lat = serializers.FloatField(allow_null=True, read_only=True)
    lon = serializers.FloatField(allow_null=True, read_only=True)
    # privacy = serializers.ChoiceField(choices=EventPrivacy.PRIVACY_CHOICES, required=False, default=get_default_event_privacy(serializers.CurrentUserDefault()))

    class Meta:
        model = Event
        fields = ('url', 'title', 'start', 'end', 'owner', 'guests', 'albums', 'location', 'lat', 'lon', 'privacy')

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

    def update(self, instance, validated_data):
        instance = super(serializers.HyperlinkedModelSerializer, self).update(instance, validated_data)

        self.send_notifications(instance)
        return instance

    def create(self, validated_data):
        event = super().create(validated_data)
        self.add_to_stream(event)
        return event

    def add_to_stream(self, event):
        sender = Account.objects.get(pk=self.context['request'].user.id)
        followers = sender.followers.filter(status=Follow.APPROVED)
        for follow in followers:
            async_add_to_stream(Stream.EVENT_CREATE, sender.id, follow.follower.id, 'event', event.id)

    def send_notifications(self, event):
        notification_type = NotificationTypes.EVENT_UPDATE.value
        sender = self.context['request'].user
        guests = event.guests.all()
        for guest in guests:
            async_send_notifications(notification_type, sender.id, guest.id, 'event', event.id)


class EventGuestHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):

    def get_url(self, obj, view_name, request, format):
        """
        Override since default implementation does not allow for multiple lookup_fields
        """
        if obj.pk is None:
            return None

        return self.reverse(view_name,
            kwargs={
                'event_id': obj.event_id,
                'guest_id': obj.guest_id
            },
            request=request,
            format=format
        )


class EventGuestSerializer(serializers.HyperlinkedModelSerializer):
    event = serializers.HyperlinkedRelatedField(read_only=True, view_name='event-detail', )
    # event = serializers.HiddenField(default=None,)
    guest = serializers.HyperlinkedRelatedField(queryset=Account.objects.all(), view_name='account-detail')
    url = EventGuestHyperlinkedIdentityField(view_name='eventguest-detail')

    class Meta:
        model = EventGuest
        fields = ('url', 'event', 'guest', 'rsvp')

    def create(self, validated_data):
        event = self.context['event']
        if event:
            guest = EventGuest.objects.create(event=event, **validated_data)
            if guest:
                self.send_notifications(guest.guest_id)
                return guest

    def validate(self, data):
        ''' For creation: Unique together (event, guest). Work-around for unique_together wont work with read-only fields (need value to validate) '''
        if self.instance is None:  # create not update
            event = self.context.get('event')
            guest = data.get('guest')  # or self.instance.guest
            if EventGuest.objects.filter(event=event, guest=guest).exists():
                raise serializers.ValidationError('Cannot add same guest to event more than once')
        return data

    def send_notifications(self, guest_id):
        notification_type = NotificationTypes.EVENT_INVITE.value
        sender = self.context['request'].user
        event = self.context['event']

        async_send_notifications(notification_type, sender.id, guest_id, 'event', event.id)  # async


class EventGuestUpdateSerializer(EventGuestSerializer):
    ''' to be used with Event Guest Detail view '''
    guest = serializers.HyperlinkedRelatedField(view_name='account-detail', read_only=True)

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


class AlbumSerializer(serializers.HyperlinkedModelSerializer):

    album_type = AlbumTypeSerializer(read_only=True, default=0)
    files = serializers.HyperlinkedIdentityField(view_name='albumfiles-list')
    event = serializers.HyperlinkedRelatedField(queryset=Event.objects.all(), view_name='event-detail', allow_null=True,)
    # owner = serializers.HiddenField(default=serializers.CurrentUserDefault())
    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='account-detail', default=serializers.CurrentUserDefault())

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

# unused
# class NotificationObjectRelatedField(serializers.RelatedField):
#     def to_representation(self, value):
#         if isinstance(value, Event):
#             serializer = EventSerializer(value, context={'request': self.context['request']})
#         elif isinstance(value, EventGuest):
#             serializer = EventGuestSerializer(value, context={'request': self.context['request']})
#         elif isinstance(value, AlbumFile):
#             serializer = AlbumFileSerializer(value, context={'request': self.context['request']})
#         else:
#             raise Exception('Unexpected type of notification object')

#         return serializer.data


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


class FollowerHyperlinkedIdentityField(serializers.HyperlinkedIdentityField):
    def get_url(self, obj, view_name, request, format):
        if obj.pk is None:
            return None

        return self.reverse(view_name,
            kwargs={
                'follower_id': obj.follower_id,
                'followee_id': obj.followee_id
            },
            request=request,
            format=format
        )


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

"""
class ConnectionSerializer(serializers.HyperlinkedModelSerializer):
    connection = serializers.HyperlinkedRelatedField(source='followee', queryset=Account.objects.filter(status=Account.ACTIVE), view_name='account-detail')
    connection_status = serializers.SerializerMethodField()

    class Meta:
        model = Follow
        fields = ('connection', 'connection_status', )

    def get_connection_status(self, obj):
        try:
            reverse = Follow.objects.get(follower=obj.followee, followee=obj.follower)
        except Follow.DoesNotExist:
            # reverse = Follow(follower=obj.followee, followee=obj.follower, status=Follow.PENDING)
            pass

        if obj.status == Follow.APPROVED and reverse.status == Follow.APPROVED:
            return 'connected'
        # elif Follow.UNAPPROVED in (obj.status, reverse.status):
        #     return 'denied' 
        # elif obj.status == Follow.APPROVED and reverse.status == Follow.PENDING:
        #     return 'pending approval from other party'
        # elif reverse.status == Follow.APPROVED and obj.status == Follow.PENDING:
        #     return 'pending approval from you'
        # elif obj.status == Follow.PENDING and reverse.status == Follow.PENDING:
        #     return 'pending approval from both parties'
        else:
            return '%d %s %d, %d %s %d' % (obj.follower_id, obj.status, obj.followee_id, reverse.follower_id, reverse.status, reverse.followee_id)

    def create(self, validated_data):
        ''' Create two way following with status PENDING '''
        follower = self.context['request'].user
        follow, created = Follow.objects.update_or_create(follower=follower, followee=validated_data.get('followee'), defaults={'status': Follow.PENDING})
        reverse, created = Follow.objects.update_or_create(followee=follower, follower=validated_data.get('followee'), defaults={'status': Follow.PENDING})
        return follow


class ConnectionUpdateSerializer(serializers.HyperlinkedModelSerializer):
    connection = serializers.HyperlinkedRelatedField(source='follower', read_only=True, view_name='account-detail')

    class Meta:
        model = Follow
        fields = ('connection', 'status',)

    def update(self, instance, data):
        instance = super().update(instance, data)
        if data['status'] in (Follow.APPROVED, Follow.UNAPPROVED) and self.context['request'].user == instance.follower:
            Follow.objects.update_or_create(follower=instance.followee, followee=instance.follower, defaults={'status': data['status']})
        return instance
"""


class StreamSerializer(serializers.ModelSerializer):
    content_type = serializers.CharField()

    class Meta:
        model = Stream
        fields = ('stream_type', 'data', 'content_type', 'object_id')


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

