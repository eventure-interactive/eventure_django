# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0069_auto_20150819_2220'),
    ]

    operations = [
        migrations.AlterField(
            model_name='inappnotification',
            name='notification_type',
            field=models.SmallIntegerField(choices=[(5, 'ACCOUNT_EMAIL_VALIDATE'), (4, 'ALBUMFILE_UPLOAD'), (2, 'EVENTGUEST_RSVP'), (6, 'EVENT_CANCEL'), (1, 'EVENT_INVITE'), (3, 'EVENT_UPDATE')]),
        ),
    ]
