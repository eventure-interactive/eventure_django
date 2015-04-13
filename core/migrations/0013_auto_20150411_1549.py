# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0012_auto_20150410_1819'),
    ]

    operations = [
        migrations.AlterField(
            model_name='albumfile',
            name='status',
            field=models.SmallIntegerField(choices=[(1, 'Active'), (2, 'Inactive'), (4, 'Processing'), (5, 'Error'), (3, 'Deleted')]),
        ),
    ]
