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

import uuid

from pymodels.backend_base import BaseQueryAdapter

try:
    from pyrant import Tyrant
except ImportError:
    raise ImportError('Package "pyrant" must be installed to enable Tokyo Tyrant'
                      ' backend.')


class QueryAdapter(BaseQueryAdapter):

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    def __and__(self, other):
        assert isinstance(other, self.__class__)
        q = self._query.intersect(other._query)
        return self._clone(q)

    def __getitem__(self, k):
        result = self._query[k]
        if isinstance(k, slice):
            return [self.storage._decorate(self.model, key, data)
                                                   for key, data in result]
        else:
            key, data = result
            return self.storage._decorate(self.model, key, data)

    def __iter__(self):
        for key, data in self._query:
            yield self.storage._decorate(self.model, key, data)

    def __or__(self, other):
        assert isinstance(other, self.__class__)
        q = self._query.union(other._query)
        return self._clone(q)


    def __sub__(self, other):
        assert isinstance(other, self.__class__)
        q = self._query.minus(other._query)
        return self._clone(q)

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _init(self):
        self._query = self.storage.connection.query
    #    # by default only fetch columns specified in the Model
    #    col_names = self.model._meta.props.keys()
    #    self._query = self.storage.connection.query.columns(*col_names)

    def _clone(self, inner_query=None):
        clone = self.__class__(self.storage, self.model)
        clone._query = self._query if inner_query is None else inner_query
        return clone

    #--------------+
    #  Public API  |
    #--------------+

    def count(self):
        """
        Returns the number of records that match current query. Does not fetch
        the records.
        """
        return self._query.count()

    def delete(self):
        """
        Deletes all records that match current query.
        """
        self._query.delete()

    def order_by(self, name):
        # introspect model and use numeric sorting if appropriate
        attr_name = name[1:] if name.startswith('-') else name
        numeric = self.model.meta.structure[attr_name] in (int, float)

        q = self._query.order_by(name, numeric)
        return self._clone(q)

    def values(self, name):
        """
        Returns a list of unique values for given column name.
        """
        values = self._query.values(name)
        datatype = self.model.meta.structure[name]
        return [self.storage.value_from_db(datatype, v) for v in values]

    def where(self, **conditions):
        """
        Returns Query instance filtered by given conditions.
        The conditions are defined exactly as in Pyrant's high-level query API.
        See pyrant.query.Query.filter documentation for details.
        """
        q = self._query
        native_conditions = self._get_native_conditions(**conditions)
        for x in native_conditions:
            q = q.filter(**x)
        return self._clone(q)

    def where_not(self, **conditions):
        """
        Returns Query instance. Inverted version of
        :meth:`~pymodels.backends.tokyo_tyrant.Query.where`.
        """
        q = self._query
        native_conditions = self._get_native_conditions(**conditions)
        for x in native_conditions:
            q = q.exclude(**x)
        return self._clone(q)
