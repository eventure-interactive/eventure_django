from collections import namedtuple
from datetime import datetime
from pytz import utc
import requests

from django.db import transaction
from core.models import Account

DBValue = namedtuple('DBValue', ('field_name', 'value'))


class ConvertMixin(object):

    def _convert_solr_field(self, solr_field, doc):
        "Find solr_field in doc, convert, and return the a DBValue (or None)."
        field_name = self.mapping[solr_field]
        if field_name is None:
            return None

        if callable(field_name):
            # calling map_value should return a DBValue or None
            return field_name(doc)

        field = self.model._meta.get_field(field_name)
        field_type = field.get_internal_type()
        solr_value = doc.get(solr_field)
        if field_type == 'DateTimeField' and solr_value:
            return DBValue(field_name, self._convert_date(solr_value))

        if (field_type in {'CharField', 'TextField'}) and solr_value is None and not field.null:
            # convert to empty string
            return DBValue(field_name, '')

        return DBValue(field_name, solr_value)

    def _convert_date(self, datestr):
        "Convert datestr to a datetime object with a UTC timezone."
        naive_dt = datetime.strptime(datestr, self.solr_date_fmt)
        return utc.localize(naive_dt)

    def get_account_id_fn(self, solr_fieldname="AccountID", model_fieldname="account_id"):
        "Return a function that provides a DBValue using solr_fieldname and model_fieldname for a given Solr doc."

        def fn(doc, sfieldname=solr_fieldname, mfieldname=model_fieldname):
            account_id = None
            solr_id = doc.get(sfieldname)
            if solr_id:
                acct = Account.objects.filter(solr_id=solr_id).first()
                if acct:
                    account_id = acct.id
            return DBValue(mfieldname, account_id)

        return fn


class BaseConverter(ConvertMixin):
    """Base class for Converters that migrate cores from Solr to Django.

    Sub-classes need to modify the following:

    - mapping : a Solr property to django property dictionary.
        - the key is a string that represents the solr property name
        - the value can be either
            - A string [Mapped directly to the django model with that field name]
            - A callable [Called with the entire document as the sole parameter. Should return a DBValue or None]
            - None [No direct action, but field is needed in callable logic]
    - solr_core : String representing the Solr core name
    - model : The Django model
    """

    mapping = dict()
    solr_core = 'TBD'
    model = object()

    # Typically wouldn't have to change the following properties
    solr_date_fmt = "%Y-%m-%dT%H:%M:%SZ"
    solr_query = "*:*"
    MAX_ROWS = 200000

    def __init__(self, solr_host='devsolrdb1.eventure.com', solr_port=8983):
        self.solr_host = solr_host
        self.solr_port = solr_port
        self.do_save = True  # Save to django db if true.
        super().__init__()

    def get_solr_docs(self):
        params = {
            'q': self.solr_query,
            'rows': self.MAX_ROWS,
            'fl': ','.join(self.mapping.keys()),
            'wt': 'json'
        }

        url = "http://{host}:{port}/solr/{core}/select".format(
            host=self.solr_host,
            port=self.solr_port,
            core=self.solr_core)
        r = requests.get(url, params=params)

        if r.status_code != 200:
            raise ValueError('unexpected status code {}, text: {}'.format(r.status_code, r.text))

        response = r.json()['response']
        if response['numFound'] >= self.MAX_ROWS:
            raise ValueError('Too many rows returned (got {})'.format(response['numFound']))

        return response['docs']

    @transaction.atomic
    def migrate(self):
        for doc in self.get_solr_docs():
            # acct = Account()
            values = self.convert_doc(doc)

            model_obj = self.model(**values)
            model_obj._do_save = True
            self.pre_save(model_obj)
            if model_obj._do_save:
                model_obj.save()
            else:
                print('Skipped saving {} with values {}'.format(model_obj, values))

    def convert_doc(self, doc):
        "Convert a solr doc to a dict of values that can be applied to a model class."
        values = {}
        for solr_field in self.mapping.keys():
            dbval = self._convert_solr_field(solr_field, doc)
            if dbval:
                values[dbval.field_name] = dbval.value

        return values

    def pre_save(self, model_obj):
        "Implement this function to do any necessary object manipulation or validation before saving model_obj."
        pass
