from django.core.management.base import BaseCommand, CommandError
from django.apps import apps
from . import _solrmap


class Command(BaseCommand):

    help = 'Migrate all data from Solr to Django'

    converters = {
        'Account': _solrmap.AccountConverter,
        'Event': _solrmap.EventConverter,
        'EventGuest': _solrmap.EventGuestConverter,
    }

    def add_arguments(self, parser):
        parser.add_argument('model', nargs='+')
        parser.add_argument('--solrhost', default='devsolrdb1.eventure.com',
                            help="Solr host name. Default: devsolrdb1.eventure.com")
        parser.add_argument('--solrport', default=8983, type=int,
                            help="Solr port. Default: 8983")

    def handle(self, *args, **options):
        to_migrate = []
        # self.stdout.write('Got args {}'.format(args))
        # self.stdout.write('Got options {}'.format(options))

        for modelname in options['model']:
            # self.stdout.write('Got modelname {}'.format(modelname))
            if modelname not in self.converters:
                raise NotImplementedError("Don't know how to migrate model {}".format(modelname))
            to_migrate.append(modelname)
            # self.stdout.write('to_migrate now {}'.format(", ".join(str(tm) for tm in to_migrate)))

        for modelname in to_migrate:
            converter = self.converters[modelname](options['solrhost'], options['solrport'])
            converter.migrate()

        # self.stdout.write('To migrate: {}'.format(", ".join(str(dir(tm)) for tm in to_migrate)))
