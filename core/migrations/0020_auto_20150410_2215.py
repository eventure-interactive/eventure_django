# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.contrib.gis.db.models.fields


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0019_auto_20150410_1913'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='mpoint',
            field=django.contrib.gis.db.models.fields.PointField(null=True, geography=True, srid=4326),
        ),
    ]
