from django.db.models.signals import pre_delete, post_save, m2m_changed
from django.dispatch import receiver
from django.utils.translation import ugettext as _
from core.models import Album, Account, AccountSettings


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
