# -*- coding: utf-8 -*-
from __future__ import unicode_literals

from django.db import models, migrations
from django.conf import settings


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0038_auto_20150709_1512'),
    ]

    operations = [
        migrations.RunSQL(sql="""INSERT INTO core_accountsettings(account_id, email_rsvp_updates, email_social_activity,
                                                email_promotions, default_event_privacy, created, modified)
                                 SELECT a.id, true, true, true, 2, current_timestamp, current_timestamp FROM core_account a
                                """,
                          reverse_sql="DELETE from core_accountsettings"),
    ]
