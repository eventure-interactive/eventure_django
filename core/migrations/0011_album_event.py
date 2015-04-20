# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_auto_20150406_1834'),
    ]

    operations = [
        migrations.AddField(
            model_name='album',
            name='event',
            field=models.ForeignKey(blank=True, related_name='albums', to='core.Event', null=True),
        ),
    ]
