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

"""
A storage/query backend for Tokyo Tyrant.

:database: `Tokyo Cabinet`_, `Tokyo Tyrant`_
:status: stable
:dependencies: `Pyrant`_

  .. _Tokyo Cabinet: http://1978th.net/tokyocabinet
  .. _Tokyo Tyrant: http://1978th.net/tokyotyrant
  .. _Pyrant: http://pypi.python.org/pypi/pyrant

"""

__all__ = ['StorageAdapter']


from storage import StorageAdapter

# let backend-specific stuff register itself with managers
import converters
import lookups

