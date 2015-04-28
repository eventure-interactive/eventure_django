# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_auto_20150428_1854'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='eventguest',
            unique_together=set([]),
        ),
    ]
