# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings
import django.core.validators
from django.utils.timezone import utc
import datetime


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0013_auto_20150408_0118'),
    ]

    operations = [
        migrations.AlterField(
            model_name='event',
            name='start',
            field=models.DateTimeField(validators=[django.core.validators.MinValueValidator(datetime.datetime(2015, 4, 8, 23, 51, 22, 516758, tzinfo=utc), 'Start Date must be in the future')]),
        ),
        migrations.AlterField(
            model_name='eventguest',
            name='guest',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL),
        ),
    ]
