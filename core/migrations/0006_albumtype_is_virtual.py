# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_auto_20150404_0516'),
    ]

    operations = [
        migrations.AddField(
            model_name='albumtype',
            name='is_virtual',
            field=models.BooleanField(default=True),
            preserve_default=False,
        ),
    ]
