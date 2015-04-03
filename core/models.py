import phonenumbers
from django.db import models
from django.core.validators import RegexValidator
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin, BaseUserManager
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _


class AccountUserManager(BaseUserManager):
    use_in_migrations = True

    def _create_user(self, phone, password, phone_country=None, email=None, is_staff=False,
                     is_superuser=False, status=None, **extra):
        phone = Account.canonical_phone(phone, phone_country)
        if email:
            email = self.normalize_email(email)
            # TODO: Save email (we don't have it set up yet)
        user = self.model(phone=phone, is_staff=is_staff, is_superuser=is_superuser, **extra)
        if status is not None:
            user.status = status
        user.set_password(password)
        user.save(self._db)
        return user

    def create_user(self, phone, password, phone_country=None, email=None, **extra):
        return self._create_user(phone, password, phone_country, email, False, False, **extra)

    def create_superuser(self, phone, password, phone_country=None, email=None, **extra):
        return self._create_user(phone, password, phone_country, email, True, True, Account.ACTIVE, **extra)


class Account(AbstractBaseUser, PermissionsMixin):

    class Meta:
        ordering = ('name',)

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

    phone = models.CharField(unique=True, max_length=40, validators=[RegexValidator(r'\+?[0-9(). -]')])
    name = models.CharField(max_length=255)
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=SIGNED_UP)
    show_welcome_page = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    modified = models.DateTimeField(auto_now=True)
    date_joined = models.DateTimeField(default=timezone.now)

    objects = AccountUserManager()

    @property
    def is_active(self):
        return self.status == self.ACTIVE

    def get_full_name(self):
        return self.name

    def get_short_name(self):
        return "{name}... XX{ph}".format(name=self.name[:5], ph=self.phone[-2:])

    USERNAME_FIELD = 'phone'
    REQUIRED_FIELDS = ['name']

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


class AlbumType(models.Model):

    class Meta:
        ordering = ('sort_order',)

    id = models.PositiveIntegerField(primary_key=True)  # No auto-increment
    name = models.CharField(unique=True, max_length=40)
    description = models.CharField(max_length=80)
    sort_order = models.PositiveSmallIntegerField()
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name


class ActiveStatusManager(models.Manager):
    "Return only items where the status is ACTIVE."

    def get_queryset(self):
        return super().get_queryset().filter(status=self.model.ACTIVE)


class Album(models.Model):

    ACTIVE = 1
    INACTIVE = 2
    DELETED = 3

    STATUS_CHOICES = (
        (ACTIVE, 'Active'),
        (INACTIVE, 'Inactive'),
        (DELETED, 'Deleted'),
    )

    active = ActiveStatusManager()
    objects = models.Manager()

    owner = models.ForeignKey('Account', related_name='albums')  # This is the owner of the album
    # event = models.ForeignKey('Event')
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    album_type = models.ForeignKey('AlbumType')
    status = models.SmallIntegerField(choices=STATUS_CHOICES, default=ACTIVE)
    created = models.DateTimeField(auto_now_add=True)
    modified = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name
