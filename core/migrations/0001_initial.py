# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import django.utils.timezone
import core.models


class Migration(migrations.Migration):

    dependencies = [
        ('auth', '0006_require_contenttypes_0002'),
    ]

    operations = [
        migrations.CreateModel(
            name='Account',
            fields=[
                ('id', models.AutoField(serialize=False, auto_created=True, primary_key=True, verbose_name='ID')),
                ('phone', models.CharField(max_length=40, unique=True)),
                ('name', models.CharField(max_length=255)),
                ('password', models.CharField(max_length=128, verbose_name='password')),
                ('status', models.SmallIntegerField(choices=[(-1, 'Contact'), (0, 'Signed Up'), (2, 'Deleted'), (3, 'Active'), (5, 'Forcefully Inactivated')], default=0)),
                ('show_welcome_page', models.BooleanField(default=True)),
                ('is_superuser', models.BooleanField(help_text='Designates that this user has all permissions without explicitly assigning them.', default=False, verbose_name='superuser status')),
                ('is_staff', models.BooleanField(default=False)),
                ('groups', models.ManyToManyField(to='auth.Group', help_text='The groups this user belongs to. A user will get all permissions granted to each of their groups.', related_name='user_set', blank=True, related_query_name='user', verbose_name='groups')),
                ('user_permissions', models.ManyToManyField(to='auth.Permission', help_text='Specific permissions for this user.', related_name='user_set', blank=True, related_query_name='user', verbose_name='user permissions')),
                ('last_login', models.DateTimeField(blank=True, null=True, verbose_name='last login')),
                ('date_joined', models.DateTimeField(default=django.utils.timezone.now)),
                ('modified', models.DateTimeField(auto_now=True)),
            ],
            options={
                'abstract': False,
            },
            managers=[
                ('objects', core.models.AccountUserManager()),
            ],
        ),
    ]
