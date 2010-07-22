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

import uuid

from docu.backend_base import BaseStorageAdapter
from managers import converter_manager, lookup_manager
from query import QueryAdapter

from pyrant import Tyrant


DEFAULT_HOST = '127.0.0.1'
DEFAULT_PORT = 1978


class StorageAdapter(BaseStorageAdapter):
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

    def connect(self):
        """
        Connects to the database. Raises RuntimeError if the connection is not
        closed yet. Use :meth:`StorageAdapter.reconnect` to explicitly close
        the connection and open it again.
        """
        # TODO: sockets, etc.
        host = self._connection_options.get('host', DEFAULT_HOST)
        port = self._connection_options.get('port', DEFAULT_PORT)
        self.connection = Tyrant(host=host, port=port)

    def delete(self, key):
        """
        Permanently deletes the record with given primary key from the database.
        """
        del self.connection[key]

    def disconnect(self):
        self.connection = None

    def get_query(self, model):
        return QueryAdapter(storage=self, model=model)

    def save(self, data, primary_key=None):
        """
        Saves given model instance into the storage. Returns primary key.

        :param data: dict containing all properties to be saved
        :param primary_key: the key for given object; if undefined, will be
            generated

        Note that you must provide current primary key for a model instance which
        is already in the database in order to update it instead of copying it.
        """
        primary_key = primary_key or self.connection.generate_key()

        self.connection[primary_key] = data

        return primary_key
