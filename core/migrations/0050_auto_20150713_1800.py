# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import datetime
import django.core.validators
import django.utils.timezone
import core.validators
import core.modelfields
from django.utils.timezone import utc


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0049_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='created',
            field=models.DateTimeField(default=datetime.datetime(2015, 7, 13, 18, 0, 31, 425769, tzinfo=utc), auto_now_add=True),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='account',
            name='solr_id',
            field=core.modelfields.EmptyStringToNoneField(null=True, max_length=45, unique=True, blank=True),
        ),
        migrations.AlterField(
            model_name='account',
            name='date_joined',
            field=models.DateTimeField(null=True, default=django.utils.timezone.now),
        ),
        migrations.AlterField(
            model_name='account',
            name='email',
            field=core.modelfields.EmptyStringToNoneField(null=True, unique=True, max_length=100, validators=[django.core.validators.EmailValidator()]),
        ),
        migrations.AlterField(
            model_name='account',
            name='name',
            field=models.CharField(default='', max_length=255, blank=True),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='account',
            name='phone',
            field=core.modelfields.EmptyStringToNoneField(null=True, max_length=40, unique=True, blank=True, validators=[core.validators.validate_phone_number]),
        ),
    ]
