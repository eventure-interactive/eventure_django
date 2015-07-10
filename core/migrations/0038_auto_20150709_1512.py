# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_auto_20150617_2106'),
    ]

    operations = [
        migrations.CreateModel(
            name='AccountSettings',
            fields=[
                ('account', models.OneToOneField(primary_key=True, to=settings.AUTH_USER_MODEL, serialize=False)),
                ('email_rsvp_updates', models.BooleanField(default=True)),
                ('email_social_activity', models.BooleanField(default=True)),
                ('email_promotions', models.BooleanField(default=True)),
                ('text_rsvp_updates', models.NullBooleanField()),
                ('text_social_activity', models.NullBooleanField()),
                ('text_promotions', models.NullBooleanField()),
                ('default_event_privacy', models.PositiveSmallIntegerField(choices=[(1, 'Public'), (2, 'Private')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AddField(
            model_name='account',
            name='profile_privacy',
            field=models.PositiveSmallIntegerField(choices=[(0, 'Public'), (2, 'Private')], default=0),
        ),
    ]
