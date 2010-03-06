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

import sys


def get_storage(settings_dict=None, **settings_kwargs):
    """
    Storage factory. Expects path to storage backend module, e.g.
    "pymodels.backends.tyrant". Returns storage class instance.

    Can be helpful to easily switch backends. For example, if you are using
    Tokyo Cabinet, you can use the same database file and only change the way
    you access it: directly (TC) or through the server (TT).

    Usage::

        # direct access
        TC_DATABASE_SETTINGS = {
            'backend': 'pymodels.backends.tokyo_cabinet',
            'path': 'test.tct',
        }

        # access through a Tyrant server instance
        TT_DATABASE_SETTINGS = {
            'backend': 'pymodels.backends.tokyo_tyrant',
            'host': 'localhost',
            'port': '1983',
        }

        db = pymodels.get_storage(TT_DATABASE_SETTINGS)
        # OR:
        db = pymodels.get_storage(TC_DATABASE_SETTINGS, path='test2.tct')

        print SomeModel.query(db)

    Note: the backend module *must* provide a class named "Storage".
    """
    # copy the dictionary because we'll modify it below
    settings = dict(settings_dict or {})
    settings.update(settings_kwargs)

    # extract the dot-delimited path to the PyModels-compatible backend
    backend_path = settings.pop('backend')

    # import the backend module
    __import__(backend_path)
    backend_module = sys.modules[backend_path]

    # instantiate the storage provided by the backend module
    Storage = backend_module.Storage
    return Storage(**settings)
