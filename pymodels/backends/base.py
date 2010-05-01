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
Abstract classes for unified storage/query API with various backends.

Derivative classes are expected to be either complete implementations or
wrappers for external libraries. The latter is assumed to be a better solution
as PyModels is only one of the possible layers. It is always a good idea to
provide different levels of abstraction and let others combine them as needed.

The backends do not have to subclass :class:`BaseStorage` and
:class:`BaseQuery`. However, they must closely follow their API.
"""


__all__ = ['Storage', 'Query']


class BaseStorage(object):

    supports_nested_data = False

    def __init__(self, **kw):
        "Typical kwargs: host, port, name, user, password."
        raise NotImplementedError

    def _decorate(self, model, key, data):
        """
        Populates a model instance with given data and initializes its state
        object with current storage and given key.
        """
        pythonized_data = {}
        for name, prop in model._meta.props.items():
            value = data.get(name, None)
            pythonized_data[name] = prop.to_python(value)
        instance = model(**pythonized_data)
        instance._state.update(storage=self, key=key, data=data)
        return instance

    def clear(self):
        """
        Clears the whole storage from data, resets autoincrement counters.
        """
        raise NotImplementedError

    def delete(self, key):
        """
        Deletes record with given primary key.
        """
        raise NotImplementedError

    def get(self, model, primary_key):
        """
        Returns model instance for given model and primary key.
        Raises KeyError if there is no item with given key
        in the database.
        """
        raise NotImplementedError

    def get_query(self):
        """
        Returns a Query object bound to this storage.
        """
        raise NotImplementedError

    def save(self, model, data, primary_key=None):
        """
        Saves given model instance into the storage. Returns
        primary key.

        :param model: model class
        :param data: dict containing all properties
            to be saved
        :param primary_key: the key for given object; if undefined, will be
            generated

        Note that you must provide current primary key for a model instance
        which is already in the database in order to update it instead of
        copying it.
        """
        raise NotImplementedError


class BaseQuery(object):
    #
    # PYTHON MAGIC METHODS
    #

    def __getitem__(self, key):
        raise NotImplementedError

    def __init__(self, storage, model):
        self.storage = storage
        self.model = model
        self._init()

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        return len(self[:])

    def __or__(self, other):
        raise NotImplementedError

    def __repr__(self):
        # we make extra DB hits here because query representation is mostly
        # used for interactive debug sessions or tests, so performance is
        # barely an issue in this case.
        MAX_ITEMS_IN_REPR = 10
        cnt = self.count()
        if MAX_ITEMS_IN_REPR < cnt:
            # assuming the query object supports slicing...
            return (str(list(self[:MAX_ITEMS_IN_REPR]))[:-1] + ' ... (other %d items '
                    'not displayed)]' % (cnt - MAX_ITEMS_IN_REPR))
        else:
            return str(list(self))

    def __sub__(self, other):
        raise NotImplementedError

    #
    # PRIVATE METHODS
    #

    def _init(self):
        pass

    #
    # PUBLIC API
    #

    def count(self):
        """
        Returns the number of records that match given query. The result of
        `q.count()` is exactly equivalent to the result of `len(q)`. The
        implementation details do not differ by default, but it is recommended
        that the backends stick to the following convention:

        - `__len__` executes the query, retrieves all matching records and
          tests the length of the resulting list;
        - `count` executes a special query that only returns a single value:
          the number of matching records.

        Thus, `__len__` is more suitable when you are going to iterate the
        records anyway (and do no extra queries), while `count` is better when
        you just want to check if the records exist, or to only use a part of
        matching records (i.e. a slice).
        """
        return len(self)    # may be inefficient, override if possible

    def delete(self):
        """
        Deletes all records that match current query.
        """
        raise NotImplementedError

    def order_by(self, name):
        """
        Returns a query object with same conditions but with results sorted by
        given column.

        :param name: string: name of the column by which results should be
            sorted. If the name begins with a ``-``, results will come in
            reversed order.

        """
        raise NotImplementedError

    def values(self, name):
        """
        Returns a list of unique values for given column name.
        """
        raise NotImplementedError

    def where(self, **conditions):
        """
        Returns Query instance filtered by given conditions.
        The conditions are specified by backend's underlying API.
        """
        raise NotImplementedError

    def where_not(self, **conditions):
        """
        Returns Query instance. Inverted version of `where()`.
        """
        raise NotImplementedError
