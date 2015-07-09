# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0040_auto_20150709_1535'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='accountsettings',
            options={'verbose_name_plural': 'account settings'},
        ),
    ]
