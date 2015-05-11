# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_event_privacy'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='profile_albumfile',
            field=models.ForeignKey(null=True, to='core.AlbumFile', blank=True),
        ),
    ]
