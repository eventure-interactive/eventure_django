# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0026_auto_20150504_2120'),
    ]

    operations = [
        migrations.CreateModel(
            name='SentNotification',
            fields=[
                ('id', models.AutoField(primary_key=True, auto_created=True, verbose_name='ID', serialize=False)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('recipients', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='sentnotifications')),
            ],
        ),
    ]
