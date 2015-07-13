from django.contrib.gis.db import models


class EmptyStringToNoneField(models.CharField):
    "Convert an empty string field to NULL."

    def get_prep_value(self, value):
        if value == '':
            return None
        return value
