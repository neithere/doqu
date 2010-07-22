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

import datetime
import decimal
import re

from docu.backend_base import ConverterManager
from docu.document_base import Document


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
    type(None), bool, dict, float, list, long, str, tuple, unicode,
    #datetime.date, datetime.datetime,
    #Document
]
for datatype in KNOWN_TYPES:
    converter_manager.register(datatype)(NoopConverter)


@converter_manager.register(int)
class IntegerConverter(NoopConverter):
    @classmethod
    def from_db(cls, value):
        if value is None:
            return None
        return int(value)    # get rid of that <type long>

@converter_manager.register(decimal.Decimal)
class DecimalConverter(NoopConverter):
    @classmethod
    def from_db(cls, value):
        if value is None:
            return None
        return decimal.Decimal(value)
    @classmethod
    def to_db(cls, value, storage):
        return str(value)

# TODO: datetime.datetime and datetime.date converters are copied straight from
# the Tokyo Tyrant extension; we should make sure this works fine with MongoDB.

@converter_manager.register(datetime.date)
class DateConverter(object):
    """
    Stores date in RFC 3339 (without separators due to issues with comparison
    operations in TC) and represents it in Python as a `datetime.date` object::

        >>> DateConverter().from_db('')
        >>> DateConverter().from_db('20100221')
        datetime.date(2010, 2, 21)
        >>> DateConverter().from_db('201002210857')   # +time
        Traceback (most recent call last):
        ...
        ValidationError: Expected date in YYYYMMDD format, got "201002210857".

        >>> import datetime
        >>> DateConverter().to_db(datetime.date(2010, 2, 21), None)
        '20100221'

    """
    date_re = re.compile(r'^(\d{4})(\d{2})(\d{2})$')

    @classmethod
    def from_db(self, value):
        # '20100328' -> datetime.date(2010, 3, 28)
        if not value:
            return None
#        print value
        value = str(value)
        match = self.date_re.search(value)
        if not match:
            raise ValueError(u'Expected date in YYYYMMDD format, got %s.'
                             % repr(value))
        year, month, day = (int(x) for x in match.groups())
        return datetime.date(year, month, day)

    @classmethod
    def to_db(self, value, storage):
        # datetime.date(2010, 3, 28) -> '20100328'
        if not value:
            return ''
        if not isinstance(value, datetime.date):
            raise ValueError(u'Expected a datetime.date instance, got %s'
                             % repr(value))
        # XXX this line differs from TC/TT: Mongo preserves type and we don't
        # want to have an integer in regex in from_db()
        return str(value.strftime('%Y%m%d'))


@converter_manager.register(datetime.datetime)
class DateTimeConverter(object):
    """
    Stores date and time in RFC 3339 (without separators due to issues with
    comparison operations in TC) and represents it in Python as a
    `datetime.datetime` object::

        >>> DateTimeConverter().from_db('')
        >>> DateTimeConverter().from_db('20100221085701')
        datetime.datetime(2010, 2, 21, 8, 57, 01)
        >>> DateTimeConverter().from_db('2010-02-21 08:57:01')  # not for TC
        Traceback (most recent call last):
        ...
        ValidationError: Expected date and time in YYYYMMDDHHMMSS format, got "2010-02-21 08:57:01".

        >>> import datetime
        >>> DateConverter().to_db(datetime.datetime(2010, 2, 21, 8, 57, 01), None)
        '20100221085701'

    """
    date_re = re.compile(r'^(\d{4})(\d{2})(\d{2})(\d{2})(\d{2})(\d{2})$')

    @classmethod
    def from_db(self, value):
        # '20100328' -> datetime.date(2010, 3, 28)
        if not value:
            return None
        value = str(value)
        match = self.date_re.search(value)
        if not match:
            raise ValueError(u'Expected date and time in YYYYMMDDHHMM format, got %s.'
                             % repr(value))
        year, month, day, h, m, s = (int(x) for x in match.groups())
        return datetime.datetime(year, month, day, h, m, s)

    @classmethod
    def to_db(self, value, storage):
        # datetime.date(2010, 3, 28) -> '20100328'
        if not value:
            return ''
        if not isinstance(value, datetime.datetime):
            raise ValueError(u'Expected a datetime.datetime instance, got %s'
                             % repr(value))
        return str(value.strftime('%Y%m%d%H%M%S'))


@converter_manager.register(datetime.time)
class TimeConverter(object):
    @classmethod
    def from_db(self, value):
        if not value:
            return None
        value = str(value)
        h, m, s = int(value[:2]), int(value[2:4]), int(value[4:6])
        return datetime.time(h,m,s)

    @classmethod
    def to_db(self, value, storage):
        if not value:
            return ''
        if not isinstance(value, datetime.time):
            raise ValueError(u'Expected a datetime.time instance, got %s'
                             % repr(value))
        return int(value.strftime('%H%M%S'))


@converter_manager.register(Document)
class ReferenceConverter(NoopConverter):
    @classmethod
    def from_db(self, value):
        if not value:
            return None
        return str(value)   # get rid of the quirky ObjectId
    @classmethod
    def to_db(cls, value, storage):
        #return NotImplemented
        if value and hasattr(value, 'pk'):
            if value.pk:
                return value.pk
            # save related object with missing PK   XXX make this more explicit?
            value.save(storage)
        return value
