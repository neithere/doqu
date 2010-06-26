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
Shelve extension
================

A storage/query backend for `shelve`_ which is bundled with Python.

:status: stable
:database: any dbm-style database supported by `shelve`_
:dependencies: the Python standard library
:suitable for: "smart" interface to a key/value store, small volume

A "shelf" is a persistent, dictionary-like object. The difference with “dbm”
databases is that the values (not the keys!) in a shelf can be essentially
arbitrary Python objects — anything that the pickle module can handle. This
includes most class instances, recursive data types, and objects containing
lots of shared sub-objects. The keys are ordinary strings.

This extension wraps the standard Python library and provides
:class:`~docu.document_base.Document` support and uniform query API.

  .. note:: The query methods are inefficient as they involve iterating over
    the full set of records and making per-row comparison without indexing.
    This backend is not suitable for applications that depend on queries and
    require decent speed. However, it is an excellent tool for existing
    DBM databases or for environments and cases where external dependencies are
    not desired.

  .. _shelve: http://docs.python.org/library/shelve.html

"""

import shelve
import uuid

from docu.backend_base import BaseStorageAdapter, BaseQueryAdapter
from docu.utils.data_structures import CachedIterator

from converters import converter_manager
from lookups import lookup_manager


__all__ = ['StorageAdapter']


class StorageAdapter(BaseStorageAdapter):
    """
    :param path: relative or absolute path to the database file (e.g. `test.tct`)

    """

    supports_nested_data = True
    converter_manager = converter_manager
    lookup_manager = lookup_manager

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    def __contains__(self, key):
        return key in self.connection

    def __init__(self, path):
        self.path = path
        self.connection = shelve.open(path)

    def __iter__(self):
        return iter(self.connection)

    def __len__(self):
        return len(self.connection)

    #--------------+
    #  Public API  |
    #--------------+

    def clear(self):
        """
        Clears the whole storage from data.
        """
        self.connection.clear()

    def delete(self, primary_key):
        """
        Permanently deletes the record with given primary key from the database.
        """
        del self.connection[primary_key]

    def get(self, model, primary_key):
        """
        Returns model instance for given model and primary key.
        """
        primary_key = str(primary_key)
        data = self.connection[primary_key]
        return self._decorate(model, primary_key, data)

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
        assert isinstance(data, dict)

        primary_key = str(primary_key or uuid.uuid4())

        self.connection[primary_key] = data

        return primary_key

    def get_query(self, model):
        return QueryAdapter(storage=self, model=model)


class QueryAdapter(CachedIterator, BaseQueryAdapter):
    """
    The Query class.
    """
    #--------------------+
    #  Magic attributes  |
    #--------------------+

    # (see CachedIterator)

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _do_search(self):
        """
        Iterates the full set of records, applies collected conditions to each
        record and yields primary keys of records that conform to these
        conditions. The conditions should be already collected via methods
        :meth:`where` and :meth:`where_not`.
        """
        assert hasattr(self._conditions, '__iter__')
        for pk in self.storage.connection:
            data = self.storage.connection[pk]
            # call check functions; if none fails, yield the key
            if all(check(data) for check in self._conditions):
                yield pk

    def _init(self, storage, model, conditions=None):  #, ordering=None):
        self.storage = storage
        self.model = model
        self._conditions = conditions or []
        # this is safe because the adapter is instantiated already with final
        # conditions; if a condition is added, that's another adapter
        self._iter = self._do_search()

    def _prepare_item(self, key):
        return self.storage.get(self.model, key)

    def _where(self, lookups, negate=False):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        conditions = list(self._get_native_conditions(lookups, negate))
        return self._clone(extra_conditions=conditions)

    def _clone(self, extra_conditions=None):    #, extra_ordering=None):
        return self.__class__(
            self.storage,
            self.model,
            conditions = self._conditions + (extra_conditions or []),
            #ordering = extra_ordering or self._ordering,
        )

    #--------------+
    #  Public API  |
    #--------------+

    def where(self, **conditions):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        return self._where(conditions)

    def where_not(self, **conditions):
        """
        Returns Query instance. Inverted version of
        :meth:`~docu.backends.tokyo_cabinet.Query.where`.
        """
        return self._where(conditions, negate=True)

    def count(self):
        """
        Same as ``__len__``.

        .. warning: the underlying Python library does not provide proper
            method to get the number of records without fetching the results.

        """
        # NOTE: inefficient, but the library does not provide proper methods
        return len(self)

    def values(self, name):
        """
        Returns an iterator that yields distinct values for given column name.

        .. note:: this is currently highly inefficient because the underlying
            library does not support columns mode (`tctdbiternext3`). Moreover,
            even current implementation can be optimized by removing the
            overhead of creating full-blown document objects.

        """
        known_values = {}
        for d in self:
            value = d.get(name)
            if value and value not in known_values:
                known_values[value] = 1
                yield value

    def delete(self):
        """
        Deletes all records that match current query. Iterates the whole set of
        records.
        """
        for pk in self._do_search():
            del self[pk]
