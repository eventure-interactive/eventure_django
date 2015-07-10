# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators

class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_add_random_emails'),
    ]

    operations = [
        migrations.AlterField(
            model_name='account',
            name='email',
            field=models.CharField(default='default@eventure.com', validators=[django.core.validators.EmailValidator()], unique=True, max_length=100),
            preserve_default=False,
        ),
    ]
