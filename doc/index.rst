Easy data modeling with PyModels
================================

`PyModels` is a lightweight framework for mapping Python classes to
schema-less databases. 

It is not an ORM as it doesn't map existing schemata to Python objects.
Instead, it lets you define schemata on a higher layer built upon a schema-less
storage (key/value or document-oriented). You define models as a valuable
subset of the whole database and work with only certain parts of existing
entities -- the parts you need.

Topics:

.. toctree::
   :maxdepth: 2

   installation
   usage
   backends
   validators

API reference:

.. toctree::
   :maxdepth: 2

   document
   backend_base

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

    http://bitbucket.org/neithere/pymodels/issues/

Licensing
---------

PyModels is free software: you can redistribute it and/or modify
it under the terms of the GNU Lesser General Public License as published
by the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

PyModels is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU Lesser General Public License for more details.

You should have received a copy of the GNU Lesser General Public License
along with PyModels.  If not, see <http://gnu.org/licenses/>.
