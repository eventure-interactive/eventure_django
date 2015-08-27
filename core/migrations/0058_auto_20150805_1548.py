# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0057_auto_20150728_0004'),
    ]

    operations = [
        migrations.AddField(
            model_name='accountsettings',
            name='home_calendar_color',
            field=models.CharField(max_length=6, default='00AEE3', validators=[django.core.validators.RegexValidator('[A-Fa-f0-9]{6}', message='Not a valid color (needs to be in hex format, e.g. FE00AC)')]),
        ),
        migrations.AddField(
            model_name='accountsettings',
            name='work_calendar_color',
            field=models.CharField(max_length=6, default='FF7979', validators=[django.core.validators.RegexValidator('[A-Fa-f0-9]{6}', message='Not a valid color (needs to be in hex format, e.g. FE00AC)')]),
        ),
        migrations.AddField(
            model_name='event',
            name='calendar_type',
            field=models.PositiveSmallIntegerField(choices=[(2, 'PERSONAL_CALENDAR'), (1, 'WORK_CALENDAR')], default=2),
        ),
    ]
