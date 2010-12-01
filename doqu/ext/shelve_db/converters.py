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

import datetime
import decimal
import re

from doqu.backend_base import ConverterManager
from doqu.document_base import Document


__all__ = ['converter_manager']


converter_manager = ConverterManager()


class NoopConverter(object):
    "Does nothing but implement the data converter API."
    @classmethod
    def from_db(cls, value):
        return value
    @classmethod
    def to_db(cls, value, storage):
        return value

KNOWN_TYPES = [
    type(None), bool, dict, float, int, list, long, str, tuple, unicode,
    datetime.date, datetime.datetime, datetime.time,
    decimal.Decimal,
    #Document
]
for datatype in KNOWN_TYPES:
    converter_manager.register(datatype)(NoopConverter)

@converter_manager.register(Document)
class ReferenceConverter(NoopConverter):
    @classmethod
    def to_db(cls, value, storage):
        #return NotImplemented
        if value and hasattr(value, 'pk'):
            if value.pk:
                return value.pk
            # save related object with missing PK   XXX make this more explicit?
            value.save(storage)
        return value
