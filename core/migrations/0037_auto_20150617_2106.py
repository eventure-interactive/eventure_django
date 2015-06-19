# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import migrations


def add_albumtype_data(apps, schema_editor):
    AlbumType = apps.get_model("core", "AlbumType")
    AlbumType.objects.create(id=11, name='ALLMEDIA', description='All media album', is_virtual=True, is_deletable=False, sort_order=0)
    AlbumType.objects.create(id=12, name='LIKED', description='Liked by You album', is_virtual=True, is_deletable=False, sort_order=10)
    AlbumType.objects.create(id=3, name='SHARED', description='Shared by You album', is_virtual=True, is_deletable=False, sort_order=90)
    AlbumType.objects.create(id=4, name='DEFAULT_PROFILE', description='Default profile album', is_virtual=False, is_deletable=False, sort_order=30)
    AlbumType.objects.create(id=5, name='DEFAULT_EVENT', description='Default event album', is_virtual=False, is_deletable=False, sort_order=60)
    AlbumType.objects.create(id=8, name='BACKGROUND', description='Background album', is_virtual=False, is_deletable=False, sort_order=20)
    AlbumType.objects.create(id=9, name='LIFEEVENT', description='Life event album', is_virtual=False, is_deletable=False, sort_order=40)
    AlbumType.objects.create(id=0, name='CUSTOM', description='Custom album', is_virtual=False, is_deletable=True, sort_order=50)


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0036_merge'),
    ]

    operations = [
        migrations.RunPython(add_albumtype_data),
    ]
