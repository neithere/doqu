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
Shove extension
===============

A storage/query backend for `shove`_ which is bundled with Python.

:status: beta
:database: any supported by `shove`_: *storage* — Amazon S3 Web Service,
    Berkeley Source Database, Filesystem, Firebird, FTP, DBM, Durus, Memory,
    Microsoft SQL Server, MySQL, Oracle, PostgreSQL, SQLite, Subversion, Zope
    Object Database (ZODB); *caching* — Filesystem, Firebird, memcached,
    Memory, Microsoft SQL Server, MySQL, Oracle, PostgreSQL, SQLite
:dependencies: `shove`_
:suitable for: "smart" interface to a key/value store; temporary memory storage

This extension wraps the `shove` library and provides the uniform query API
along with support for :class:`~docu.document_base.Document` API.

  .. note:: Regardless of the underlying storage, Shove serializes the records
    and only offers access by primary key. This means that efficient queries
    are impossible even with RDBMS; moreover, such databases are more likely to
    perform slower than simple key/value stores. The `Docu` queries with Shove
    involve iterating over the full set of records on client side and making
    per-row comparison without proper indexing.

    That said, the backend is considered not suitable for applications that
    depend on queries and require decent speed of lookups by value. However, it
    can be very useful as a memory storage (e.g. to analyze a JSON dump or
    calculate some data on the fly) or as an improved interface to an existing
    pure key/value storage which is mostly used without advanced queries.

  .. _shove: http://pypi.python.org/pypi/shove

"""

import uuid

from docu import dist
dist.check_dependencies(__name__)

from shove import Shove

from docu.backend_base import BaseStorageAdapter, BaseQueryAdapter
from docu.utils.data_structures import CachedIterator

# reuse most of the shelve extension's code
from docu.ext import shelve_db


__all__ = ['StorageAdapter']


class StorageAdapter(shelve_db.StorageAdapter):
    """
    All parametres are optional. Here are the most common:

    :param store_uri:
        URI for the data store
    :param cache_uri:
        URI for the caching instance

    The URI format for a backend is documented in its module (see the `shove`_
    documentation). The URI form is the same as `SQLAlchemy's`_.

    .. _SQLAlchemy's: http://www.sqlalchemy.org/docs/04/dbengine.html#dbengine_establishing

    """
    supports_nested_data = True

    converter_manager = shelve_db.converter_manager
    lookup_manager = shelve_db.lookup_manager

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    def connect(self):
        """
        Connects to the database. Raises RuntimeError if the connection is not
        closed yet. Use :meth:`StorageAdapter.reconnect` to explicitly close
        the connection and open it again.
        """
        if self.connection is not None:
            raise RuntimeError('already connected')

        self.connection = Shove(**self._connection_options)

    #--------------+
    #  Public API  |
    #--------------+

    def get_query(self, model):
        return QueryAdapter(storage=self, model=model)


class QueryAdapter(shelve_db.QueryAdapter):
    """
    The Query class.
    """
