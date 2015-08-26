# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0058_applecredentials'),
    ]

    operations = [
        migrations.AlterField(
            model_name='applecredentials',
            name='account',
            field=models.OneToOneField(serialize=False, primary_key=True, to=settings.AUTH_USER_MODEL, related_name='apple_credentials'),
        ),
    ]
