# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_albumtype_is_virtual'),
    ]

    operations = [
        migrations.AddField(
            model_name='albumtype',
            name='is_deletable',
            field=models.BooleanField(default=False),
            preserve_default=False,
        ),
    ]
