# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0051_auto_20150713_1856'),
    ]

    operations = [
        migrations.CreateModel(
            name='PasswordReset',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('email', models.EmailField(max_length=254, db_index=True)),
                ('token_salt', models.UUIDField(default=uuid.uuid4)),
                ('message_sent_date', models.DateTimeField(null=True)),
                ('reset_date', models.DateTimeField(null=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('account', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
