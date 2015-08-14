# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0062_manual_eventguest_unique_constraint'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='featured_albumfile',
            field=models.ForeignKey(blank=True, null=True, to='core.AlbumFile'),
        ),
    ]
