# -*- coding: utf-8 -*-
#
#    Models is a framework for mapping Python classes to semi-structured data.
#    Copyright © 2009  Andrey Mikhaylenko
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
Abstract classes for unified storage/query API with various backends.
"""


__all__ = ['Storage', 'Query']


class BaseStorage(object):

    supports_nested_data = False

    def __init__(self, **kw):
        "Typical kwargs: host, port, name, user, password."
        raise NotImplementedError

    def _decorate(self, model, key, data):
        pythonized_data = {}
        for name, prop in model._meta.props.items():
            value = data.get(name, None)
            pythonized_data[name] = prop.to_python(value)
        return model(key=key, storage=self, **pythonized_data)

    def save(self, model_instance):
        raise NotImplementedError

    def get_query(self):
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
        # Do the query using getitem
        return unicode(self[:])

    def __sub__(self, other):
        return self.minus(other)

    #
    # PRIVATE METHODS
    #

    def _clone(self, inner_query=None):
        clone = self.__class__(self.storage, self.model)
        clone._query = self._query if inner_query is None else inner_query
        return clone

    def _init(self):
        pass

    #
    # PUBLIC API
    #

    def where(self, **conditions):
        """
        Returns Query instance filtered by given conditions.
        The conditions are specified by backend's underlying API.
        """
        raise NotImplementedError

    def where_not(self, **conditions):
        """
        Returns Query instance. Inverted version of ``where``.
        """
        raise NotImplementedError

    def order_by(self, name):
        raise NotImplementedError

    def values(self, name):
        raise NotImplementedError
