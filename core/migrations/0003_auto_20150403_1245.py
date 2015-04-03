# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_auto_20150403_0145'),
    ]

    operations = [
        migrations.CreateModel(
            name='Album',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, verbose_name='ID', serialize=False)),
                ('name', models.CharField(max_length=255)),
                ('description', models.TextField(blank=True)),
                ('status', models.SmallIntegerField(choices=[(1, 'Active'), (2, 'Inactive'), (3, 'Deleted')], default=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AlterModelOptions(
            name='albumtype',
            options={'ordering': ('sort_order',)},
        ),
        migrations.AddField(
            model_name='album',
            name='album_type',
            field=models.ForeignKey(to='core.AlbumType'),
        ),
        migrations.AddField(
            model_name='album',
            name='owner',
            field=models.ForeignKey(to=settings.AUTH_USER_MODEL, related_name='albums'),
        ),
    ]
