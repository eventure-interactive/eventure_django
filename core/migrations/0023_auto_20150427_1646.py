# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0022_event_privacy'),
    ]

    operations = [
        
        migrations.AlterUniqueTogether(
            name='eventguest',
            unique_together=set([]),
        ),
    ]
