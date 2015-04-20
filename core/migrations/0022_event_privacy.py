# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0021_merge'),
    ]

    operations = [
        migrations.AddField(
            model_name='event',
            name='privacy',
            field=models.SmallIntegerField(choices=[(1, 'Public'), (2, 'Private')], default=1),
        ),
    ]
