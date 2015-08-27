# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0059_auto_20150806_1827'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='is_all_day',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='event',
            name='status',
            field=models.PositiveSmallIntegerField(choices=[(2, 'ACTIVE'), (3, 'CANCELLED'), (1, 'DRAFT')], default=1),
        ),
    ]
