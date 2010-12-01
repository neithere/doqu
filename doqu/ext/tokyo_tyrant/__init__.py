# -*- coding: utf-8 -*-
#
#    Doqu is a lightweight schema/query framework for document databases.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of Docu.
#
#    Doqu is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Doqu is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Docu.  If not, see <http://gnu.org/licenses/>.

"""
Tokyo Tyrant extension
======================

A storage/query backend for Tokyo Tyrant.

:status: stable
:database: `Tokyo Cabinet`_, `Tokyo Tyrant`_
:dependencies: `Pyrant`_
:suitable for: general purpose

  .. _Tokyo Cabinet: http://1978th.net/tokyocabinet
  .. _Tokyo Tyrant: http://1978th.net/tokyotyrant
  .. _Pyrant: http://pypi.python.org/pypi/pyrant

"""

__all__ = ['StorageAdapter']

from doqu import dist
dist.check_dependencies(__name__)

from storage import StorageAdapter

# let backend-specific stuff register itself with managers
import converters
import lookups

