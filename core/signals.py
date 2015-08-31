from django.db.models.signals import pre_delete, post_save, m2m_changed
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from django.db.models import Q
from core.models import Album, Account, AccountStatus, AccountSettings, Event, EventGuest, AppleCredentials
from core.shared import icloud_http, icloud_webdav
from celery import shared_task
import logging
logger = logging.getLogger(__name__)


class AlbumNotDeletableError(Exception):
    pass


@receiver(pre_delete, sender=Album)
def handle_album_delete(sender, instance, **kwargs):

    if not instance.album_type.is_deletable:
        msg = _('Cannot delete an Album of type %(type_name)s') % {'type_name': instance.album_type.name}
        raise AlbumNotDeletableError(msg)


# TODO: Want to restrict saving albumfiles to virtual albums
def handle_album_m2m_albumfile(sender, instance, action, reverse, model, **kwargs):
    pass


@receiver(post_save, sender=Account)
def handle_account_create(sender, instance, created, **kwargs):
    "Add AcccountSettings on account creation."
    if created:
        settings = AccountSettings(account=instance)
        settings.save()


@receiver(post_save, sender=Event)
def export_to_icloud_calendar_when_updating_event(sender, instance, **kwargs):
    "Create or Update icloud calendar event for owner, guests when an event is saved"
    to_icloud.s(instance.id).delay()


@receiver(post_save, sender=EventGuest)
def export_to_icloud_calendar_when_updating_eventguest(sender, instance, **kwargs):
    "Create or Update icloud calendar event for owner, guests when an guest is added/changed rsvp"
    to_icloud.s(instance.event.id).delay()


def export_to_icloud(account, rsvp, ical_event, caldav_event):
    """Based on account credentials, use ical or caldav protocol
    Params: ical_event: event in format that accepted by icloud.com
            caldav_event: event in caldav format
            account: core.models.Account
            rsvp: core.models.EventGuest.rsvp
    """
    try:
        ac = AppleCredentials.objects.get(account=account)
    except AppleCredentials.DoesNotExist:
        logger.debug('Account ID %s does not have apple credentials. No event exported.' % account.id)
    else:
        if ac.credentials.apple_password:  # 2-step-verification with app-specific password
            icloud_webdav.export_to_icloud(caldav_event, account, rsvp, ac)
        elif ac.credentials.x_apple_webauth_token:  # regular apple account
            icloud_http.export_to_icloud(ical_event, account, rsvp, ac)


@shared_task
def to_icloud(event_id):
    """
    Create or Update an event on owner & guests' icloud Calendar
    Params: event: core.models.event
    """
    # TODO: need to check that event status is not draft
    try:
        event = Event.objects.get(pk=event_id)
    except Event.DoesNotExist:
        logger.error('Event %d does not exist' % event_id)
    else:
        ical_event = icloud_http.to_ical_event(event)
        caldav_event = icloud_webdav.to_ical_event(event)
        # For event owner
        response = export_to_icloud(event.owner, None, ical_event, caldav_event)
        if response is not None and response.status_code != 200:
            logger.error(response.json())

        # For guest
        guests = EventGuest.objects.filter(Q(event_id=event_id), Q(guest__status=AccountStatus.ACTIVE),)

        for guest in guests:
            response = export_to_icloud(guest.guest, guest.rsvp, ical_event, caldav_event)
            # Log if error
            if response is not None and response.status_code != 200:
                logger.error(response.json())
