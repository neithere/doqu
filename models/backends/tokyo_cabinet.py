# -*- coding: utf-8 -*-
#
#    Models is a framework for mapping Python classes to semi-structured data.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of Models.
#
#    Models is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Models is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Models.  If not, see <http://gnu.org/licenses/>.

"""
>>> import os
>>> import models
>>> DB_SETTINGS = {
...     'backend': 'models.backends.tokyo_cabinet',
...     'kind': 'TABLE',
...     'path': '_tc_test.tct',
... }
>>> assert not os.path.exists(DB_SETTINGS['path']), 'test database must not exist'
>>> db = models.get_storage(DB_SETTINGS)
>>> class Person(models.Model):
...     name = models.Property()
...     __unicode__ = lambda self: self.name
>>> Person.query(db)    # the database is expected to be empty
[]
>>> db.connection.put('john', {'name': 'John'})
>>> db.connection.put('mary', {'name': 'Mary'})
>>> q = Person.query(db)
>>> q
[<Person John>, <Person Mary>]
>>> q.where(name__matches='^J')
[<Person John>]
>>> q    # the original query was not modified by the descendant
[<Person John>, <Person Mary>]
>>> os.unlink(DB_SETTINGS['path'])

"""


from models.backends.base import BaseStorage, BaseQuery
from models.utils.iterators import CachedIterator

try:
    import tc
except ImportError:
    raise ImportError('Tokyo Cabinet backend requires package "tc". Most recent '
                      'version from github.com/rsms/tc/ is preferable.')

try:
    from pyrant.query import Condition
except ImportError:
    raise ImportError('Tokyo Cabinet backend requires package "pyrant".')

# TODO: use pyrant.query.Condition

DB_TYPES = {
    'BTREE': tc.BDB,    # 'B+ tree'
    'HASH':  tc.HDB,
    'TABLE': tc.TDB,
}

class Storage(BaseStorage):
    """
    :param path: relative or absolute path to the database file (e.g. `test.tct`)
    :param kind: storage flavour, one of: 'BTREE', 'HASH', 'TABLE' (default).
    """

    supports_nested_data = False

    def __init__(self, path, kind=None):
        self.path = path
        self.kind = kind or 'TABLE'
        assert self.kind in DB_TYPES
        ConnectionClass = DB_TYPES[self.kind]
        self.connection = ConnectionClass(path, tc.TDBOWRITER | tc.TDBOCREAT)

    def get(self, model, primary_key):
        """
        Returns model instance for given model and primary key.
        """
        data = self.connection.get(primary_key)
        return self._decorate(model, primary_key, data)

    def _generate_primary_key(self, model):
        # TODO
        raise NotImplementedError

    def save(self, model, data, primary_key=None):
        """
        Saves given model instance into the storage. Returns primary key.

        :param model: model class
        :param data: dict containing all properties to be saved
        :param primary_key: the key for given object; if undefined, will be
            generated

        Note that you must provide current primary key for a model instance which
        is already in the database in order to update it instead of copying it.
        """
        # sanitize data for Tokyo Cabinet:
        # None-->'None' is wrong, force None-->''
        for key in data:
            if data[key] is None:
                data[key] = ''

        primary_key = primary_key or self._generate_primary_key(model)

        self.connection.put(primary_key, data)

        # TODO: check if this is useful; if yes, include param "sync" in meth sig
        #if sync:
        #    storage.sync()

        return primary_key

    def get_query(self, model):
        return Query(storage=self, model=model)


class Query(CachedIterator):    # NOTE: not a subclass of BaseQuery -- maybe the latter is too fat?
    #
    # PYTHON MAGIC METHODS
    #

    # (see CachedIterator)

    #
    # PRIVATE METHODS
    #

    def _init(self, storage, model, conditions=None):
        self.storage = storage
        self.model = model
        self._conditions = conditions or []
        #self._iter = self._fresh_query.keys()    #storage.connection.query().keys()
        if self._iter is None:
            _query = self.storage.connection.query()
            for condition in self._conditions:
                _query = _query.filter(*condition.prepare())
            self._iter = iter(_query.keys())

    def _prepare_item(self, key):
        return self.storage.get(self.model, key)

    def _where(self, lookups, negate=False):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        new_conditions = [Condition(k, v, negate) for k, v in lookups]
        conditions = self._conditions + new_conditions
        return self.__class__(self.storage, self.model, conditions=conditions)

    #
    # PUBLIC API
    #

    def where(self, **conditions):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        return self._where(conditions.items())

    def where_not(self, **conditions):
        return self._where(conditions.items(), negate=True)

    def count(self):
        # NOTE: inefficient, but the library does not provide proper methods
        return len(self)

    ''' TODO
    def order_by(self, name):
        # introspect model and use numeric sorting if appropriate
        property = self.model._meta.props[name]
        numeric = property.python_type in (int, float)

        q = self._clone(self._query)
        q.order_by(name, numeric)
        return q
    '''

    ''' TODO
    def values(self, name):
        return self._query.values(name)
    '''

    ''' TODO
    def delete(self):
        """
        Deletes all records that match current query.
        """
        self._query.delete()
    '''
