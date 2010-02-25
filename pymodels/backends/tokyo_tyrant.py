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


from pymodels.backends.base import BaseStorage, BaseQuery

try:
    from pyrant import Tyrant
except ImportError:
    raise ImportError('Package "pyrant" must be installed to enable Tokyo Tyrant'
                      ' backend.')


class Storage(BaseStorage):

    supports_nested_data = False

    def __init__(self, host='127.0.0.1', port=1978):
        # TODO: sockets, etc.
        self.host = host
        self.port = port
        self.connection = Tyrant(host=host, port=port)

    def get(self, model, primary_key):
        """
        Returns model instance for given model and primary key.
        Raises KeyError if there is no item with given key in the database.
        """
        data = self.connection[primary_key] or {}
        return self._decorate(model, primary_key, data)

    def _generate_primary_key(self, model):
        # TODO check if this is a correct way of generating an autoincremented pk
        # FIXME ...isn't! Table database supports "setindex", "search", "genuid".
        model_label = model.__name__.lower()
        max_key = len(self.connection.prefix_keys(model_label))
        return '%s_%d' % (model_label, max_key)

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
        # TODO: patch Pyrant itself, it's the library's area of responsibility
        for key in data:
            if data[key] is None:
                data[key] = ''

        primary_key = primary_key or self._generate_primary_key(model)

        self.connection[primary_key] = data

        # TODO: check if this is useful; if yes, include param "sync" in meth sig
        #if sync:
        #    storage.sync()

        return primary_key

    def get_query(self, model):
        return Query(storage=self, model=model)


class Query(BaseQuery):
    #
    # PYTHON MAGIC METHODS
    #

    def __and__(self, other):
        assert isinstance(other, self.__class__)
        q = self._query.intersect(other._query)
        return self._clone(q)

    def __getitem__(self, k):
        result = self._query[k]
        if isinstance(k, slice):
            return [self.storage._decorate(self.model, *result_) for result_ in result]
        else:
            return self.storage._decorate(self.model, *result)

    def __iter__(self):
        for key, data in self._query:
            yield self.storage._decorate(self.model, key, data)

    def __or__(self, other):
        assert isinstance(other, self.__class__)
        q = self._query.union(other._query)
        return self._clone(q)

    def __repr__(self):
        MAX_ITEMS_IN_REPR = 10
        if MAX_ITEMS_IN_REPR < self.count():
            return (str(list(self[:MAX_ITEMS_IN_REPR]))[:-1] + ' ... (other %d items '
                    'not displayed)]' % (self.count() - MAX_ITEMS_IN_REPR))
        else:
            return str(list(self))

    def __sub__(self, other):
        assert isinstance(other, self.__class__)
        q = self._query.minus(other._query)
        return self._clone(q)

    #
    # PRIVATE METHODS
    #

    def _init(self):
        self._query = self.storage.connection.query
    #    # by default only fetch columns specified in the Model
    #    col_names = self.model._meta.props.keys()
    #    self._query = self.storage.connection.query.columns(*col_names)

    def _clone(self, inner_query=None):
        clone = self.__class__(self.storage, self.model)
        clone._query = self._query if inner_query is None else inner_query
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
        q = self._query.filter(**conditions)
        return self._clone(q)

    def where_not(self, **conditions):
        q = self._query.exclude(**conditions)
        return self._clone(q)

    def count(self):
        return self._query.count()

    def order_by(self, name):
        # introspect model and use numeric sorting if appropriate
        attr_name = name[1:] if name.startswith('-') else name
        property = self.model._meta.props[attr_name]
        numeric = property.python_type in (int, float)

        q = self._query.order_by(name, numeric)
        return self._clone(q)

    def values(self, name):
        return self._query.values(name)

    def delete(self):
        """
        Deletes all records that match current query.
        """
        self._query.delete()
