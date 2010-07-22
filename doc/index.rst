Easy data modeling with Docu
============================

`Docu` is a lightweight Python framework for document databases. It provides a
uniform API for modeling, validation and queries across various kinds of
storages.

It is not an ORM as it doesn't map existing schemata to Python objects.
Instead, it lets you define schemata on a higher layer built upon a schema-less
storage (key/value or document-oriented). You define models as a valuable
subset of the whole database and work with only certain parts of existing
entities -- the parts you need.

Topics:

.. toctree::
    :maxdepth: 2

    installation
    tutorial
    glossary
    validators
    utils
    ext
    api

Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

Author
------

Originally written by Andrey Mikhaylenko since 2009.

See the file AUTHORS for a complete authors list of this application.

Please feel free to submit patches, report bugs or request features:

    http://bitbucket.org/neithere/docu/issues/

Licensing
---------

Docu is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Docu is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with Docu.  If not, see <http://gnu.org/licenses/>.
