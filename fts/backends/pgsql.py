"Pgsql Fts backend"

from django.db import transaction
from fts.backends.base import InvalidFtsBackendError
from fts.backends.base import BaseClass, BaseModel, BaseManager, BaseQueryset
from django.db import models
from pprint import pprint

LANGUAGES = {
    '' : 'simple',
    'da' : 'danish',
    'nl' : 'dutch',
    'en' : 'english',
    'fi' : 'finnish',
    'fr' : 'french',
    'de' : 'german',
    'hu' : 'hungarian',
    'it' : 'italian',
    'no' : 'norwegian',
    'pt' : 'portuguese',
    'ro' : 'romanian',
    'ru' : 'russian',
    'es' : 'spanish',
    'sv' : 'swedish',
    'tr' : 'turkish',
}

class _VectorField(models.Field):
    def __init__(self, *args, **kwargs):
        kwargs['null'] = True
        kwargs['editable'] = False
        kwargs['serialize'] = False
        super(_VectorField, self).__init__(*args, **kwargs)
    
    def db_type(self, connection=None):
        return 'tsvector'

class SearchClass(BaseClass):
    def __init__(self, server, params):
        from django.conf import settings
        
        if not (settings.DATABASE_ENGINE in ['postgresql', 'postgresql_psycopg2'] or settings.DATABASES['default']['ENGINE'].find('postgresql') != -1 or settings.DATABASES['default']['ENGINE'].find('postgis') != -1):
            raise InvalidFtsBackendError("PostgreSQL with tsearch2 support is needed to use the pgsql FTS backend")
        
        self.backend = 'pgsql'

class SearchQueryset(BaseQueryset):
    def __init__(self, **kwargs):
        super(SearchQueryset, self).__init__(**kwargs)
        self.language = LANGUAGES[self.language_code]
        self._vector_field_cache = None
        
    def _vector_field(self):
        """
        Returns the _VectorField defined for this manager's model. There must be exactly one _VectorField defined.
        """
        if self._vector_field_cache is not None:
            return self._vector_field_cache
        
        vectors = [f for f in self.model._meta.fields if isinstance(f, _VectorField)]
        
        if len(vectors) != 1:
            raise ValueError('There must be exactly 1 _VectorField defined for the %s model.' % self.model._meta.object_name)
            
        self._vector_field_cache = vectors[0]
        
        return self._vector_field_cache
    vector_field = property(_vector_field)
    
    def _vector_sql(self, field, weight=None):
        """
        Returns the SQL used to build a tsvector from the given (django) field name.
        """
        if weight is None:
            weight = self.default_weight
        f = self.model._meta.get_field(field)
        return "setweight(to_tsvector('%s', coalesce(\"%s\",'')), '%s')" % (self.language, f.column, weight)
    
    @transaction.commit_on_success
    def update_index(self, pk=None):
        from django.db import connection
        # Build a list of SQL clauses that generate tsvectors for each specified field.
        clauses = []
        if self.fields is None:
            self.fields = self._find_text_fields()
            
        if isinstance(self.fields, (list,tuple)):
            for field in self.fields:
                clauses.append(self._vector_sql(field))
        else:
            for field, weight in self.fields.items():
                clauses.append(self._vector_sql(field, weight))
        
        vector_sql = ' || '.join(clauses)
        
        where = ''
        # If one or more pks are specified, tack a WHERE clause onto the SQL.
        if pk is not None:
            if isinstance(pk, (list,tuple)):
                ids = ','.join([str(v) for v in pk])
                where = ' WHERE "%s" IN (%s)' % (self.model._meta.pk.column, ids)
            else:
                where = ' WHERE "%s" = %s' % (self.model._meta.pk.column, pk)
        sql = 'UPDATE "%s" SET "%s" = %s%s' % (self.model._meta.db_table, self.vector_field.column, vector_sql, where)
        cursor = connection.cursor()
        transaction.set_dirty()
        cursor.execute(sql)
    
    def search(self, query, **kwargs):
        """
        Returns a queryset after having applied the full-text search query. If rank_field
        is specified, it is the name of the field that will be put on each returned instance.
        When specifying a rank_field, the results will automatically be ordered by -rank_field.
        
        For possible rank_normalization values, refer to:
        http://www.postgresql.org/docs/8.3/static/textsearch-controls.html#TEXTSEARCH-RANKING
        """
        rank_field = kwargs.get('rank_field')
        rank_normalization = kwargs.get('rank_normalization', 32)
        highlight_field = kwargs.get('highlight_field')
        
        ts_query = "plainto_tsquery('%s',%%s)" % (self.language, )
        where = "\"%s\".\"%s\" @@ %s" % (self.model._meta.db_table, self.vector_field.column, ts_query)
        params = [unicode(query)]
        
        select = {}
        select_params = []
        order = []
        if rank_field is not None:
            select[rank_field] = 'ts_rank("%s"."%s", %s, %d)' % (self.model._meta.db_table, self.vector_field.column, ts_query, rank_normalization)
            select_params += [unicode(query)]
            order = ['-%s' % rank_field]
        if highlight_field is not None:
            select[highlight_field + '_highlight'] = 'ts_headline(\'%s\', "%s"."%s", %s, \'StartSel=<span>, StopSel=</span>, HighlightAll=TRUE\')' % (self.language, self.model._meta.db_table, highlight_field, ts_query)
            select_params += [unicode(query)]
        #pprint(select)
        
        return self.all().distinct().extra(select=select, select_params=select_params, where=[where], params=params, order_by=order)
    
class SearchManager(BaseManager):
    def get_query_set(self): 
        return SearchQueryset(model=self.model, fields=self.fields, default_weight=self.default_weight, language_code=self.language_code)


class SearchableModel(BaseModel):
    class Meta:
        abstract = True

    search_index = _VectorField()

    search_objects = SearchManager()
