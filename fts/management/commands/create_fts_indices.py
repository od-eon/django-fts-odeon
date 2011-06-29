from django.core.management.base import NoArgsCommand
from django.db import connections, router, transaction, models, DEFAULT_DB_ALIAS
import fts

class Command(NoArgsCommand):
    help = 'create FTS indices'

    def handle_noargs(self, **options):
        manifest = dict((app.__name__.split('.')[-2], [m for m in models.get_models(app)]) for app in models.get_apps())
        cursor = connections[DEFAULT_DB_ALIAS].cursor()
        for app_name, model_list in manifest.items():
            for model in model_list:
                if not issubclass(model, fts.SearchableModel):
                    continue
                table = model._meta.db_table
                try:
                    cursor.execute('CREATE INDEX "%s_search_index" ON "%s" USING gin("search_index")' % (table, table))
                    transaction.commit_unless_managed()
                except:
                    continue
                print "Creating FTS index for %s.%s" % (app_name, model._meta.object_name)


