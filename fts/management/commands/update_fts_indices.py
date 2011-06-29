from django.core.management.base import NoArgsCommand
from django.db import connections, router, transaction, models, DEFAULT_DB_ALIAS
import fts

class Command(NoArgsCommand):
    help = 'update FTS indices'

    def handle_noargs(self, **options):
        manifest = dict((app.__name__.split('.')[-2], [m for m in models.get_models(app)]) for app in models.get_apps())
        for app_name, model_list in manifest.items():
            for model in model_list:
                if not issubclass(model, fts.SearchableModel):
                    continue
                print "Processing %s.%s model" % (app_name, model._meta.object_name)
                model._search_manager.update_index()

