# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_make_account_email_unique_field'),
    ]

    operations = [
        migrations.CreateModel(
            name='CommChannel',
            fields=[
                ('id', models.AutoField(verbose_name='ID', serialize=False, auto_created=True, primary_key=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('comm_type', models.SmallIntegerField(choices=[(0, 'EMAIL'), (1, 'PHONE')])),
                ('comm_endpoint', models.CharField(max_length=100)),
                ('validation_token', models.CharField(max_length=20, unique=True, default=uuid.uuid4)),
                ('validation_date', models.DateTimeField(null=True)),
                ('account', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
