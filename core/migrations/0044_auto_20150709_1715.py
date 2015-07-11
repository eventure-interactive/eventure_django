# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0043_auto_20150709_1654'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='account',
            options={'ordering': ('email',)},
        ),
        migrations.AlterField(
            model_name='account',
            name='name',
            field=models.CharField(null=True, blank=True, max_length=255),
        ),
    ]
