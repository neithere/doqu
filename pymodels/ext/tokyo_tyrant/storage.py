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

from pymodels.backend_base import BaseStorageAdapter
from managers import converter_manager, lookup_manager
from query import QueryAdapter

try:
    from pyrant import Tyrant
except ImportError:  # pragma: nocover
    raise ImportError('Package "pyrant" must be installed to enable Tokyo Tyrant'
                      ' backend.')


class StorageAdapter(BaseStorageAdapter):
    supports_nested_data = False
    converter_manager = converter_manager
    lookup_manager = lookup_manager

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    def __contains__(self, key):
        return key in self.connection

    def __init__(self, host='127.0.0.1', port=1978):
        # TODO: sockets, etc.
        self.host = host
        self.port = port
        self.connection = Tyrant(host=host, port=port)

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _fetch(self, primary_key):
        """
        Returns model instance for given model and primary key.
        Raises KeyError if there is no item with given key in the database.
        """
        return self.connection[primary_key] or {}

    #--------------+
    #  Public API  |
    #--------------+

    def clear(self):
        """
        Clears the whole storage from data, resets autoincrement counters.
        """
        self.connection.clear()

    def delete(self, key):
        """
        Permanently deletes the record with given primary key from the database.
        """
        del self.connection[key]


    def get_query(self, model):
        return QueryAdapter(storage=self, model=model)

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
        primary_key = primary_key or self.connection.generate_key()

        self.connection[primary_key] = data

        return primary_key
