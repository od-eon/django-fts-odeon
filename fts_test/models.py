from django.db import models
import fts

class Blog(fts.SearchableModel):
    title = models.CharField(max_length=100)
    body = models.TextField()

    search_objects = fts.SearchManager(fields=('title', 'body')) # index both fields
    #search_objects = fts.SearchManager(fields=('title',)) # index only the title
    #search_objects = fts.SearchManager(fields=('body',)) # index only the body

    def __unicode__(self):
        return self.title

