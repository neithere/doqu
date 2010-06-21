Storage backends
================

PyModels can be used with a multitude of databases providing a uniform API for
retrieving, storing, removing and searching of records. To couple PyModels with
a database, a storage/query backend is needed.

How it works
------------

A "**backend**" is a module that provides two classes: `Storage` and `Query`.
Both must conform to the basic specifications (see basic specs below).
Backends may not be able to implement all default methods; they may also
provide some extra methods.

The **Storage** class is an interface for the database. It allows
to add, read, create and update records by primary keys. You will not use this
class directly in your code.

The **Query** class is what you will talk
to when filtering objects of a model. There are no constraints on how the
search conditions should be represented. This is likely to cause some problems
when you switch from one backend to another. Some guidlines will be probably
defined to address the issue of portability. For now we try to ensure that all
default backends share the conventions defined by the Tokyo Tyrant backend.

Batteries included
------------------

The PyModels library ships with some storage/query backends. Here is the
complete API reference for these backends:

.. toctree::

   backend_base
   ext_tokyo_tyrant
   ext_tokyo_cabinet
   ext_mongodb
   ext_shelve

Switching backends
------------------

Let's assume we have a Tokyo Cabinet database. You can choose the TC backend to
use the DB file :doc:`directly <ext_tokyo_cabinet>` or access the same file
:doc:`through the manager <ext_tokyo_tyrant>`. The first option is great
for development and some other cases where you would use SQLite; the second
option is important for most production environments where multiple connections
are expected. The good news is that there's no more import and export,
dump/load sequences, create/alter/drop and friends. Having tested the
application against the database `storage.tct` with Cabinet backend, just run
`ttserver storage.tct` and switch the backend config.

Let's create our application::

    import pymodels
    import settings
    from models import Country, Person

    storage = pymodels.get_storage(settings.DATABASE)

    print Person.objects(storage)   # prints all Person objects from DB

Now define settings for both backends (settings.py)::

    # direct access to the database (simple, not scalable)
    TOKYO_CABINET_DATABASE = {
        'backend': 'pymodels.ext.tokyo_cabinet',
        'kind': 'TABLE',
        'path': 'storage.tct',
    }

    # access through the Tyrant manager (needs daemon, scalable)
    TOKYO_TYRANT_DATABASE = {
        'backend': 'pymodels.ext.tokyo_tyrant',
        'host': 'localhost',
        'port': 1978,
    }

    # this is the *only* line you need to change in order to change the backend
    DATABASE = TOKYO_CABINET_DATABASE
