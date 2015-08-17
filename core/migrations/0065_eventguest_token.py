# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import uuid


def generate_uuid(apps, schema_editor):
    EventGuest = apps.get_model('core', 'EventGuest')
    for eg in EventGuest.objects.all().iterator():
        eg.token = uuid.uuid4()
        eg.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0064_auto_20150814_2123'),
    ]

    operations = [
        migrations.AddField(
            model_name='eventguest',
            name='token',
            field=models.UUIDField(unique=True, null=True),
            preserve_default=False
        ),
        migrations.RunPython(
            generate_uuid
        ),
        migrations.AlterField(
            model_name='eventguest',
            name='token',
            field=models.UUIDField(editable=False, unique=True, default=uuid.uuid4),
            preserve_default=True,
        )
    ]
