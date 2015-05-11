# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('contenttypes', '0002_remove_content_type_name'),
        ('core', '0027_auto_20150507_1846'),
    ]

    operations = [
        migrations.CreateModel(
            name='InAppNotification',
            fields=[
                ('id', models.AutoField(primary_key=True, verbose_name='ID', serialize=False, auto_created=True)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('notification_type', models.SmallIntegerField(choices=[(1, 'EVENT_INVITE')])),
                ('object_id', models.PositiveIntegerField()),
                ('content_type', models.ForeignKey(to='contenttypes.ContentType')),
                ('recipients', models.ManyToManyField(to=settings.AUTH_USER_MODEL)),
                ('sender', models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='ntfs')),
            ],
        ),
        migrations.RemoveField(
            model_name='sentnotification',
            name='content_type',
        ),
        migrations.RemoveField(
            model_name='sentnotification',
            name='recipients',
        ),
        migrations.RemoveField(
            model_name='sentnotification',
            name='sender',
        ),
        migrations.DeleteModel(
            name='SentNotification',
        ),
    ]
