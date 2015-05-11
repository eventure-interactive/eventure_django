# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0031_merge'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='account',
            name='profile_image',
        ),
        # migrations.AlterUniqueTogether(
        #     name='albumfile',
        #     unique_together=set([]),
        # ),
        # migrations.RemoveField(
        #     model_name='albumfile',
        #     name='tmp_filename',
        # ),
        # migrations.RemoveField(
        #     model_name='albumfile',
        #     name='tmp_hostname',
        # ),
    ]
