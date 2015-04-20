# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
from django.utils.timezone import utc
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0014_auto_20150408_2351'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='start',
            field=models.DateTimeField(validators=[django.core.validators.MinValueValidator(datetime.datetime(2015, 4, 8, 23, 57, 54, 886022, tzinfo=utc), 'Start Date must be in the future')]),
        ),
    ]
