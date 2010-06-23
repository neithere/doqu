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

import re
import sys


__all__ = ['get_db', 'camel_case_to_underscores']


def get_db(settings_dict=None, **settings_kwargs):
    """
    Storage adapter factory. Expects path to storage backend module, e.g.
    "docu.ext.tokyo_tyrant". Returns storage adapter instance.

    Can be helpful to easily switch backends. For example, if you are using
    Tokyo Cabinet, you can use the same database file and only change the way
    you access it: directly (TC) or through the server (TT).

    Usage::

        # direct access
        TC_DATABASE_SETTINGS = {
            'backend': 'docu.ext.tokyo_cabinet',
            'path': 'test.tct',
        }

        # access through a Tyrant server instance
        TT_DATABASE_SETTINGS = {
            'backend': 'docu.ext.tokyo_tyrant',
            'host': 'localhost',
            'port': '1983',
        }

        db = docu.get_db(TT_DATABASE_SETTINGS)
        # OR:
        db = docu.get_db(TC_DATABASE_SETTINGS, path='test2.tct')

        print SomeDocument.objects(db)

    Note: the backend module *must* provide a class named "StorageAdapter".
    """
    # copy the dictionary because we'll modify it below
    settings = dict(settings_dict or {})
    settings.update(settings_kwargs)

    # extract the dot-delimited path to the Docu-compatible backend
    backend_path = settings.pop('backend')

    # import the backend module
    __import__(backend_path)
    backend_module = sys.modules[backend_path]

    # instantiate the storage provided by the backend module
    StorageAdapter = backend_module.StorageAdapter
    return StorageAdapter(**settings)

def camel_case_to_underscores(class_name):
    """
    Returns a pretty readable name based on the class name.
    """
    # This is derived from Django:
    # Calculate the verbose_name by converting from InitialCaps to "lowercase with spaces".
    return re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1',
                  class_name).lower().strip().replace(' ', '_')
