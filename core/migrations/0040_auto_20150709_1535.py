# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0039_manual_accountsettings'),
    ]

    operations = [
        migrations.AlterField(
            model_name='accountsettings',
            name='default_event_privacy',
            field=models.PositiveSmallIntegerField(choices=[(1, 'Public'), (2, 'Private')], default=2),
        ),
    ]
