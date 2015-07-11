# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0047_commchannel_validation_token'),
    ]

    operations = [
        migrations.AlterField(
            model_name='commchannel',
            name='validation_token',
            field=models.UUIDField(default=uuid.uuid4, unique=True),
        ),
    ]
