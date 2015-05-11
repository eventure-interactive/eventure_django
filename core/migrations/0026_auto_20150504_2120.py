# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0025_auto_20150428_1900'),
    ]

    operations = [
        migrations.AddField(
            model_name='account',
            name='email',
            field=models.CharField(max_length=100, unique=True, validators=[django.core.validators.EmailValidator()], null=True),
        ),
        # migrations.AddField(
        #     model_name='account',
        #     name='profile_image',
        #     field=models.ForeignKey(to='core.AlbumFile', null=True),
        # ),
        migrations.AddField(
            model_name='account',
            name='profile_image',
            field=models.ForeignKey(to='core.AlbumFile', null=True),
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
