# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0037_auto_20150617_2106'),
    ]

    operations = [
        # migrations.AlterField(
        #     model_name='account',
        #     name='email',
        #     field=models.CharField(default='default%s@eventure.com', validators=[django.core.validators.EmailValidator()], null=True, max_length=100),
        #     preserve_default=False,
        # ),
        migrations.AlterField(
            model_name='account',
            name='phone',
            field=models.CharField(null=True, validators=[django.core.validators.RegexValidator('\\+?[0-9(). -]')], unique=True, max_length=40),
        ),
    ]
