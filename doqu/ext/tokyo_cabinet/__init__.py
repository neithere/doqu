# -*- coding: utf-8 -*-
#
#    Doqu is a lightweight schema/query framework for document databases.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of Docu.
#
#    Doqu is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Doqu is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Docu.  If not, see <http://gnu.org/licenses/>.


"""
Tokyo Cabinet extension
=======================

A storage/query backend for Tokyo Cabinet.

Allows direct access to the database and is thus extremely fast. However, it
locks the database and is therefore not suitable for environments where
concurrent access is required. Please use Tokyo Tyrant for such environments.

:status: beta
:database: `Tokyo Cabinet`_
:dependencies: `tokyo-python`_, `pyrant`_
:suitable for: general purpose, embedded

  .. _Tokyo Cabinet: http://1978th.net/tokyocabinet
  .. _tokyo-python: http://pypi.python.org/pypi/tokyo-python/
  .. _pyrant: http://bitbucket.org/neithere/pyrant

.. warning::

    this module is not intended for production despite it *may* be stable. Bug
    reports and patches are welcome.

.. note::

    this module should not depend on Pyrant; just needs some refactoring.

.. note::

    support for metasearch is planned.

Usage::

    >>> import os
    >>> import doqu
    >>> DB_SETTINGS = {
    ...     'backend': 'doqu.ext.tokyo_cabinet',
    ...     'path': '_tc_test.tct',
    ... }
    >>> assert not os.path.exists(DB_SETTINGS['path']), 'test database must not exist'
    >>> db = doqu.get_db(DB_SETTINGS)
    >>> class Person(doqu.Document):
    ...     structure = {'name': unicode}
    ...     def __unicode__(self):
    ...         u'%(name)s' % self
    ...
    >>> Person.objects(db)    # the database is expected to be empty
    []
    >>> db.connection['john'] = {'name': 'John'}
    >>> mary = Person(name='Mary')
    >>> mary_pk = mary.save(db)
    >>> q = Person.objects(db)
    >>> q
    [<Person John>, <Person Mary>]
    >>> q.where(name__matches='^J')
    [<Person John>]
    >>> q    # the original query was not modified by the descendant
    [<Person John>, <Person Mary>]
    >>> db.connection.close()
    >>> os.unlink(DB_SETTINGS['path'])

"""

from doqu import dist
dist.check_dependencies(__name__)

from decimal import Decimal    # for order_by introspection

import tokyo.cabinet as tc

from doqu.backend_base import BaseStorageAdapter, BaseQueryAdapter
from doqu.utils.data_structures import CachedIterator

from converters import converter_manager
from lookups import lookup_manager


# FIXME this should be rather a Doqu feature.
# Or maybe a stand-alone library providing an abstract query layer.
try:
    from pyrant.query import Ordering
except ImportError:  # pragma: nocover
    raise ImportError('Tokyo Cabinet backend requires package "pyrant".')


__all__ = ['StorageAdapter']


class StorageAdapter(BaseStorageAdapter):
    """
    :param path:
        relative or absolute path to the database file (e.g. `test.tct`)

    .. note::

        Currently only *table* flavour of Tokyo Cabinet databases is supported.
        It is uncertain whether it is worth supporting other flavours as they
        do not provide query mechanisms other than access by primary key.

    """

    supports_nested_data = False
    converter_manager = converter_manager
    lookup_manager = lookup_manager

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    def __contains__(self, key):
        return key in self.connection

    def __iter__(self):
        return iter(self.connection)

    def __len__(self):
        return len(self.connection)

    #--------------+
    #  Public API  |
    #--------------+

    def clear(self):
        """
        Clears the whole storage from data, resets autoincrement counters.
        """
        self.connection.clear()

    def connect(self):
        """
        Connects to the database. Raises RuntimeError if the connection is not
        closed yet. Use :meth:`StorageAdapter.reconnect` to explicitly close
        the connection and open it again.
        """
        if self.connection is not None:
            raise RuntimeError('already connected')

        path = self._connection_options['path']
        self.connection = tc.TDB()
        self.connection.open(path, tc.TDBOWRITER | tc.TDBOCREAT)

    def delete(self, primary_key):
        """
        Permanently deletes the record with given primary key from the database.
        """
        del self.connection[primary_key]

    def disconnect(self):
        """
        Closes internal store and removes the reference to it.
        """
        self.connection.close()
        self.connection = None

    def get(self, doc_class, primary_key):
        """
        Returns document object for given document class and primary key.
        """
        data = self.connection[primary_key]
        return self._decorate(doc_class, primary_key, data)

    def save(self, data, primary_key=None):
        """
        Saves given model instance into the storage. Returns primary key.

        :param data:
            dict containing all properties to be saved
        :param primary_key:
            the key for given object; if undefined, will be generated

        Note that you must provide current primary key for a document object
        which is already in the database in order to update it instead of
        copying it.
        """
        # sanitize data for Tokyo Cabinet:
        # None-->'None' is wrong, force None-->''
        for key in data:
            if data[key] is None:
                data[key] = ''
            try:
                data[key] = str(data[key])
            except UnicodeEncodeError:
                data[key] = unicode(data[key]).encode('UTF-8')

        primary_key = primary_key or unicode(self.connection.uid())

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

    def _init(self, storage, model, conditions=None, ordering=None):
        self.storage = storage
        self.model = model
        self._conditions = conditions or []
        self._ordering = ordering
        # TODO: make this closer to the Pyrant's internal mechanism so that
        # metasearch can be used via storage.metasearch([q1, q2, .., qN], meth)
        if self._iter is None:
            self._query = self.storage.connection.query()
            for condition in self._conditions:
#                print 'condition:', condition
                col, op, expr = condition  #.prepare()
                if not isinstance(expr, basestring):
                    expr = str(expr)
                self._query.filter(col, op, expr)
            if self._ordering:
                self._query.sort(self._ordering.name,
                                 self._ordering.type)
                                             # TODO: make this lazy  (it fetches the keys)
            self._iter = iter(self._query.search())

    def _prepare_item(self, key):
        return self.storage.get(self.model, key)

    def _where(self, lookups, negate=False):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        conditions = list(self._get_native_conditions(lookups, negate))
#        print lookups, '  -->  ', conditions

        #for x in native_conditions:
        #    q = q.filter(**x)
        #conditions = [Condition(k, v, negate) for k, v in lookups]
        #conditions = lookups
        return self._clone(extra_conditions=conditions)

    def _clone(self, extra_conditions=None, extra_ordering=None):
        return self.__class__(
            self.storage,
            self.model,
            conditions = self._conditions + (extra_conditions or []),
            ordering = extra_ordering or self._ordering,
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
        :meth:`~doqu.backends.tokyo_cabinet.Query.where`.
        """
        return self._where(conditions, negate=True)

    def count(self):
        """
        Same as ``__len__`` but without fetching the records (i.e. faster).
        """
        return self._query.count()

    def order_by(self, names, reverse=False):
        """
        Defines order in which results should be retrieved.

        :param names:
            the field name by which the results should be sorted. Must be a
            string. The name is a bit misleading but the base backend API
            prescribes it.

        Examples::

            q.order_by('name')                  # ascending
            q.order_by('name', reverse=True)    # descending

        .. warning::

            The basic Doqu backend API allows multiple sorting fields. However,
            Tokyo Cabinet does not more than one. Specifying multiple names
            will raise TypeError.

        """
        assert isinstance(names, basestring)
        name = names
        direction = Ordering.DESC if reverse else Ordering.ASC

        # introspect model and use numeric sorting if appropriate
        numeric = False
        datatype = self.model.meta.structure.get(name)
        if datatype and isinstance(datatype, (int, float, long, Decimal)):
            numeric = True

        ordering = Ordering(name, direction, numeric)

        return self._clone(extra_ordering=ordering)

    def values(self, name):
        """
        Returns an iterator that yields distinct values for given column name.

        .. note::

            this is currently highly inefficient because the underlying library
            does not support columns mode (`tctdbiternext3`). Moreover, even
            current implementation can be optimized by removing the overhead of
            creating full-blown document objects (though preserving data type
            is necessary).

        """
        known_values = {}
        for d in self:
            value = d.get(name)
            if value and value not in known_values:
                known_values[value] = 1
                yield value

    def delete(self):
        """
        Deletes all records that match current query.
        """
        self._query.remove()
