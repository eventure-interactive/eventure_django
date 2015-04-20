# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0017_auto_20150409_0001'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventguest',
            name='lat',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='eventguest',
            name='location',
            field=models.CharField(null=True, max_length=250),
        ),
        migrations.AddField(
            model_name='eventguest',
            name='lon',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='eventguest',
            name='mpoint',
            field=django.contrib.gis.db.models.fields.PointField(null=True, srid=4326),
        ),
    ]
