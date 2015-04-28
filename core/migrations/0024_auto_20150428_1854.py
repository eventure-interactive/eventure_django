# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_auto_20150427_1646'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='eventguest',
            unique_together=set([('guest', 'event')]),
        ),
    ]
