import os
import tempfile
from six.moves.urllib.parse import unquote
from django.conf import settings
from django.utils.translation import ugettext as _
from PIL import Image
from rest_framework import serializers
from .models import Account, Album, AlbumType, AlbumFile, Thumbnail, Event, EventGuest, InAppNotification
from django.utils import timezone
import requests
from .tasks import store_albumfile_and_thumbnails_s3
from .tasks import send_email, send_notifications
from core.shared.const.NotificationTypes import NotificationTypes
import logging
logger = logging.getLogger(__name__)


class AccountSerializer(serializers.HyperlinkedModelSerializer):
    # profile_image = serializers.SerializerMethodField('get_user_albumfile')

    # def get_user_albumfile(self, obj):
    #     user = self.context['request'].user
    #     albumfiles = AlbumFile.objects.filter(owner=user)
    #     serializer = AlbumFileSerializer(many=True, data=albumfiles, context={'request': self.context['request']})
    #     serializer.is_valid()
    #     return serializer.data

    class Meta:
        model = Account
        fields = ('url', 'name', 'email', 'profile_albumfile')


class ThumbnailSerializer(serializers.ModelSerializer):

    class Meta:
        model = Thumbnail
        fields = ('size_type', 'file_url', 'width', 'height', 'size_bytes')


class AlbumTypeSerializer(serializers.ModelSerializer):

    class Meta:
        model = AlbumType
        fields = ('id', 'name', 'description')


class FileFieldAllowEmpty(serializers.FileField):
    "Work-around for fact that normal FileField has trouble with empty values."

    def to_internal_value(self, data):
        if not data and not self.required:
            return data

        return super(FileFieldAllowEmpty, self).to_internal_value(data)


class TempImageFileData(object):

    def __init__(self, **kw):
        self.filename = kw.get('filename')
        self.original_name = kw.get('original_name')
        self.width = kw.get('width')
        self.height = kw.get('height')
        self.format = kw.get('format', '')
        self.size_bytes = kw.get('size_bytes')

    def update_from_file(self, filename):
        if not self.filename:
            new_name = "{}.{}".format(filename, self.format.lower())
            os.rename(filename, new_name)
            self.filename = new_name
        self.size_bytes = os.path.getsize(self.filename)


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

        tmp = self._get_tmpfile()
        for chunk in resp.iter_content(65536):  # 64K
            tmp.write(chunk)

        img_data = self._validate_img_file(tmp)
        img_data.original_name = unquote(data.split('/')[-1])
        filename = tmp.name
        tmp.close()
        img_data.update_from_file(filename)

        self.context['img_data'] = img_data

        return data

    def validate_source_file(self, data):

        if not data:
            return data

        if data.content_type.startswith('video/'):
            raise serializers.ValidationError(_("Uploading videos not yet supported."))

        if not (data.content_type.startswith('image/') or data.content_type.startswith('video/')):
            msg = _("Url needs to contain an image.")  # TODO: Or a video
            raise serializers.ValidationError(msg)

        tmp = self._get_tmpfile()
        for chunk in data.chunks():
            tmp.write(chunk)

        img_data = self._validate_img_file(tmp)
        img_data.original_name = data.name

        filename = tmp.name
        tmp.close()
        img_data.update_from_file(filename)

        self.context['img_data'] = img_data

        return data

    def _get_tmpfile(self):
        return tempfile.NamedTemporaryFile(dir=settings.TEMP_ALBUMFILE_DIR, prefix='img', delete=False)

    def _validate_img_file(self, imgfile):
        "Bare validation to make sure what was uploaded is a parseable image."

        imgfile.seek(0)

        try:
            img = Image.open(imgfile)
            w, h = img.size
            format_ = img.format
        except IOError:
            try:
                os.remove(imgfile)
            except OSError:
                pass
            raise serializers.ValidationError('Does not appear to be a valid image.')

        return TempImageFileData(width=w, height=h, format=format_)

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
            af = album.albumfiles.create(
                owner=self.context['request'].user,
                name=validated_data.get('name') or img_data.original_name.rsplit('.', 1)[0],
                description=validated_data.get('description', ''),
                width=img_data.width,
                height=img_data.height,
                size_bytes=img_data.size_bytes,
                file_type=AlbumFile.PHOTO_TYPE,
                status=AlbumFile.PROCESSING,
                # tmp_filename=img_data.filename,
                # tmp_hostname=settings.HOST_NAME
                )
            store_albumfile_and_thumbnails_s3(af.id)  # Async task
            # send out in-app notifications to all guests
            guests = album.event.guests.all()
            self.send_notifications(guests, af)

            return af

    def send_notifications(self, guests, albumfile):
        notification_type = NotificationTypes.ALBUMFILE_UPLOAD.value
        sender = self.context['request'].user
        for guest in guests:
            send_notifications(notification_type, sender.id, guest.id, 'albumfile', albumfile.id)


class EventSerializer(serializers.HyperlinkedModelSerializer):

    owner = serializers.HyperlinkedRelatedField(read_only=True, view_name='account-detail')
    albums = serializers.HyperlinkedRelatedField(many=True, view_name='album-detail', read_only=True)
    # guests = serializers.HyperlinkedRelatedField(many=True, view_name='account-detail', read_only=True)
    guests = serializers.HyperlinkedIdentityField(view_name='eventguest-list')
    lat = serializers.FloatField(allow_null=True, read_only=True)
    lon = serializers.FloatField(allow_null=True, read_only=True)

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

    def send_notifications(self, event):
        notification_type = NotificationTypes.EVENT_UPDATE.value
        sender = self.context['request'].user
        guests = event.guests.all()
        for guest in guests:
            send_notifications(notification_type, sender.id, guest.id, 'event', event.id)


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
                # Send invitation email
                # self.send_invitation()  
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

    # def send_invitation(self):
    #     notification_type = 'invite'
    #     # gather sender data
    #     sender = self.context['request'].user
    #     logger.debug(sender.phone)
    #     data = {
    #         'Site_Url': 'http://devapi.eventure.com/',

    #         'ProfileImage': 'https://www.petfinder.com/wp-content/uploads/2012/11/dog-how-to-select-your-new-best-friend-thinkstock99062463.jpg',
    #         'Email': sender.email,
    #         'Phone': sender.phone,
    #         'AccountName': sender.name,
    #         'AccountScreenName': sender.name,
    #     }
    #     # gather recipient data
    #     to_email = 'tidushue@gmail.com' #guest.email 
    #     # gather event data
    #     data.update({
    #             'PlanID': 2,
    #             'Title': 'Event ABCDEF',
    #             'StartDate': '2015-6-1 12PM',
    #             'Address': '123 Someplace',
    #         })

    #     # gather card data
    #     data['Card'] = u'<a href="default.asp">\
    #                         <img src="http://imagesdie.com/wp-content/uploads/2015/02/dog-poll-photos-videos-blogs-itimes-animals-images-dog-pictures.jpg" alt="HTML tutorial" style="width:420px;border:0">\
    #                         </a>'

    #     send_email(notification_type, to_email, data) # async task
    def send_notifications(self, guest_id):
        notification_type = NotificationTypes.EVENT_INVITE.value
        sender = self.context['request'].user
        event = self.context['event']

        send_notifications(notification_type, sender.id, guest_id, 'event', event.id)  # async


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

        send_notifications(notification_type, sender.id, recipient.id, 'eventguest', eventguest.id)  # async


class AlbumSerializer(serializers.HyperlinkedModelSerializer):

    album_type = AlbumTypeSerializer(read_only=True, default=AlbumType.objects.get(name='CUSTOM'))
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


class InAppNotificationSerializer(serializers.HyperlinkedModelSerializer):
    content_type = serializers.CharField()

    class Meta:
        model = InAppNotification
        fields = ('sender', 'recipient', 'notification_type', 'content_type', 'object_id')
# EOF
