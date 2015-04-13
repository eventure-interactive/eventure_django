# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0009_auto_20150405_1504'),
    ]

    operations = [
        migrations.AddField(
            model_name='albumfile',
            name='description',
            field=models.TextField(blank=True),
        ),
        migrations.AddField(
            model_name='albumfile',
            name='media_created',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='albumfile',
            name='name',
            field=models.CharField(blank=True, max_length=255),
        ),
        migrations.AlterField(
            model_name='albumfile',
            name='status',
            field=models.SmallIntegerField(choices=[(1, 'Active'), (2, 'Inactive'), (4, 'Processing'), (3, 'Deleted')]),
        ),
    ]
