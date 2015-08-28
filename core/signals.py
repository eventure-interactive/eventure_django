from django.db.models.signals import pre_delete, post_save, post_init, m2m_changed
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from core.models import Album, Account, AccountSettings, Event, EventGuest
from core.shared.const.choice_types import EventStatus, NotificationTypes
from core.shared.utilities import get_absolute_url
from core import tasks


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


def handle_tracked_post_init(sender, instance, **kwargs):
    "Store initial values of models so we can track what was changed."

    instance._prior_data = {}
    for field in instance.tracked_fields:
        instance._prior_data[field] = getattr(instance, field)

post_init.connect(handle_tracked_post_init, sender=Event)
post_init.connect(handle_tracked_post_init, sender=EventGuest)


@receiver(post_save, sender=Event)
def handle_event_notifications(sender, instance, **kwargs):

    event = instance

    if event.status == EventStatus.DRAFT.value:
        # Do nothing when working with draft events
        return

    status_changed = event.status != event._prior_data.get('status')

    if event.status == EventStatus.ACTIVE.value and status_changed:

        # This is a newly-active event. Send invitiations out.
        tasks.send_event_invitations.delay(event.id)
        for guest in event.guests.all():
            tasks.send_inapp_notification.delay(NotificationTypes.EVENT_INVITE.value, event.owner.id,
                                                guest.id, 'event', event.id)
        return

    if event.status == EventStatus.CANCELLED.value and event._prior_data.get('status') == EventStatus.ACTIVE.value:
        tasks.send_event_cancellation_notifications.delay(event.id)
        for guest in event.guests.all():
            tasks.send_inapp_notification.delay(NotificationTypes.EVENT_CANCEL.value, event.owner.id,
                                                guest.id, 'event', event.id)
        return

    for field in event.tracked_fields:
        if getattr(event, field) != event._prior_data[field]:
            tasks.send_event_update_notifications.delay(event.id)
            for guest in event.guests.all():
                tasks.send_inapp_notification.delay(NotificationTypes.EVENT_UPDATE.value, event.owner.id,
                                                    guest.id, 'event', event.id)
            return


@receiver(post_save, sender=EventGuest)
def handle_event_guest_notifications(sender, instance, created, **kwargs):

    event_guest = instance
    event = event_guest.event
    guest = event_guest.guest

    if created and event.status == EventStatus.ACTIVE.value:
        tasks.send_event_invitations.delay(event.id, guest_account_id=guest.id)
        tasks.send_inapp_notification.delay(NotificationTypes.EVENT_INVITE.value, event.owner.id,
                                            guest.id, 'event', event.id)
