# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0034_auto_20150513_2127'),
    ]

    operations = [
        migrations.AddField(
            model_name='stream',
            name='recipient',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='streams', default=10),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='stream',
            name='sender',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='sent_streams', default=9),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='stream',
            name='stream_type',
            field=models.SmallIntegerField(default=1, choices=[(0, 'EVENT_CREATE'), (1, 'EVENTGUEST_ADD')]),
            preserve_default=False,
        ),
    ]
