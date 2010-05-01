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


# for Date and DateTime:
import datetime

import re

from pymodels.base import Model
from pymodels.exceptions import ValidationError


__all__ = ('Property', 'Boolean', 'Date', 'DateTime', 'Float', 'Integer',
           'List', 'Number')


class Property(object):
    """
    A model property. Usage::

        >>> from pymodels import *
        >>> class Foo(Model):
        ...     name = Property(unicode, required=True)
        ...     age  = Property(int, default=123)
        ...     bio  = Property()  # unicode by default

        >>> Property(unicode).to_python('')
        ''
        >>> Property(unicode, default='hello').to_python('')
        'hello'

        >>> Property().pre_save(u'Hello!', None)
        u'Hello!'
        >>> Property().pre_save(2.5, None)
        2.5
        >>> Property().pre_save(True, None)
        True
        >>> Property().pre_save(False, None)
        False
        >>> prop_required = Property(required=True)
        >>> prop_required.model = lambda x:x
        >>> prop_required.model.__name__ = 'FakeModel'
        >>> prop_required.attr_name = 'fake_field'
        >>> prop_required.pre_save(True, None)
        True
        >>> prop_required.pre_save(False, None)
        False
        >>> prop_required.pre_save('', None)
        Traceback (most recent call last):
        ...
        ValidationError: property FakeModel.fake_field is required
        >>> prop_required.pre_save(None, None)
        Traceback (most recent call last):
        ...
        ValidationError: property FakeModel.fake_field is required

    """

    creation_cnt = 0
    python_type = unicode    # can be any type or even list of them; note that
                             # any iterable will be interpreted as list of types

    def __init__(self, datatype=None, required=False, default=None, label=None):
        if datatype:
            self.python_type = datatype

        self.required = required
        self.default_value = default

        # information that can be useful for display purposes
        self.label = label

        # info about model we are assigned to -- to be filled from outside
        self.model = None
        self.attr_name = None

        # count field instances to preserve order in which they were declared
        self.creation_cnt = Property.creation_cnt
        Property.creation_cnt += 1

    def contribute_to_model(self, model, attr_name):
        """
        Expects a model and attribute name. Binds self to the model and modifies
        the model as required (including adding self to the model options).
        Can be subclassed to introduce more complex behaviour including
        aggregated properties.
        """
        if self.model:
            # already bound, ensure inheritance
            assert issubclass(model, self.model), (
                'Property %s.%s can only be bound to %s through model '
                'inheritance.' % (self.model.__name__, self.attr_name, model))
        else:
            self.model = model

        if self.attr_name:
            # already bound, make sure name is kept the same
            assert self.attr_name == attr_name, (
                'The property is already bound to %s as "%s". Renaming to "%s"'
                ' is not allowed.' % (self.model.__name__, self.attr_name,
                                      attr_name))
        else:
            self.attr_name = attr_name

        model._meta.add_prop(self)

        setattr(model, attr_name, None)

    def get_default(self):
        if self.default_value:
            if hasattr(self.default_value, '__call__'):
                return self.default_value()
            return self.default_value
        return None


    def to_python(self, value):
        "Converts incoming data into correct Python form."

        # handle reference    XXX is this a correct place for that?
        if isinstance(self.python_type, Model) and not isinstance(value, Model):
            raise TypeError('expected %s instance, got "%s"' %
                            (type(self.python_type).__name__, value))

        # TODO: decide what to do if value in DB cannot be converted to Python type:
        # a) ignore; b) let exception propagate; c) wrap TypeError to provide
        # details on broken property, at least its name; d) do anything else?
        if value:
            return self.pythonize_non_empty(value)

        default = self.get_default()
        if default:
            return default

        return self.pythonize_empty(value)

    def pythonize_empty(self, value):
        """
        Returns correctly pythonized representation of given "empty" value.
        An empty value is a value for which ``bool(value)`` returns `False`.
        """
        return value

    def pythonize_non_empty(self, value):
        """
        Returns correctly pythonized representation of given "non-empty" value.
        A non-empty value is a value for which ``bool(value)`` returns `True`.
        """
        if self.python_type is unicode and not isinstance(value, unicode):
            # attempt to properly convert to Unicode (it is the default data type)
            return value.decode('UTF-8')
        else:
            if hasattr(self.python_type, '__iter__'):
                types = self.python_type
                for type_ in types:
                    try:
                        return type_(value)
                    except:
                        pass
                raise ValueError('could not convert "%s" to any of %s' %(value,
                                                                         types))
            else:
                return self.python_type(value)

    def pre_save(self, value, storage):
        assert self.model and self.attr_name, 'model must be initialized'

        # validate empty value
        if value is None or value == '':

            default = self.get_default()
            if default:
                return default
            if self.required:
                raise ValidationError('property %s.%s is required' % (
                                      self.model.__name__, self.attr_name))
            return None

        return value


class Boolean(Property):
    """
    A property which stores logical values: `True` and `False`.

        # from database:

        >>> Boolean().to_python(1)
        True
        >>> Boolean().to_python('a')
        True

        >>> Boolean().to_python(0)
        False
        >>> Boolean().to_python('')
        False
        >>> Boolean().to_python('0')
        False

        # to database:

        >>> Boolean().pre_save(True, 'storage')
        1
        >>> Boolean().pre_save(1, 'storage')
        1
        >>> Boolean().pre_save('a', 'storage')
        1

        >>> Boolean().pre_save(False, 'storage')
        0
        >>> Boolean().pre_save(0, 'storage')
        0
        >>> Boolean().pre_save('', 'storage')
        0

    """
    python_type = bool

    def pythonize_empty(self, value):
        return self.python_type(value)

    def pythonize_non_empty(self, value):
        try:
            value = int(value)
        except ValueError:
            pass
        return self.python_type(value)

    def pre_save(self, value, storage):
        return 1 if value else 0


class Number(Property):
    """
    A property which stores numbers of different types. If a value cannot be
    converted to `int`, it is converted to `float`.

        >>> number_nullable = Number()
        >>> number_nullable.to_python('')
        >>> number_nullable.to_python(0)
        0
        >>> number_nullable.to_python('1')
        1
        >>> number_nullable.to_python('1.5')
        1.5

        >>> number_nullable.pre_save(2, None)
        2
        >>> number_nullable.pre_save(2.5, None)
        2.5

        >>> number_required = Number(required=True)
        >>> number_required.model = lambda x:x
        >>> number_required.model.__name__ = 'FakeModel'
        >>> number_required.attr_name = 'fake_field'
        >>> number_required.pre_save('', None)
        Traceback (most recent call last):
        ...
        ValidationError: property FakeModel.fake_field is required
        >>> number_required.pre_save(0, None)
        0
        >>> number_required.pre_save(1, None)
        1

    """
    python_type = int, float

    def pythonize_empty(self, value):
        return value if value == 0 else None


class Integer(Number):
    """
    Equivalent to `Property(int)` with more accurate processing::

        >>> Integer().to_python('')
        >>> Integer().to_python(0)
        0
        >>> Integer().to_python('1')
        1
        >>> Integer().to_python('1.5')
        Traceback (most recent call last):
        ...
        ValueError: invalid literal for int() with base 10: '1.5'
        >>> Integer().to_python('x')
        Traceback (most recent call last):
        ...
        ValueError: invalid literal for int() with base 10: 'x'

        >>> Integer().pre_save(2, None)
        2

    """
    python_type = int


class Float(Number):
    """
    Equivalent to `Property(float)` with more accurate processing::

        >>> Float().to_python('')
        >>> Float().to_python(0)
        0.0
        >>> Float().to_python('1')
        1.0
        >>> Float().to_python('1.5')
        1.5

        >>> Float().pre_save(2.5, None)
        2.5

    """
    python_type = float

    def pythonize_empty(self, value):
        return 0.0 if value == 0 else None


class Date(Property):
    """
    A property which stores date in RFC 3339 and represents it in Python as
    a `datetime.date` object::

        >>> Date().to_python('')
        >>> Date().to_python('2010-02-21')
        datetime.date(2010, 2, 21)
        >>> Date().to_python('2010-02-21 08:57')
        Traceback (most recent call last):
        ...
        ValidationError: Enter a valid date in YYYY-MM-DD format.

        >>> import datetime
        >>> Date().pre_save(datetime.date(2010, 2, 21), None)
        '2010-02-21'

    """
    ansi_date_re = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')
    python_type = datetime.date

    def pythonize_empty(self, value):
        return None

    def pythonize_non_empty(self, value):
        if isinstance(value, datetime.date):
            return value
        if not Date.ansi_date_re.search(value):
            raise ValidationError('Enter a valid date in YYYY-MM-DD format.')
        try:
            return datetime.date(*[int(x) for x in value.split('-')])
        except ValueError, e:
            raise ValidationError(u'Invalid date: %s' % e)

    def pre_save(self, value, storage):
        value = super(Date, self).pre_save(value, storage)
        if not value:
            return
        if not isinstance(value, datetime.date):
            raise ValidationError(u'Expected a datetime.date instance, got "%s"'
                                  % value)
        try:
            return value.isoformat()
        except (AttributeError, ValueError), e:
            raise ValidationError(u'Bad date value "%s": %s' % (value, e))


class DateTime(Property):
    """
    A property which stores date and time in RFC 3339 and represents them in
    Python as a `datetime.date` object::

        >>> DateTime().to_python('')
        >>> DateTime().to_python('2010-02-21')
        Traceback (most recent call last):
        ...
        ValidationError: Bad datetime value "2010-02-21"
        >>> DateTime().to_python('2010-02-21 08:57')
        datetime.datetime(2010, 2, 21, 8, 57)

        >>> import datetime
        >>> DateTime().pre_save(datetime.datetime(2010, 2, 21, 8, 57), None)
        '2010-02-21 08:57:00'

    """
    python_type = datetime.datetime

    POSSIBLE_FORMATS = (
        '%Y-%m-%dT%H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S.%f',
        '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M',
    )

    def pythonize_empty(self, value):
        return None

    def pythonize_non_empty(self, value):
        for fmt in self.POSSIBLE_FORMATS:
            try:
                return datetime.datetime.strptime(value, fmt)
            except ValueError as error:
                pass
        raise ValidationError(u'Bad datetime value "%s"' % value)

    def pre_save(self, value, storage):
        value = super(DateTime, self).pre_save(value, storage)
        if value:
            return value.isoformat(sep=' ')


class List(Property):
    """
    A property which stores lists as comma-separated strings and converts them
    back to Python `list`::

        >>> List().to_python('')
        []
        >>> List().to_python('foo')
        ['foo']
        >>> List().to_python('foo 123')
        ['foo 123']
        >>> List().to_python('foo 123, bar 456')
        ['foo 123', 'bar 456']

        >>> List().pre_save(['foo 123', 'bar 456'], None)
        'foo 123, bar 456'

    """
    python_type = list

    def pythonize_empty(self, value):
        return []

    def pythonize_non_empty(self, value):
        return value.split(', ')

    def pre_save(self, value, storage):
        value = super(List, self).pre_save(value, storage)
        if not hasattr(value, '__iter__'):
            raise TypeError('expected iterable, got %s' % value)
        return ', '.join(value)

