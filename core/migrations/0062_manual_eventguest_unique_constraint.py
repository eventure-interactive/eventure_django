"""Add a unique constraint to core_eventguest on event, account.

Doing this manually because django rest doesn't play well with it when declared in
the model.
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [("core", "0061_eventguest_name")]

    operations = [
        migrations.RunSQL("ALTER TABLE core_eventguest ADD CONSTRAINT eventguest_unique UNIQUE (event_id, guest_id)"),
    ]
