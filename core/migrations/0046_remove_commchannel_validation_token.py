# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0044_auto_20150709_1715'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='commchannel',
            name='validation_token',
        ),
    ]
