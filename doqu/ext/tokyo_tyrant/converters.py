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

from managers import converter_manager
from doqu.document_base import Document


@converter_manager.register(type(None))
class NoneTypeConverter(object):
    "Converts `None`. Only outgoing."
    @classmethod
    def from_db(cls, value):
        # this cannot be, ok?
        raise NotImplementedError

    @classmethod
    def to_db(cls, value, storage):
        return ''

@converter_manager.register(unicode)
@converter_manager.register(str)
class StringConverter(object):
    @classmethod
    def from_db(cls, value):
        try:
            return unicode(value)
        except UnicodeDecodeError:
            return value.decode('utf-8')

    @classmethod
    def to_db(cls, value, storage):
        return unicode(value)

@converter_manager.register(bool)
class BooleanConverter(object):
    @classmethod
    def from_db(self, value):
        value = value or 0
        try:
            value = int(value)
        except ValueError:
            pass
        return bool(value)

    @classmethod
    def to_db(self, value, storage):
        return '1' if value else '0'

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
        return int(value.strftime('%Y%m%d'))


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
        return int(value.strftime('%Y%m%d%H%M%S'))


@converter_manager.register(decimal.Decimal)
class DecimalConverter(object):
    @classmethod
    def from_db(self, value):
        if not value:
            return None
        return decimal.Decimal(value)

    @classmethod
    def to_db(self, value, storage):
        if value is None:
            return ''
        return unicode(value)


@converter_manager.register(int)
class IntegerConverter(object):
    """
    Converts integer values::

        >>> IntegerConverter().from_db('')
        >>> IntegerConverter().from_db('0')
        0
        >>> IntegerConverter().from_db('1')
        1
        >>> IntegerConverter().from_db('1.5')
        Traceback (most recent call last):
        ...
        ValueError: invalid literal for int() with base 10: '1.5'
        >>> IntegerConverter().from_db('x')
        Traceback (most recent call last):
        ...
        ValueError: invalid literal for int() with base 10: 'x'

        >>> IntegerConverter().to_db(2, None)
        '2'
        >>> IntegerConverter().to_db(None, None)
        ''

    """
    @classmethod
    def from_db(self, value):
        return None if value == '' else int(value)

    @classmethod
    def to_db(self, value, storage):
        return '' if value is None else str(int(value))


@converter_manager.register(float)
class FloatConverter(object):
    """
    Converts floating point numbers::

        >>> FloatConverter().from_db('')
        >>> FloatConverter().from_db('0')
        0.0
        >>> FloatConverter().from_db('1')
        1.0
        >>> FloatConverter().from_db('1.5')
        1.5
        >>> FloatConverter().from_db('x')
        Traceback (most recent call last):
        ...
        ValueError: invalid literal for float(): 'x'

        >>> FloatConverter().to_db(2, None)
        '2.0'
        >>> FloatConverter().to_db(None, None)
        ''

    """
    @classmethod
    def from_db(self, value):
        return None if value == '' else float(value)

    @classmethod
    def to_db(self, value, storage):
        return '' if value is None else str(float(value))


@converter_manager.register(list)
@converter_manager.register(tuple)
class ListConverter(object):
    """
    A property which stores lists as comma-separated strings and converts them
    back to Python `list`::

        >>> ListConverter().from_db('')
        []
        >>> ListConverter().from_db('foo')
        ['foo']
        >>> ListConverter().from_db('foo 123')
        ['foo 123']
        >>> ListConverter().from_db('foo 123, bar 456')
        ['foo 123', 'bar 456']

        >>> ListConverter().to_db(['foo 123', 'bar 456'], None)
        'foo 123, bar 456'

    """
    @classmethod
    def from_db(self, value):
        return value.split(', ') if value else []

    @classmethod
    def to_db(self, value, storage):
        return ', '.join(value)


@converter_manager.register(Document)
class ReferenceConverter(object):
    @classmethod
    def from_db(cls, value):
        #print 'ReferenceConverter.from_db(%s)' % repr(value)
        return value
        #return NotImplemented

    @classmethod
    def to_db(cls, value, storage):
        #return NotImplemented
        if value and hasattr(value, 'pk'):
            if value.pk:
                return value.pk
            # save related object with missing PK   XXX make this more explicit?
            value.save(storage)
        return value

