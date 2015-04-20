# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0016_auto_20150408_2358'),
    ]

    operations = [
        migrations.AlterField(
            model_name='eventguest',
            name='guest',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='guests'),
        ),
    ]
