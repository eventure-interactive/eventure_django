from datetime import datetime
from six.moves.urllib.parse import unquote
import uuid
import boto
import phonenumbers
import mimetypes
from django.contrib.contenttypes.fields import GenericForeignKey
from django.contrib.contenttypes.models import ContentType
from django.core.validators import RegexValidator, MinValueValidator, MaxValueValidator, EmailValidator
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.contrib.postgres.fields import HStoreField
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.conf import settings
from django.core.exceptions import ValidationError
from django.contrib.gis.db import models
from django.contrib.gis.geos import Point
from geopy.geocoders import GoogleV3
from core.shared.const.NotificationTypes import NotificationTypes
from jsonfield import JSONField
from rest_framework import serializers
import logging
logger = logging.getLogger(__name__)


class AccountUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, email, password, phone_country=None, phone=None, is_staff=False,
                     is_superuser=False, status=None, **extra):
        if phone:
            phone = Account.canonical_phone(phone, phone_country)
        if email:
            email = self.normalize_email(email)
        else:
            raise ValueError('The email is required to create this user')
        user = self.model(email=email, phone=phone, is_staff=is_staff, is_superuser=is_superuser, **extra)
        if status is not None:
            user.status = status
        user.set_password(password)
        user.save(self._db)
        return user

    def create_user(self, email, password, phone_country=None, phone=None, **extra):
        return self._create_user(email, password, phone_country, phone, False, False, **extra)

    def create_superuser(self, email, password, phone_country=None, phone=None, **extra):
        return self._create_user(email, password, phone_country, phone, True, True, Account.ACTIVE, **extra)


class Account(AbstractBaseUser, PermissionsMixin):

    class Meta:
        ordering = ('email',)

    CONTACT = -1  # Not signed up; stub account for future account
    SIGNED_UP = 0
    DELETED = 2
    ACTIVE = 3
    DEACTIVE_FORCEFULLY = 5

    STATUS_CHOICES = (
        (CONTACT, 'Contact'),
        (SIGNED_UP, 'Signed Up'),
        (DELETED, 'Deleted'),
        (ACTIVE, 'Active'),
        (DEACTIVE_FORCEFULLY, 'Forcefully Inactivated'),
    )

    phone = models.CharField(unique=True, max_length=40, null=True, validators=[RegexValidator(r'\+?[0-9(). -]')])
    name = models.CharField(max_length=255, null=True, blank=True)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=SIGNED_UP)
    show_welcome_page = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    modified = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(default=timezone.now)
    email = models.CharField(unique=True, max_length=100, validators=[EmailValidator()])
    last_ntf_checked = models.DateTimeField(null=True)
    profile_albumfile = models.ForeignKey('AlbumFile', blank=True, null=True)

    objects = AccountUserManager()

    @property
    def is_active(self):
        return self.status == self.ACTIVE

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return "{name}... XX{email}".format(name=self.name or '', email=self.email[:5])

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    @staticmethod
    def canonical_phone(phone_number, country=None):
        """Return the canonical phone number for a given phone number and country.

        Assumes a US phone number if no country is given.
        """
        if len(phone_number) < 1:
            return ValueError(_("Phone number too short."))
        if not country and phone_number[0] != '+':
            # Assume US phone number
            country = 'US'

        pn = phonenumbers.parse(phone_number, country)
        if not phonenumbers.is_valid_number(pn):
            raise ValueError(_('Does not seem to be a valid phone number'))

        return phonenumbers.format_number(pn, phonenumbers.PhoneNumberFormat.E164)

    def __str__(self):
        return self.get_short_name()


class AlbumType(models.Model):

    class Meta:
        ordering = ('sort_order',)

    id = models.PositiveIntegerField(primary_key=True)  # No auto-increment
    name = models.CharField(unique=True, max_length=40)
    description = models.CharField(max_length=80)
    sort_order = models.PositiveSmallIntegerField()
    is_virtual = models.BooleanField()
    is_deletable = models.BooleanField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ActiveStatusManager(models.Manager):
    "Return only items where the status is ACTIVE."

    def get_queryset(self):
        return super(ActiveStatusManager, self).get_queryset().filter(status=self.model.ACTIVE)


class ActiveProcessingStatusManager(models.Manager):
    "Return only items where the status is ACTIVE or PROCESSING"

    def get_queryset(self):
        return super(ActiveStatusManager, self).get_queryset()\
            .filter(status__in=(self.model.ACTIVE, self.model.PROCESSING))


class AlbumFile(models.Model):

    PHOTO_TYPE = 1
    VIDEO_TYPE = 2

    FILETYPE_CHOICES = (
        (PHOTO_TYPE, 'PHOTO'),
        (VIDEO_TYPE, 'VIDEO'),
    )

    ACTIVE = 1
    INACTIVE = 2
    DELETED = 3
    PROCESSING = 4
    ERROR = 5

    STATUS_CHOICES = (
        (ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
        (PROCESSING, 'Processing'),
        (ERROR, 'Error'),
        (DELETED, 'Deleted'),
    )

    class Meta:
        unique_together = (("s3_bucket", "s3_key"),)

    objects = models.Manager()
    active = ActiveStatusManager()
    activepending = ActiveProcessingStatusManager()

    owner = models.ForeignKey('Account')
    name = models.CharField(max_length=255, blank=True)
    description = models.TextField(blank=True)
    file_url = models.URLField(unique=True, null=True)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    size_bytes = models.PositiveIntegerField()
    file_type = models.PositiveSmallIntegerField(choices=FILETYPE_CHOICES)
    status = models.SmallIntegerField(choices=STATUS_CHOICES)
    albums = models.ManyToManyField('Album', related_name='albumfiles')

    s3_bucket = models.CharField(max_length=255, null=True)
    s3_key = models.CharField(max_length=255, null=True)

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)
    media_created = models.DateTimeField(null=True, blank=True)  # When the base media file was taken/created.

    def __str__(self):
        return self.name

    def upload_s3_photo(self, file_obj, img_format):
        "Upload a photo contained in file_obj to s3 and set the appropriate albumfile properties."

        if self.file_type == AlbumFile.VIDEO_TYPE:
            raise NotImplementedError('Videos are unsupported')

        self.s3_bucket = settings.S3_MEDIA_UPLOAD_BUCKET
        conn = boto.s3.connect_to_region(settings.S3_MEDIA_REGION,
                                         aws_access_key_id=settings.AWS_MEDIA_ACCESS_KEY,
                                         aws_secret_access_key=settings.AWS_MEDIA_SECRET_KEY)

        bucket = conn.get_bucket(self.s3_bucket, validate=False)

        if not self.s3_key:
            datepart = datetime.utcnow().strftime("%Y/%m/%d")
            fname = uuid.uuid4()
            fmtargs = dict(datepart=datepart, filename=fname, ext=img_format.lower(),
                           prefix=settings.S3_MEDIA_KEY_PREFIX)
            self.s3_key = "{prefix}img/{datepart}/{filename}.{ext}".format(**fmtargs)
            k = bucket.new_key(self.s3_key)
        else:
            k = bucket.get_key(self.s3_key)

        headers = {}
        content_type = mimetypes.types_map.get('.' + img_format.lower())
        if content_type:
            headers['Content-Type'] = content_type

        file_obj.seek(0)
        self.size_bytes = k.set_contents_from_file(file_obj, headers=headers, policy='public-read')
        self.file_url = k.generate_url(expires_in=0, query_auth=False)


class Album(models.Model):

    ACTIVE = 1
    INACTIVE = 2
    DELETED = 3

    STATUS_CHOICES = (
        (ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
        (DELETED, 'Deleted'),
    )

    class Meta:
        ordering = ('album_type__sort_order',)

    objects = models.Manager()
    active = ActiveStatusManager()

    owner = models.ForeignKey('Account', related_name='albums')  # This is the owner of the album
    event = models.ForeignKey('Event', related_name='albums', null=True, blank=True, default=None)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    album_type = models.ForeignKey('AlbumType')
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=ACTIVE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    def albumfiles_queryset(self, account):
        """Return an appropriate queryset for this albumfile type.

        Queryset will vary depending on if the album_type is virtual.
        """
        if not self.album_type.is_virtual:
            return self.albumfiles.filter(status=AlbumFile.ACTIVE)
        elif self.album_type.name == "ALLMEDIA":
            return AlbumFile.active.filter(owner=account)
        else:
            raise NotImplementedError(_("%(name)s albumfiles query not implemented") % {'name': self.album_type.name})


class Thumbnail(models.Model):

    class Meta:
        ordering = ('size_type',)
        unique_together = (('albumfile', 'size_type'))

    SIZE_48 = 48
    SIZE_100 = 100
    SIZE_144 = 144
    SIZE_205 = 205
    SIZE_320 = 320
    SIZE_610 = 610
    SIZE_960 = 960

    SIZE_CHOICES = (
        (SIZE_48, "SIZE_48"),
        (SIZE_100, "SIZE_100"),
        (SIZE_144, "SIZE_144"),
        (SIZE_205, "SIZE_205"),
        (SIZE_320, "SIZE_320"),
        (SIZE_610, "SIZE_610"),
        (SIZE_960, "SIZE_960"),
    )

    albumfile = models.ForeignKey('AlbumFile', related_name='thumbnails')
    file_url = models.URLField(unique=True)
    size_type = models.PositiveSmallIntegerField(choices=SIZE_CHOICES)
    width = models.PositiveIntegerField()
    height = models.PositiveIntegerField()
    size_bytes = models.PositiveIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    @property
    def name(self):
        if self.file_url:
            return unquote(self.file_url.split("/")[-1])
        else:
            return ""

    def __str__(self):
        return self.name


class Event(models.Model):
    PUBLIC = 1
    PRIVATE = 2

    PRIVACY_CHOICES = (
        (PUBLIC, 'Public'),
        (PRIVATE, 'Private'),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    title = models.CharField(max_length=100,)
    start = models.DateTimeField()  # UTC start time
    end = models.DateTimeField()  # UTC end time
    owner = models.ForeignKey('Account', related_name='events')
    guests = models.ManyToManyField('Account', through='EventGuest')

    privacy = models.SmallIntegerField(choices=PRIVACY_CHOICES, default=PUBLIC)

    location = models.CharField(max_length=250, null=True)
    lon = models.FloatField(null=True)
    lat = models.FloatField(null=True)
    mpoint = models.PointField(null=True, geography=True)

    objects = models.GeoManager()

    class Meta:
        ordering = ('created',)

    def __str__(self):
        return "%s %s" % (self.id, self.title)

    def save(self, *args, **kwargs):
        # Geocoding to get lat lon and update PointField on create/update
        geolocator = GoogleV3()
        loc = geolocator.geocode(self.location)
        self.lat = loc.latitude
        self.lon = loc.longitude

        self.mpoint = Point(self.lon, self.lat, srid=4326)
        super(Event, self).save(*args, **kwargs)


class EventGuest(models.Model):
    UNDECIDED = 0
    YES = 1
    NO  = 2
    MAYBE = 3

    RSVP_CHOICES = (
        (UNDECIDED, 'Undecided'),
        (YES, 'Yes'),
        (NO, 'No'),
        (MAYBE, 'Maybe')
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    guest = models.ForeignKey('Account', related_name='guests')
    event = models.ForeignKey('Event')
    rsvp = models.SmallIntegerField(choices=RSVP_CHOICES, default=UNDECIDED)

    # class Meta: # comment out so event can be read-only in serializer
    #     unique_together = (("guest", "event"),)


class InAppNotification(models.Model):
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    sender = models.ForeignKey('Account', related_name='sent_ntfs')
    recipient = models.ForeignKey('Account', related_name='received_ntfs')
    notification_type = models.SmallIntegerField(choices=NotificationTypes.choices())

    #polymorphic generic relation (ForeignKey to multiple models)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')


class Follow(models.Model):
    PENDING = 0
    APPROVED = 1
    UNAPPROVED = 2

    STATUS_CHOICES = (
        (PENDING, 'PENDING'),
        (APPROVED, 'APPROVED'),
        (UNAPPROVED, 'UNAPPROVED')
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    follower = models.ForeignKey('Account', related_name='followings')
    followee = models.ForeignKey('Account', related_name='followers')
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=PENDING)


class EventInStreamSerializer(serializers.ModelSerializer):
    class Meta:
        model = Event
        fields = ('title', 'start', 'location', 'guests')


class Stream(models.Model):
    EVENT_CREATE = 0
    EVENTGUEST_ADD = 1

    STREAMTYPE_CHOICES = (
        (EVENT_CREATE, 'EVENT_CREATE'),
        (EVENTGUEST_ADD, 'EVENTGUEST_ADD'),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    stream_type = models.SmallIntegerField(choices=STREAMTYPE_CHOICES)
    data = JSONField()

    sender = models.ForeignKey('Account', related_name='sent_streams')
    recipient = models.ForeignKey('Account', related_name='streams')

    #polymorphic generic relation (ForeignKey to multiple models)
    content_type = models.ForeignKey(ContentType)
    object_id = models.PositiveIntegerField()
    content_object = GenericForeignKey('content_type', 'object_id')

    def save(self, *args, **kwargs):
        # Auto generate and save json presentation of data
        serializer = None
        if self.content_type.model_class() == Event:
            serializer = EventInStreamSerializer(self.content_object)


        if serializer.data is not None:
            self.data = serializer.data
        super(Stream, self).save(*args, **kwargs)


class CommChannel(models.Model):
    ''' Store info about validation of email or phone of account '''
    EMAIL = 0
    PHONE = 1

    COMM_CHANNEL_CHOICES = (
        (EMAIL, 'EMAIL'),
        (PHONE, 'PHONE'),
    )

    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    account = models.ForeignKey('Account', )
    comm_type = models.SmallIntegerField(choices=COMM_CHANNEL_CHOICES)
    comm_endpoint = models.CharField(max_length=100)  # email or phone to be validated
    validation_token = models.UUIDField(unique=True, default=uuid.uuid4)
    validation_date = models.DateTimeField(null=True)  # null if not yet validated
    message_sent_date = models.DateTimeField(null=True)


# EOF
