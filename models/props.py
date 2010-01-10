# -*- coding: utf-8 -*-
#
#    Models is a framework for mapping Python classes to semi-structured data.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of Models.
#
#    Models is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Models is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Models.  If not, see <http://gnu.org/licenses/>.


# for serialized properties:
import yaml
import json
# for Date and DateTime:
import datetime

import re

from base import Model
from exceptions import ValidationError


__all__ = ['Property', 'Date', 'YAMLProperty', 'JSONProperty']


class Property(object):
    """
    A model property. Usage::

        class Foo(Model):
            name = Property(unicode, required=True)
            age  = Property(int)
            bio  = Property()  # unicode by default
    """

    creation_cnt = 0
    python_type = unicode

    def __init__(self, datatype=None, required=False, *args, **kw):
        if datatype:
            self.python_type = datatype

        self.required = required

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

        self.model = model
        self.attr_name = attr_name

        model._meta.add_prop(self)

        setattr(model, attr_name, None)

    def to_python(self, value):
        "Converts incoming data into correct Python form."
        if isinstance(self.python_type, Model) and not isinstance(value, Model):
            raise TypeError('expected %s instance, got "%s"' %
                            (type(self.python_type).__name__, value))
        return self.python_type(value)

    def pre_save(self, value, storage):
        assert self.model and self.attr_name, 'model must be initialized'

        # validate empty value
        if value is None or value == '':
            if self.required:
                raise ValidationError('property %s.%s is required' % (
                                      self.model.__name__, self.attr_name))
            return None

        return value


class Number(Property):
    """
    Equivalent to `Property(int)`.
    """
    python_type = int


class FloatNumber(Number):
    """
    Equivalent to `Property(float)`.
    """
    python_type = float


class Date(Property):
    """
    A property which stores dates in RFC 3339 and represents them in Python as
    `datetime.date` objects.
    """
    ansi_date_re = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')
    python_type = datetime.date

    def to_python(self, value):
        if not value:
            return
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
        if value:
            try:
                return value.isoformat()
            except (AttributeError, ValueError), e:
                raise ValidationError(u'Bad date value "%s": %s' % (value, e))


'''
class DateTime(Property):

    def pre_save(self, value):
        value = super(DateTime, self).pre_save(value)
        if value:
            return value.isoformat(sep=' ')

    def to_python(self, value):
        if value:
            return datetime.datetime.strptime(value, u'%Y-%M-%d')
'''


class SerializedProperty(Property):
    """
    An abstract class for properties which contents are serialized.
    """

    # NOTE: python_type is not pre-determined

    def to_python(self, value):
        try:
            return self.deserialize(value)
        except Exception, e:
            raise ValidationError('Tried to deserialize value, got error "%s" '
                                  'with data: %s' % (unicode(e), value))

    def pre_save(self, value, storage):
        value = super(SerializedProperty, self).pre_save(value, storage)
        try:
            return self.serialize(value)
        except Exception, e:
            raise ValidationError('Tried to serialize value, got error "%s" '
                                  'with data: %s' % (unicode(e), value))

    def deserialize(self, value):
        raise NotImplementedError

    def serialize(self, value):
        raise NotImplementedError


class YAMLProperty(SerializedProperty):
    """
    A property which contents are serialized with YAML.
    """

    def deserialize(self, value):
        return yaml.load(value)

    def serialize(self, value):
        return yaml.dump(value)


class JSONProperty(SerializedProperty):
    """
    A property which contents are serialized with JSON.
    """

    def deserialize(self, value):
        return json.loads(value)

    def serialize(self, value):
        return json.dumps(value)
