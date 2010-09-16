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

:status: beta
:database: `MongoDB`_
:dependencies: `pymongo`_
:suitable for: general purpose (mostly server-side)

  .. _MongoDB: http://mongodb.org
  .. _pymongo: http://api.mongodb.org/python

.. warning::

    this module is not intended for production. It contains some hacks and
    should be refactored. However, it is actually used in a real project
    involving complex queries. Patches, improvements, rewrites are welcome.

"""

from docu import dist
dist.check_dependencies(__name__)

import pymongo

from docu.backend_base import BaseStorageAdapter, BaseQueryAdapter
from docu.utils.data_structures import CachedIterator

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
        key = self._string_to_object_id(key)
        return bool(self.connection.find({'_id': key}).count())

    def __iter__(self):
        """
        Yields all keys available for this connection.
        """
        return iter(self.connection.find(spec={}, fields={'_id': 1}))

    def __len__(self):
        return self.connection.count()

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _decorate(self, model, primary_key, raw_data):
        data = dict(raw_data)
        key = data.pop('_id')
        # this case is for queries where we don't know the PKs in advance;
        # however, we do know them when fetching a certain document by PK
        if primary_key is None:
            primary_key = self._object_id_to_string(key)
        return super(StorageAdapter, self)._decorate(model, primary_key, data)

    def _object_id_to_string(self, pk):
        if isinstance(pk, pymongo.objectid.ObjectId):
            return u'x-objectid-{0}'.format(pk)
        return pk

    def _string_to_object_id(self, pk):
        # XXX check consistency
        # MongoDB will *not* find items by the str/unicode representation of
        # ObjectId so we must wrap them; however, it *will* find items if their
        # ids were explicitly defined as plain strings. These strings will most
        # likely be not accepted by ObjectId as arguments.
        # Also check StorageAdapter.__contains__, same try/catch there.
        #print 'TESTING GET', model.__name__, primary_key
        assert isinstance(pk, basestring)
        if pk.startswith('x-objectid-'):
            return pymongo.objectid.ObjectId(pk.split('x-objectid-')[1])
        return pk

    #--------------+
    #  Public API  |
    #--------------+

    def clear(self):
        """
        Clears the whole storage from data.
        """
        self.connection.remove()

    def connect(self):
        host = self._connection_options.get('host', '127.0.0.1')
        port = self._connection_options.get('port', 27017)
        database_name = self._connection_options.get('database', 'default')
        collection_name = self._connection_options.get('collection', 'default')

        self._mongo_connection = pymongo.Connection(host, port)
        self._mongo_database = self._mongo_connection[database_name]
        self._mongo_collection = self._mongo_database[collection_name]
        self.connection = self._mongo_collection

    def delete(self, primary_key):
        """
        Permanently deletes the record with given primary key from the database.
        """
        primary_key = self._string_to_object_id(primary_key)
        self.connection.remove({'_id': primary_key})

    def disconnect(self):
        self._mongo_connection.disconnect()
        self._mongo_connection = None
        self._mongo_database = None
        self._mongo_collection = None
        self.connection = None

    def get(self, model, primary_key):
        """
        Returns model instance for given model and primary key.
        Raises KeyError if there is no item with given key in the database.
        """
        obj_id = self._string_to_object_id(primary_key)
        data = self.connection.find_one({'_id': obj_id})
        if data:
            return self._decorate(model, str(primary_key), data)
        raise KeyError('collection "{collection}" of database "{database}" '
                       'does not contain key "{key}"'.format(
                           database = self._mongo_database.name,
                           collection = self._mongo_collection.name,
                           key = str(primary_key)
                       ))

    def get_many(self, doc_class, primary_keys):
        """
        Returns a list of documents with primary keys from given list. More
        efficient than calling :meth:`~StorageAdapter.get` multiple times.
        """
        obj_ids = [self._string_to_object_id(pk) for pk in primary_keys]
        results = self.connection.find({'_id': {'$in': obj_ids}}) or []
        assert len(results) <= len(primary_keys), '_id must be unique'
        _get_obj_pk = lambda obj: str(self._object_id_to_string(data['_id']))
        if len(data) == len(primary_keys):
            return [self._decorate(model, _get_obj_pk(obj), data)
                    for data in results]
        keys = [_get_obj_pk(obj) for obj in results]
        missing_keys = [pk for pk in keys if pk not in primary_keys]
        raise KeyError('collection "{collection}" of database "{database}" '
                       'does not contain keys "{keys}"'.format(
                           database = self._mongo_database.name,
                           collection = self._mongo_collection.name,
                           keys = ', '.join(missing_keys)))

    def save(self, data, primary_key=None):
        """
        Saves given model instance into the storage. Returns primary key.

        :param data:
            dict containing all properties to be saved
        :param primary_key:
            the key for given object; if undefined, will be generated

        Note that you must provide current primary key for a model instance which
        is already in the database in order to update it instead of copying it.
        """
        outgoing = data.copy()
        if primary_key:
            outgoing.update({'_id': self._string_to_object_id(primary_key)})
#        print outgoing
        obj_id = self.connection.save(outgoing)
        return self._object_id_to_string(obj_id) or primary_key
#        return unicode(self.connection.save(outgoing) or primary_key)

    def get_query(self, model):
        return QueryAdapter(storage=self, model=model)


class QueryAdapter(CachedIterator, BaseQueryAdapter):

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    # ...

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _do_search(self, **kwargs):
        # TODO: slicing? MongoDB supports it since 1.5.1
        # http://www.mongodb.org/display/DOCS/Advanced+Queries#AdvancedQueries-%24sliceoperator
        spec = self.storage.lookup_manager.combine_conditions(self._conditions)
        if self._ordering:
            kwargs.setdefault('sort',  self._ordering)
        cursor = self.storage.connection.find(spec, **kwargs)
        self._cursor = cursor  # used in count()    XXX that's a mess
        return iter(cursor) if cursor is not None else []

    def _init(self, storage, model, conditions=None, ordering=None):
        self.storage = storage
        self.model = model
        self._conditions = conditions or []
        self._ordering = ordering
        #self._query = self.storage.connection.find()
        self._iter = self._do_search()

    # XXX can this be inherited?
#    def _clone(self, inner_query=None):
#        clone = self.__class__(self.storage, self.model)
#        clone._query = self._query.clone() if inner_query is None else inner_query
#        return clone

    def _clone(self, extra_conditions=None, extra_ordering=None):
        return self.__class__(
            self.storage,
            self.model,
            conditions = self._conditions + (extra_conditions or []),
            ordering = extra_ordering or self._ordering,
        )

    def _prepare(self):
        # XXX this seems to be [a bit] wrong; check the CachedIterator workflow
        # (hint: if this meth is empty, query breaks on empty result set
        # because self._iter appears to be None in that case)
        # (Note: same crap in in docu.ext.shelve_db.QueryAdapter.)

        # also note that we have to ensure that _cache is not empty because
        # otherwise it would be filled over and over again (and not even
        # refilled but appended to).
        # _iter can be None in two cases: a) initial state, and b) the iterable
        # is exhausted, cache filled.
        # but what if the iterable is just empty? _iter=None, _cache=[] and we
        # start over and over.
        # this must be fixed.
        if self._iter is None and not self._cache:   # XXX important for all backends!
            self._iter = self._do_search()

    def _prepare_item(self, raw_data):
        return self.storage._decorate(self.model, None, raw_data)

    def _where(self, lookups, negate=False):
        conditions = list(self._get_native_conditions(lookups, negate))
        return self._clone(extra_conditions=conditions)

    #--------------+
    #  Public API  |
    #--------------+

    def count(self):
        return self._cursor.count()

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

    def order_by(self, names, reverse=False):
        # TODO: MongoDB supports per-key directions. Support them somehow?
        direction = pymongo.DESCENDING if reverse else pymongo.ASCENDING
        if isinstance(names, basestring):
            names = [names]
        ordering = [(name, direction) for name in names]
        return self._clone(extra_ordering=ordering)

    def values(self, name):
        """
        Returns distinct values for given field.

        :param name:
            the field name.

        .. note::

            A set is dynamically build on client side if the query contains
            conditions. If it doesn't, a much more efficient approach is used.
            It is only available within current **connection**, not query.

        """
        # TODO: names like "date_time__year"
        if not self._conditions:
            # this is faster but without filtering by query
            return self.storage.connection.distinct(name)
        values = set()
        for d in self._do_search(fields=[name]):
            values.add(d.get(name))
        return values

#    def delete(self):
#        """
#        Deletes all records that match current query.
#        """
#        raise NotImplementedError
