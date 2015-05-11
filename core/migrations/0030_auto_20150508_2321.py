# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0029_auto_20150507_2255'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='last_ntf_checked',
            field=models.DateTimeField(null=True),
        ),
        migrations.AlterField(
            model_name='inappnotification',
            name='notification_type',
            field=models.SmallIntegerField(choices=[(4, 'ALBUMFILE_UPLOAD'), (2, 'EVENTGUEST_RSVP'), (1, 'EVENT_INVITE'), (3, 'EVENT_UPDATE')]),
        ),
        
    ]
