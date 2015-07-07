import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives, EmailMessage
from django.core import mail
from django.template import Context
from django.template.loader import get_template
from core.shared.const.NotificationTypes import NotificationTypes
from django.contrib.contenttypes.models import ContentType
from core.models import Account
from celery import shared_task
logger = logging.getLogger(__name__)


# MAPPING from NotificationType to Email Template
notification_map = {
    NotificationTypes.EVENT_INVITE.value: 'email/plan-invitation',
    # NotificationTypes.EVENTGUEST_RSVP.value: '',  TODO
    # NotificationTypes.ALBUMFILE_UPLOAD.value: '',  TODO
}


def _send(NotificationType, to_email, data):
    template = notification_map.get(NotificationType)
    if template is None:
        # raise ValueError("Email template not found")
        logger.error("Email template for NotificationType %s is not found" % (NotificationType))
        return

    plaintext = get_template(template + '.txt')
    htmly = get_template(template + '.htm')

    ctx = Context(data)
    html_content = htmly.render(ctx)

    # find the subject in the rendered html
    subject_start = str.find(html_content, "<subject>")
    subject_end = str.find(html_content, "</subject>")

    if subject_start == -1 or subject_end == -1:
        raise ValueError("Subject not found")

    subject = html_content[subject_start + 9: subject_end]
    html_content = html_content.replace("<subject>" + subject + "</subject>", "")
    text_content = plaintext.render(ctx)

    msg = EmailMultiAlternatives(subject, text_content, settings.EMAIL_FROM, [to_email])
    msg.attach_alternative(html_content, "text/html")
    msg.send()

    logger.info("Sending email [" + str(NotificationType) + "] to [" + str(to_email) + "] sucessful")


@shared_task
def send_email(NotificationType, sender_id, recipient_id, obj_model_class, obj_id):
    # TODO Check if recipient wants email notification for this notification type

    # Gather email data then send
    recipient = Account.objects.get(pk=recipient_id)
    to_email = recipient.email

    if to_email:
        data = gather_email_data(NotificationType, sender_id, recipient_id, obj_model_class, obj_id)
        _send(NotificationType, to_email, data)


def gather_email_data(NotificationType, sender_id, recipient_id, obj_model_class, obj_id):
    ''' Each email notification template requires certain fields '''
    sender = Account.objects.get(pk=sender_id)
    recipient = Account.objects.get(pk=recipient_id)
    content_type = ContentType.objects.get(app_label=Account._meta.app_label, model=obj_model_class)
    content_object = content_type.get_object_for_this_type(pk=obj_id)

    data = {
        'Site_Url': '''http://eventure.com/api/''',  # TODO: add this to settings
        'to_email': recipient.email,
    }

    if NotificationType == NotificationTypes.EVENT_INVITE.value:
        data.update({
            'AccountName': sender.name,
            'Title': content_object.title,
            'StartDate': content_object.start.strftime("%b %d, %Y at %r (%Z)"),
            'Address': content_object.location,
            'Phone': sender.phone,
            'Notes': None,
            'PlanID': obj_id,
        })
    # elif NotificationTypes == NotificationTypes.EVENTGUEST_RSVP.value:  TODO
    # elif NotificationTypes == NotificationTypes.ALBUMFILE_UPLOAD.value:  TODO
        
    return data