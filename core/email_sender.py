import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import Context
from django.template.loader import get_template


logger = logging.getLogger(__name__)


# MAPPING from NotificationType to Email Template
notification_map = {
    'invite': 'email/plan-invitation',
}


def send(NotificationType, to_email, data):
    template = notification_map.get(NotificationType)
    if template is None:
        raise ValueError("Email template not found")

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
