# -*- coding: utf-8 -*-
#
#    PyModels is a framework for mapping Python classes to semi-structured data.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of PyModels.
#
#    PyModels is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    PyModels is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with PyModels.  If not, see <http://gnu.org/licenses/>.

"""
A storage/query backend for MongoDB.

:database: `MongoDB`_
:status: experimental
:dependencies: `pymongo`_

  .. _MongoDB: http://mongodb.org
  .. _pymongo: http://api.mongodb.org/python

.. warning:: this module is not intended for production, it's just a (working)
    example. Patches, improvements, rewrites are welcome.

"""

from pymodels.backends.base import BaseStorage, BaseQuery

try:
    import pymongo
except ImportError:
    raise ImportError('Package "pymongo" must be installed to enable MongoDB'
                      ' backend.')


class Storage(BaseStorage):

    supports_nested_data = True

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

    def _decorate(self, model, raw_data):
        data = dict(raw_data)
        key = data.pop('_id')
        return super(Storage, self)._decorate(model, key, data)

    def get(self, model, primary_key):
        """
        Returns model instance for given model and primary key.
        Raises KeyError if there is no item with given key in the database.
        """
        data = self.connection.find_one({'_id': primary_key})
        if data:
            return self._decorate(model, primary_key, data)
        raise KeyError('collection "%(collection)s" of database "%(database)s" '
                        'does not contain key "%(key)s"' % {
                            'database': self.database_name,
                            'collection': self.collection_name,
                            'key': primary_key,
                        })


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

        return self.connection.save(data)

    def get_query(self, model):
        return Query(storage=self, model=model)


class Query(BaseQuery):
    #
    # PYTHON MAGIC METHODS
    #

    def __and__(self, other):
        raise NotImplementedError

    def __getitem__(self, k):
        result = self._query[k]
        if isinstance(k, slice):
            return [self.storage._decorate(self.model, r) for r in result]
        else:
            return self.storage._decorate(self.model, result)

    def __iter__(self):
        for item in self._query:
            yield self.storage._decorate(self.model, data)

    def __or__(self, other):
        raise NotImplementedError

    def __sub__(self, other):
        raise NotImplementedError

    #
    # PRIVATE METHODS
    #

    def _init(self):
        self._query = self.storage.connection.find()

    def _clone(self, inner_query=None):
        clone = self.__class__(self.storage, self.model)
        clone._query = self._query.clone() if inner_query is None else inner_query
        return clone

    #
    # PUBLIC API
    #

    def where(self, **conditions):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        # FIXME PyMongo conditions API propagates; we would like to unify all
        # APIs but let user specify backend-specific stuff.
        # TODO:inherit other cursor properties (see pymongo.cursor.Cursor.clone)

        ### HACK: using private properties is nasty
        old_conds = dict(self._query._Cursor__query_spec())['query']

        combined_conds = dict(old_conds, **conditions)
        q = self.storage.connection.find(combined_conds)
        return self._clone(q)

    def where_not(self, **conditions):
        raise NotImplementedError

    def count(self):
        return self._query.count()

    def order_by(self, name):
        name, direction = name, pymongo.ASCENDING
        if name.startswith('-'):
            name, direction = name[1:], pymongo.DESCENDING

        q = self._query.sort(name, direction)
        return self._clone(q)

    def values(self, name):
        return self._query.distinct(name)

    def delete(self):
        """
        Deletes all records that match current query.
        """
        raise NotImplementedError
