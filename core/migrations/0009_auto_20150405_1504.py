# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0008_auto_20150404_2246'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='album',
            options={'ordering': ('album_type__sort_order',)},
        ),
    ]
