# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0023_account_profile_albumfile'),
    ]

    operations = [
        migrations.AddField(
            model_name='albumfile',
            name='s3_bucket',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='albumfile',
            name='s3_key',
            field=models.CharField(max_length=255, null=True),
        ),
        migrations.AlterUniqueTogether(
            name='albumfile',
            unique_together=set([('s3_bucket', 's3_key'), ('tmp_filename', 'tmp_hostname')]),
        ),
    ]
