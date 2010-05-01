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
A storage/query backend for Tokyo Cabinet.

Allows direct access to the database and is thus extremely fast. However, it
locks the database and is therefore not suitable for environments where
concurrent access is required. Please use Tokyo Tyrant for such environments.


:database: `Tokyo Cabinet`_
:status: experimental
:dependencies: `tc (rsms)`_

  .. _Tokyo Cabinet: http://1978th.net/tokyocabinet
  .. _tc (rsms): http://github.com/rsms/tc

.. warning:: this module is not intended for production, it's just a (working)
    example. Patches, improvements, rewrites are welcome.

Usage::

    >>> import os
    >>> import pymodels
    >>> DB_SETTINGS = {
    ...     'backend': 'pymodels.backends.tokyo_cabinet',
    ...     'kind': 'TABLE',
    ...     'path': '_tc_test.tct',
    ... }
    >>> assert not os.path.exists(DB_SETTINGS['path']), 'test database must not exist'
    >>> db = pymodels.get_storage(DB_SETTINGS)
    >>> class Person(pymodels.Model):
    ...     name = pymodels.Property()
    ...     __unicode__ = lambda self: self.name
    >>> Person.objects(db)    # the database is expected to be empty
    []
    >>> db.connection.put('john', {'name': 'John'})
    >>> mary = Person(name='Mary')
    >>> mary_pk = mary.save(db)
    >>> q = Person.objects(db)
    >>> q
    [<Person John>, <Person Mary>]
    >>> q.where(name__matches='^J')
    [<Person John>]
    >>> q    # the original query was not modified by the descendant
    [<Person John>, <Person Mary>]
    >>> os.unlink(DB_SETTINGS['path'])

"""

import uuid
from pymodels.backends.base import BaseStorage, BaseQuery
from pymodels.utils.iterators import CachedIterator

try:
    import tc
except ImportError:
    raise ImportError('Tokyo Cabinet backend requires package "tc". Most recent '
                      'version from github.com/rsms/tc/ is preferable.')

try:
    from pyrant.query import Condition, Ordering
except ImportError:
    raise ImportError('Tokyo Cabinet backend requires package "pyrant".')


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
        # FIXME we should use TC's internal function "genuid", but it is not
        # available with current Python API (i.e. the "tc" package).
        model_label = model.__name__.lower()
        return '%s_%s' % (model_label, uuid.uuid4())

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
            try:
                data[key] = str(data[key])
            except UnicodeEncodeError:
                data[key] = unicode(data[key]).encode('UTF-8')

        primary_key = primary_key or self._generate_primary_key(model)

        self.connection.put(primary_key, data)

        # TODO: check if this is useful; if yes, include param "sync" in meth sig
        #if sync:
        #    storage.sync()

        return primary_key

    def get_query(self, model):
        return Query(storage=self, model=model)


class Query(CachedIterator):    # NOTE: not a subclass of BaseQuery -- maybe the latter is too fat?
    """
    The Query class. Experimental.
    """
    #
    # PYTHON MAGIC METHODS
    #

    # (see CachedIterator)

    #
    # PRIVATE METHODS
    #

    def _init(self, storage, model, conditions=None, ordering=None):
        self.storage = storage
        self.model = model
        self._conditions = conditions or []
        self._ordering = ordering
        if self._iter is None:
            _query = self.storage.connection.query()
            for condition in self._conditions:
                col, op, expr = condition.prepare()
                if not isinstance(expr, basestring):
                    expr = str(expr)
                _query = _query.filter(col, op, expr)
            if self._ordering:
                _query.order(type=self._ordering.type, column=self._ordering.name)
            self._iter = iter(_query.keys())

    def _prepare_item(self, key):
        return self.storage.get(self.model, key)

    def _where(self, lookups, negate=False):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        conditions = [Condition(k, v, negate) for k, v in lookups]
        return self._clone(extra_conditions=conditions)

    def _clone(self, extra_conditions=None, extra_ordering=None):
        return self.__class__(
            self.storage,
            self.model,
            conditions = self._conditions + (extra_conditions or []),
            ordering = extra_ordering or self._ordering,
        )

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
        """
        Returns Query instance. Inverted version of
        :meth:`~pymodels.backends.tokyo_cabinet.Query.where`.
        """
        return self._where(conditions.items(), negate=True)

    def count(self):
        """
        Same as ``__len__``.

        .. warning: the underlying Python library does not provide proper
            method to get the number of records without fetching the results.

        """
        # NOTE: inefficient, but the library does not provide proper methods
        return len(self)

    def order_by(self, name, numeric=False):
        """
        Defines order in which results should be retrieved.

        :param name: the column name. If prefixed with ``-``, direction changes
            from ascending (default) to descending.

        Examples::

            q.order_by('name')     # ascending
            q.order_by('-name')    # descending

        """

        # handle "name"/"-name"
        if name.startswith('-'):
            name = name[1:]
            direction = Ordering.DESC
        else:
            direction = Ordering.ASC

        # introspect model and use numeric sorting if appropriate
        property = self.model._meta.props[name]
        numeric = property.python_type in (int, float)

        ordering = Ordering(name, direction, numeric)

        return self._clone(extra_ordering=ordering)

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
