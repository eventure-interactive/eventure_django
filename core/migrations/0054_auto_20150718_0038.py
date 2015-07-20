# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0053_auto_20150717_1657'),
    ]

    operations = [
        migrations.AlterField(
            model_name='googlecredentials',
            name='account',
            field=models.OneToOneField(primary_key=True, to=settings.AUTH_USER_MODEL, serialize=False),
        ),
    ]
