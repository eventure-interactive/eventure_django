from .base import BaseConverter, DBValue
from core.models import Event, EventGuest


class EventConverter(BaseConverter):

    solr_core = "Plan"
    model = Event

    solr_query = "ID:0001*"

    def __init__(self, *args, **kw):
        self.mapping = {
            'ID': 'solr_id',
            'AccountID':  self.get_account_id_fn(model_fieldname="owner_id"),
            'Title': 'title',
            'Description': 'description',
            'Location': 'location',
            'StartDate': 'start',
            'EndDate': 'end',
            'CreatedDate': 'created',
            'UpdatedDate': 'modified',
        }
        super().__init__(*args, **kw)

    def pre_save(self, obj):
        if not obj.owner_id:
            print("No owner_id, skipping...")
            obj._do_save = False


def get_event_id(doc):
    solr_id = doc.get('PlanID')
    event_id = None
    if solr_id:
        event = Event.objects.filter(solr_id=solr_id).first()
        if event:
            event_id = event.id

    return DBValue('event_id', event_id)


class EventGuestConverter(BaseConverter):

    solr_core = "PlanGuests"
    model = EventGuest

    def __init__(self, *args, **kw):
        self.mapping = {
            'ID': 'solr_id',
            'AccountID': self.get_account_id_fn(model_fieldname="guest_id"),
            'PlanID': get_event_id,
            'Response': 'rsvp',
        }
        super().__init__(*args, **kw)

    def pre_save(self, obj):
        if not obj.guest_id:
            print('No guest_id, skipping...')
            obj._do_save = False
        elif not obj.event_id:
            print('No event_id found, skipping...')
            obj._do_save = False
