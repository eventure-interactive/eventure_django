# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0052_googlecredentials'),
    ]

    operations = [
        migrations.AlterField(
            model_name='googlecredentials',
            name='credentials',
            field=core.models.MyCredentialsField(null=True),
        ),
    ]
