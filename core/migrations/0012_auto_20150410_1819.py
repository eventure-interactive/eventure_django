# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_auto_20150410_1800'),
    ]

    operations = [
        migrations.AlterField(
            model_name='albumfile',
            name='file_url',
            field=models.URLField(unique=True, null=True),
        ),
    ]
