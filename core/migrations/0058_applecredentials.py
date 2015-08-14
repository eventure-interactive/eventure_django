# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_auto_20150728_0004'),
    ]

    operations = [
        migrations.CreateModel(
            name='AppleCredentials',
            fields=[
                ('account', models.OneToOneField(to=settings.AUTH_USER_MODEL, primary_key=True, serialize=False)),
                ('credentials', core.models.MyCredentialsField(null=True)),
            ],
        ),
    ]
