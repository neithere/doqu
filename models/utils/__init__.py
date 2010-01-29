# -*- coding: utf-8 -*-

import sys


def get_storage(settings_dict=None, **settings_kwargs):
    """
    Expects path to storage backend module, e.g. "models.backends.tyrant".
    Returns storage class instance.

    Can be helpful to easily switch backends. For example, if you are using
    Tokyo Cabinet, you can use the same database file and only change the way
    you access it: directly (TC) or through the server (TT).

    Usage::

        # direct access
        TC_DATABASE_SETTINGS = {
            'backend': 'models.backends.tokyo_cabinet',
            'path': 'test.tct',
        }

        # access through a Tyrant server instance
        TT_DATABASE_SETTINGS = {
            'backend': 'models.backends.tokyo_tyrant',
            'host': 'localhost',
            'port': '1983',
        }

        db = models.get_storage(TT_DATABASE_SETTINGS)
        # OR:
        db = models.get_storage(TC_DATABASE_SETTINGS, path='test2.tct')

        print SomeModel.query(db)

    Note: the backend module *must* provide a class named "Storage".
    """
    # copy the dictionary because we'll modify it below
    settings = dict(settings_dict or {})
    settings.update(settings_kwargs)

    # extract the dot-delimited path to the Models-compatible backend
    backend_path = settings.pop('backend')

    # import the backend module
    __import__(backend_path)
    backend_module = sys.modules[backend_path]

    # instantiate the storage provided by the backend module
    Storage = backend_module.Storage
    return Storage(**settings)
