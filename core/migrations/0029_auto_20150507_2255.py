# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0028_auto_20150507_2202'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='inappnotification',
            name='recipients',
        ),
        migrations.AddField(
            model_name='inappnotification',
            name='recipient',
            field=models.ForeignKey(default=2, to=settings.AUTH_USER_MODEL, related_name='received_ntfs'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='inappnotification',
            name='sender',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='sent_ntfs'),
        ),
    ]
