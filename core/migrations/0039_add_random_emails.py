# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
import string
import random


def id_generator(size=6, chars=string.ascii_uppercase + string.digits):
    return ''.join(random.choice(chars) for _ in range(size))


def gen_email(apps, schema_editor):
    Account = apps.get_model('core', 'Account')
    for row in Account.objects.all():
        row.email = id_generator() + '@eventure.com'
        row.save()

# Intermediate data migration
# Generate random unique emails for all accounts so it can be made non-null unique in the next migration
class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_auto_20150708_1701'),
    ]

    operations = [
        # omit reverse_code=... if you don't want the migration to be reversible.
        migrations.RunPython(gen_email, reverse_code=migrations.RunPython.noop),
    ]
