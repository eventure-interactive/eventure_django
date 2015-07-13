from base64 import b64decode

from django.contrib.auth.hashers import make_password
from core.models import Account

from .base import BaseConverter, DBValue


def convert_name(doc):
    if doc.get('Name'):
        return DBValue('name', doc['Name'])

    fname = doc.get('FirstName', '')
    lname = doc.get('LastName', '')

    name = "{} {}".format(fname, lname)
    return DBValue('name', name.strip())


def convert_password(doc):
    b64_pw = doc['Password'].split('-zW2eh')[0]
    # print(b64_pw)
    clear_pw = b64decode(b64_pw, validate=True).decode('utf8')
    return DBValue('password', make_password(clear_pw))


def convert_phone(doc):
    phone = doc.get('Phone')
    all_phone = doc.get('AllPhoneNumbers', [])

    if phone and all_phone:
        if len(all_phone) > 1:
            raise ValueError('Too many phones, got: {}'.format(all_phone))
        if all_phone[0] != phone:
            raise ValueError('have phone: {}, all_phone: {}'.format(phone, all_phone))

    val = phone or (all_phone and all_phone[0]) or None

    if val:
        try:
            val = Account.normalize_phone(val)
        except ValueError:
            print('got a bad phone number for doc {}'.format(doc))
            val = None

    return DBValue('phone', val)


def convert_email(doc):
    email = doc.get('Email')
    all_email = doc.get('AllEmails')

    if email and all_email:
        if len(all_email) > 1:
            raise ValueError('Too many emails, got: {}'.format(all_phone))
        if all_email[0].strip() != email.strip():
            raise ValueError('have email: {}, all_email: {}'.format(email, all_email))

    val = email or (all_email and all_email[0]) or None

    return DBValue('email', val.strip())


# solr field to Django model field
class AccountConverter(BaseConverter):

    mapping = {
        'ID': 'solr_id',
        'Phone': convert_phone,
        'AllPhoneNumbers': None,
        'Email': convert_email,
        'AllEmails': None,
        'Status': 'status',
        'ShowWelcomePage': 'show_welcome_page',
        # 'InviteID': 'invite_id',
        # 'Location': 'location',
        # 'About': 'about',
        # 'Work': 'work',
        # 'College': 'college',
        # 'HighSchool': 'high_school',
        'CreatedDate': 'date_joined',
        'UpdatedDate': 'modified',
        'LastLoginDate': 'last_login',
        'FirstName': None,
        'LastName': None,
        'Name': convert_name,
        'Password': convert_password,
    }

    solr_core = "Account"
    model = Account

    def pre_save(self, obj):
        "Perform any necessary object manipulation or validation here."

        if obj.solr_id == '00039930afd213eef03111e4895a12c71eb3bb6d' and obj.email == 'tidushue@gmail.com':
            # fix duplicate email issue
            obj.email = None
        elif obj.solr_id == '000175155a210b92108b11e5895a12c71eb3bb6d' and obj.email == 'testthree@eventure.com':
            obj.email = None

        if not (obj.email or obj.phone):
            print(obj)
            raise ValueError("Account does not have an email or phone.")
