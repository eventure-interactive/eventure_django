# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_auto_20150403_1245'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlbumFile',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('file_url', models.URLField()),
                ('width', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField()),
                ('size_bytes', models.PositiveIntegerField()),
                ('file_type', models.PositiveSmallIntegerField(choices=[(1, 'PHOTO'), (2, 'VIDEO')])),
                ('status', models.SmallIntegerField(choices=[(1, 'Active'), (2, 'Inactive'), (3, 'Deleted')])),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('albums', models.ManyToManyField(to='core.Album', related_name='albumfiles')),
                ('owner', models.ForeignKey(to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Thumbnail',
            fields=[
                ('id', models.AutoField(serialize=False, primary_key=True, auto_created=True, verbose_name='ID')),
                ('file_url', models.URLField()),
                ('size_type', models.PositiveSmallIntegerField(choices=[(48, 'SIZE_48'), (100, 'SIZE_100'), (144, 'SIZE_144'), (180, 'SIZE_180'), (205, 'SIZE_205'), (610, 'SIZE_610'), (960, 'SIZE_960')])),
                ('width', models.PositiveIntegerField()),
                ('height', models.PositiveIntegerField()),
                ('size_bytes', models.PositiveIntegerField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
                ('album', models.ForeignKey(to='core.Album', related_name='thumbnails')),
            ],
            options={
                'ordering': ('size_type',),
            },
        ),
    ]
