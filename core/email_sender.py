#-*- coding: utf-8 -*-

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.utils import formatdate

from mako.template import Template
from mako.lookup import TemplateLookup
from mako import exceptions

from traceback import format_exc
import smtplib
import logging
import os

from celery import shared_task
from django.conf import settings

logger = logging.getLogger(__name__)


class EmailConfig:
    templates_path = os.path.abspath(os.path.join('res', 'email-templates')) + os.sep
    from_email = "from.all.of.us@eventure.com"
    smtp_server = {"server": "smtpout.secureserver.net", "username": "from.all.of.us@eventure.com", "password": "1Billion"}

# MAPPING from NotificationType to Email Template
notification_map = {
    'invite': 'plan-invitation.htm',
}


@shared_task(queue=settings.HOST_NAME)
def send(NotificationType, to_email, data):
    try:
        template = notification_map.get(NotificationType)
        if template is None:
            raise ValueError("Email template not found")

        mylookup = TemplateLookup(directories=['/', '.', EmailConfig.templates_path, 'C:/', 'D:/', 'E:/'], input_encoding='utf-8', output_encoding='utf-8', encoding_errors='replace')
        template = EmailConfig.templates_path + template
        template = Template(filename=template, lookup=mylookup)
        html = str(template.render(**data))
        subject_start = str.find(html, "<subject>")
        subject_end = str.find(html, "</subject>")
        if subject_start == -1 or subject_end == -1:
            raise ValueError("Subject not found")
        subject = html[subject_start + 9: subject_end]
        html = str.replace(html, "<subject>" + subject + "</subject>", "")

        msg = MIMEMultipart()
        msg['From'] = EmailConfig.from_email
        msg['To'] = to_email
        msg['Date'] = formatdate(localtime=True)
        msg['Subject'] = subject
        msg.attach(MIMEText(html, "html", "utf-8"))
        smtp_server = EmailConfig.smtp_server
        smtp = smtplib.SMTP(smtp_server["server"])
        if smtp_server.get("password") and smtp_server.get("username"):
            smtp.login(smtp_server["username"], smtp_server["password"])
        receivers = [to_email]
        smtp.sendmail(EmailConfig.from_email, receivers, msg.as_string())
        smtp.close()

        logger.info("Sending email [" + str(NotificationType) + "] to [" + str(to_email) + "] sucessful")
    except:
        logger.error("Sending email [" + str(NotificationType) + "] to [" + str(to_email) + "] failed:\r\n" + format_exc())

#EOF
