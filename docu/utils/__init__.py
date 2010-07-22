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
Utilities
=========

Various useful functions. Some can be imported from :mod:`docu.utils`, some
are available directly at :mod:`docu`.
"""

import os
import pkg_resources
import re
import sys


__all__ = ['get_db', 'camel_case_to_underscores', 'load_fixture']


def get_db(settings_dict=None, **settings_kwargs):
    """
    Storage adapter factory. Expects path to storage backend module and
    optional backend-specific settings. Returns storage adapter instance.
    If required underlying library is not found, exception
    `pkg_resources.DistributionNotFound` is raised with package name and
    version as the message.

    :param backend:
        string, dotted path to a Docu storage backend (e.g.
        `docu.ext.tokyo_tyrant`). See :doc:`ext` for a list of bundled backends
        or :doc:`backend_base` for backend API reference.

    Usage::

        import docu

        db = docu.get_db(backend='docu.ext.shelve', path='test.db')

        query = SomeDocument.objects(db)

    Settings can be also passed as a dictionary::

        SETTINGS = {
            'backend': 'docu.ext.tokyo_cabinet',
            'path': 'test.tct',
        }

        db = docu.get_db(SETTINGS)

    The two methods can be combined to override certain settings::

        db = docu.get_db(SETTINGS, path='another_db.tct')


    """
    # copy the dictionary because we'll modify it below
    settings = dict(settings_dict or {})
    settings.update(settings_kwargs)

    # extract the dot-delimited path to the Docu-compatible backend
    backend_path = settings.pop('backend')

    # import the backend module
    entry_points = pkg_resources.iter_entry_points('db_backends')
    named_entry_points = dict((x.module_name, x) for x in entry_points)
    if backend_path in named_entry_points:
        entry_point = named_entry_points[backend_path]
        module = entry_point.load()
    else:
        __import__(backend_path)
        module = sys.modules[backend_path]

    # instantiate the storage provided by the backend module
    StorageAdapter = module.StorageAdapter
    return StorageAdapter(**settings)

def camel_case_to_underscores(class_name):
    """
    Returns a pretty readable name based on the class name. For example,
    "SomeClass" is translated to "some_class".
    """
    # This is derived from Django:
    # Calculate the verbose_name by converting from InitialCaps to "lowercase with spaces".
    return re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1',
                  class_name).lower().strip().replace(' ', '_')

def load_fixture(path, db=None):
    """
    Reads given file (assuming it is in a known format), loads it into given
    storage adapter instance and returns that instance.

    :param path:
        absolute or relative path to the fixture file; user constructions
        ("~/foo") will be expanded.
    :param db:
        a storage adapter instance (its class must conform to the
        :class:`~docu.backend_base.BaseStorageAdapter` API). If not provided, a
        memory storage will be created.

    Usage::

        import docu

        db = docu.load_fixture('account.csv')

        query = SomeDocument.objects(db)

    """
    db = db or get_db(backend='docu.ext.shove_db', store_uri='memory://')
    path = os.path.expanduser(path) if '~' in path else os.path.abspath(path)
    if not os.path.isfile(path):
        raise ValueError('could not find file {0}'.format(path))
    loader = _get_fixture_loader(path)
    f = open(path)
    items = loader(f)
    for item in items:
        db.save(None, item)
    return db

def _get_fixture_loader(filename):
    if filename.endswith('.yaml'):
        import yaml
        loader = yaml.load
    elif filename.endswith('.json'):
        import json
        loader = json.load
    elif filename.endswith('.csv'):
        import csv
        loader = csv.DictReader
    else:
        raise ValueErrori('unknown data file type: {0}'.format(filename))
    return loader
