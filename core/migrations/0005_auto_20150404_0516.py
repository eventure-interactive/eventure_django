# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_albumfile_thumbnail'),
    ]

    operations = [
        migrations.AlterField(
            model_name='albumfile',
            name='file_url',
            field=models.URLField(unique=True),
        ),
        migrations.AlterField(
            model_name='thumbnail',
            name='file_url',
            field=models.URLField(unique=True),
        ),
        migrations.AlterUniqueTogether(
            name='thumbnail',
            unique_together=set([('album', 'size_type')]),
        ),
    ]
