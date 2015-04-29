# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0024_auto_20150427_2120'),
    ]

    operations = [
        migrations.AlterUniqueTogether(
            name='albumfile',
            unique_together=set([('s3_bucket', 's3_key')]),
        ),
        migrations.RemoveField(
            model_name='albumfile',
            name='tmp_filename',
        ),
        migrations.RemoveField(
            model_name='albumfile',
            name='tmp_hostname',
        ),
    ]
