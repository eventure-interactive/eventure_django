# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0060_auto_20150806_2232'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventguest',
            name='name',
            field=models.CharField(max_length=255, blank=True),
        ),
    ]
