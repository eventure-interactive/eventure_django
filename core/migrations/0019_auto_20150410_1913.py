# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0018_auto_20150410_1910'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='eventguest',
            name='lat',
        ),
        migrations.RemoveField(
            model_name='eventguest',
            name='location',
        ),
        migrations.RemoveField(
            model_name='eventguest',
            name='lon',
        ),
        migrations.RemoveField(
            model_name='eventguest',
            name='mpoint',
        ),
        migrations.AddField(
            model_name='event',
            name='lat',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='location',
            field=models.CharField(null=True, max_length=250),
        ),
        migrations.AddField(
            model_name='event',
            name='lon',
            field=models.FloatField(null=True),
        ),
        migrations.AddField(
            model_name='event',
            name='mpoint',
            field=django.contrib.gis.db.models.fields.PointField(null=True, srid=4326),
        ),
    ]
