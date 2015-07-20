# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import oauth2client.django_orm


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_auto_20150713_1856'),
    ]

    operations = [
        migrations.CreateModel(
            name='GoogleCredentials',
            fields=[
                ('account', models.ForeignKey(related_name='google_credentials', serialize=False, to=settings.AUTH_USER_MODEL, primary_key=True)),
                ('credentials', oauth2client.django_orm.CredentialsField(null=True)),
            ],
        ),
    ]
