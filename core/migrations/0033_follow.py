# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0032_auto_20150511_2227'),
    ]

    operations = [
        migrations.CreateModel(
            name='Follow',
            fields=[
                ('id', models.AutoField(verbose_name='ID', auto_created=True, primary_key=True, serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('status', models.SmallIntegerField(default=0, choices=[(0, 'PENDING'), (1, 'APPROVED'), (2, 'UNAPPROVED')])),
                ('followee', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='followings')),
                ('follower', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='followers')),
            ],
        ),
    ]
