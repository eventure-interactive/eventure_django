# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0007_albumtype_is_deletable'),
    ]

    operations = [
        migrations.AddField(
            model_name='thumbnail',
            name='albumfile',
            field=models.ForeignKey(to='core.AlbumFile', related_name='thumbnails', default=0),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='thumbnail',
            name='size_type',
            field=models.PositiveSmallIntegerField(choices=[(48, 'SIZE_48'), (100, 'SIZE_100'), (144, 'SIZE_144'), (205, 'SIZE_205'), (320, 'SIZE_320'), (610, 'SIZE_610'), (960, 'SIZE_960')]),
        ),
        migrations.AlterUniqueTogether(
            name='thumbnail',
            unique_together=set([('albumfile', 'size_type')]),
        ),
        migrations.RemoveField(
            model_name='thumbnail',
            name='album',
        ),
    ]
