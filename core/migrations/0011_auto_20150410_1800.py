# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0010_auto_20150410_1701'),
    ]

    operations = [
        # migrations.AddField(
        #     model_name='albumfile',
        #     name='tmp_filename',
        #     field=models.CharField(null=True, max_length=255),
        # ),
        # migrations.AddField(
        #     model_name='albumfile',
        #     name='tmp_hostname',
        #     field=models.CharField(null=True, max_length=255),
        # ),
        # migrations.AlterUniqueTogether(
        #     name='albumfile',
        #     unique_together=set([('tmp_filename', 'tmp_hostname')]),
        # ),
    ]
