# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0063_event_featured_albumfile'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='stream',
            name='content_type',
        ),
        migrations.RemoveField(
            model_name='stream',
            name='recipient',
        ),
        migrations.RemoveField(
            model_name='stream',
            name='sender',
        ),
        migrations.DeleteModel(
            name='Stream',
        ),
    ]
