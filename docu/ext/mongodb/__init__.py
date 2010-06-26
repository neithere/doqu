# -*- coding: utf-8 -*-
#
#    Docu is a lightweight schema/query framework for document databases.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of Docu.
#
#    Docu is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Docu is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Docu.  If not, see <http://gnu.org/licenses/>.

"""
MongoDB extension
=================

A storage/query backend for MongoDB.

:status: experimental
:database: `MongoDB`_
:dependencies: `pymongo`_
:suitable for: general purpose

  .. _MongoDB: http://mongodb.org
  .. _pymongo: http://api.mongodb.org/python

.. warning:: this module is not intended for production, it's just a (working)
    example. Patches, improvements, rewrites are welcome.

"""

from docu.backend_base import BaseStorageAdapter, BaseQueryAdapter
from docu.utils.data_structures import CachedIterator

try:
    import pymongo
except ImportError:  # pragma: nocover
    raise ImportError('Package "pymongo" must be installed to enable MongoDB'
                      ' backend.')

from converters import converter_manager
from lookups import lookup_manager


class StorageAdapter(BaseStorageAdapter):
    """
    :param host:
    :param port:
    :param database:
    :param collection:
    """
    supports_nested_data = True

    converter_manager = converter_manager
    lookup_manager = lookup_manager

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    def __contains__(self, key):
        return bool(self.connection.find({'_id': key}).count())

    def __iter__(self):
        return iter(self.connection.find(spec={}, fields={'_id': 1}))

    def __init__(self, host='127.0.0.1', port=27017, database='default',
                 collection='default'):
        self.host = host
        self.port = port
        self.database_name = database
        self.collection_name = collection
        self._mongo_connection = pymongo.Connection(host, port)
        self._mongo_database = self._mongo_connection[database]
        self._mongo_collection = self._mongo_database[collection]
        self.connection = self._mongo_collection

    def __len__(self):
        return len(self.connection)

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _decorate(self, model, primary_key, raw_data):
        data = dict(raw_data)
        key = data.pop('_id')
        return super(StorageAdapter, self)._decorate(model, primary_key, data)

    #--------------+
    #  Public API  |
    #--------------+

    def clear(self):
        """
        Clears the whole storage from data.
        """
        self.connection.remove()

    def delete(self, primary_key):
        """
        Permanently deletes the record with given primary key from the database.
        """
        self.connection.remove({'_id': primary_key})

    def get(self, model, primary_key):
        """
        Returns model instance for given model and primary key.
        Raises KeyError if there is no item with given key in the database.
        """
        data = self.connection.find_one({'_id': primary_key})
        if data:
            return self._decorate(model, primary_key, data)
        raise KeyError('collection "{collection}" of database "{database}" '
                        'does not contain key "{key}"'.format(
                            database = self.database_name,
                            collection = self.collection_name,
                            key = primary_key
                        ))


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
        outgoing = data.copy()
        if primary_key:
            outgoing.update({'_id': primary_key})
#        print outgoing
        return self.connection.save(outgoing) or primary_key

    def get_query(self, model):
        return QueryAdapter(storage=self, model=model)


class QueryAdapter(CachedIterator, BaseQueryAdapter):

    #--------------------+
    #  Magic attributes  |
    #--------------------+

#    def __and__(self, other):
#        raise NotImplementedError

#    def __getitem__(self, k):
#        result = self._query[k]
#        if isinstance(k, slice):
#            return [self.storage._decorate(self.model, r) for r in result]
#        else:
#            return self.storage._decorate(self.model, result)

#    def __iter__(self):
#        for item in self._query:
#            yield self.storage._decorate(self.model, data)

#    def __or__(self, other):
#        raise NotImplementedError

#    def __sub__(self, other):
#        raise NotImplementedError

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _do_search(self):
        # this is a bit weird -- we merge all conditions into a single
        # dictionary; calling find() in a sequence may be a better idea(?)
        # because smth like:
        #  [{'foo': {'$gt': 0}}, {'foo': {'$lt': 5}}]
        # will yield an equivalent of `foo < 5` instead of `0 < foo < 5`.
        # We try to alleviate this issue by respecting an extra level but a
        # more complex structure can be crippled.
        spec = {}
        for condition in self._conditions:
#            print 'MONGO condition', condition
            for name, clause in condition.iteritems():
                spec.setdefault(name, {}).update(clause)
#        print 'MONGO spec', spec
        results = self.storage.connection.find(spec)
        return iter(results) if results is not None else []

    def _init(self, storage, model, conditions=None):  #, ordering=None):
        self.storage = storage
        self.model = model
        self._conditions = conditions or []
        #self._query = self.storage.connection.find()
        self._iter = self._do_search()

    # XXX can this be inherited?
#    def _clone(self, inner_query=None):
#        clone = self.__class__(self.storage, self.model)
#        clone._query = self._query.clone() if inner_query is None else inner_query
#        return clone

    def _clone(self, extra_conditions=None):    #, extra_ordering=None):
        return self.__class__(
            self.storage,
            self.model,
            conditions = self._conditions + (extra_conditions or []),
            #ordering = extra_ordering or self._ordering,
        )
    def _where(self, lookups, negate=False):
        conditions = list(self._get_native_conditions(lookups, negate))
#        print lookups
        return self._clone(extra_conditions=conditions)

    #--------------+
    #  Public API  |
    #--------------+

    def where(self, **conditions):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        return self._where(conditions, negate=False)

    def where_not(self, **conditions):
        """
        Returns Query instance. Inverted version of
        :meth:`~docu.backends.tokyo_cabinet.Query.where`.
        """
        return self._where(conditions, negate=True)

#        # FIXME PyMongo conditions API propagates; we would like to unify all
#        # APIs but let user specify backend-specific stuff.
#        # TODO:inherit other cursor properties (see pymongo.cursor.Cursor.clone)
#
#        ### HACK: using private properties is nasty
#        old_conds = dict(self._query._Cursor__query_spec())['query']
#
#        combined_conds = dict(old_conds, **conditions)
#        q = self.storage.connection.find(combined_conds)
#        return self._clone(q)

#    def where_not(self, **conditions):
#        raise NotImplementedError

#    def count(self):
#        return self._query.count()

#    def order_by(self, name):
#        name, direction = name, pymongo.ASCENDING
#        if name.startswith('-'):
#            name, direction = name[1:], pymongo.DESCENDING
#
#        q = self._query.sort(name, direction)
#        return self._clone(q)

#    def values(self, name):
#        return self._query.distinct(name)

#    def delete(self):
#        """
#        Deletes all records that match current query.
#        """
#        raise NotImplementedError
