# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators
from django.utils.timezone import utc
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20150406_2329'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventguest',
            name='rsvp',
            field=models.SmallIntegerField(default=0, choices=[(0, 'Undecided'), (1, 'Yes'), (2, 'No'), (3, 'Maybe')]),
        ),
        migrations.AlterField(
            model_name='event',
            name='start',
            field=models.DateTimeField(validators=[django.core.validators.MinValueValidator(datetime.datetime(2015, 4, 8, 1, 18, 50, 831680, tzinfo=utc), 'Start Date must be in the future')]),
        ),
    ]
