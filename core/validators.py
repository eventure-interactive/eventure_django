from django.core.exceptions import ValidationError
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException


def validate_phone_number(value):
    "Validates a phone number is a possible number and is in E164 format."

    try:
        p = phonenumbers.parse(value)
    except NumberParseException:
        raise ValidationError("{} does not appear to be a valid phone number".format(value))

    if value != phonenumbers.format_number(p, phonenumbers.PhoneNumberFormat.E164):
        raise ValidationError("{} needs to be in E164 format".format(value))

    if not phonenumbers.is_possible_number(p):
        raise ValidationError('{} does not appear to be a valid phone number'.format(value))
