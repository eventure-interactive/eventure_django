# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0011_album_event'),
    ]

    operations = [
        migrations.AlterField(
            model_name='album',
            name='event',
            field=models.ForeignKey(null=True, default=None, blank=True, related_name='albums', to='core.Event'),
        ),
    ]
