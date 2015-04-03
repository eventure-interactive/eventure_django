# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.core.validators


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='AlbumType',
            fields=[
                ('id', models.PositiveIntegerField(serialize=False, primary_key=True)),
                ('name', models.CharField(unique=True, max_length=40)),
                ('description', models.CharField(max_length=80)),
                ('sort_order', models.PositiveSmallIntegerField()),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
        ),
        migrations.AlterModelOptions(
            name='account',
            options={'ordering': ('name',)},
        ),
        migrations.AlterField(
            model_name='account',
            name='phone',
            field=models.CharField(unique=True, max_length=40, validators=[django.core.validators.RegexValidator('\\+?[0-9(). -]')]),
        ),
    ]
