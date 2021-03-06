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
Document Fields
===============

.. versionadded:: 0.23

.. note::

    This abstraction is by no means a complete replacement for the normal
    approach of semantic grouping. Please use it with care. Also note that the
    API can change. The class can even be removed in future versions of Docu.

"""
from .base import Field
from .files import FileField, ImageField

__all__ = ['Field', 'FileField', 'ImageField']
