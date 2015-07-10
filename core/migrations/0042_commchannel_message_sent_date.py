# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0041_commchannel'),
    ]

    operations = [
        migrations.AddField(
            model_name='commchannel',
            name='message_sent_date',
            field=models.DateTimeField(null=True),
        ),
    ]
