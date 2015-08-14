from collections import namedtuple
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
import phonenumbers
from phonenumbers.phonenumberutil import NumberParseException
import re


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


ParsedEventGuest = namedtuple('ParsedEventGuest', ('guest_name', 'value', 'type'))


class EventGuestValidator(object):
    """Validator for New Account Guests"""

    # Can match:
    # Guy Floove <+16545551212>
    # Lass McApple <plewis@something.com>
    # plewis@example.com
    # +16572001111

    def __init__(self, Account):  # Account is the core.models.Account class
        self.name_re = re.compile(r'(?P<name>.*)\s*<(?P<channel_address>.*)>')
        self.Account = Account

    def __call__(self, value):
        if re.match(r'account_id:\d+', value):
            account_id = value.replace("account_id:", "")
            self._validate_account_id(account_id)
            return ParsedEventGuest(guest_name="", value=account_id, type="account")

        peg = None
        name_match = self.name_re.match(value)
        if name_match is not None:
            addr = name_match.group("channel_address")
            name = name_match.group("name").rstrip()
            if "@" in addr:
                validate_email(addr)
                peg = ParsedEventGuest(guest_name=name, value=addr, type='email')
            else:
                validate_phone_number(addr)
                peg = ParsedEventGuest(guest_name=name, value=addr, type='phone')
        else:
            # No name, just the raw channel
            if "@" in value:
                validate_email(value)
                peg = ParsedEventGuest(guest_name="", value=value, type='email')
            else:
                validate_phone_number(value)
                peg = ParsedEventGuest(guest_name="", value=value, type='phone')

        return peg

    def _validate_account_id(self, account_id):
        try:
            acct = self.Account.actives.get(pk=account_id)
        except self.Account.DoesNotExist:
            raise ValidationError("account_id {} does not exist".format(account_id))
