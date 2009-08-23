# -*- coding: utf-8 -*-
#
#    Models is a framework for mapping Python classes to semi-structured data.
#    Copyright © 2009  Andrey Mikhaylenko
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

from exceptions import ValidationError


__all__ = ['Property', 'Date', 'YAMLProperty', 'JSONProperty']


class Property(object):
    "A model property"

    creation_cnt = 0

    def __init__(self, required=False, *args, **kw):
        self.required = required

        # info about model we are assigned to -- to be filled from outside
        self.model_instance = None
        self.attr_name = None

        # reference properties need additional care
        self.is_reference = False

        # count field instances to preserve order in which they were declared
        self.creation_cnt = Property.creation_cnt
        Property.creation_cnt += 1

    def to_python(self, value):
        "Converts incoming data into correct Python form."
        return value

    def pre_save(self, value):
        assert self.model_instance and self.attr_name, 'model must be initialized'

        # validate empty
        if value is None or value == '':
            if self.required:
                raise ValidationError('field %s.%s is required' % (
                        self.model_instance.__class__.__name__, self.attr_name))
            return
        return value


class Date(Property):
    ansi_date_re = re.compile(r'^\d{4}-\d{1,2}-\d{1,2}$')

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

    def pre_save(self, value):
        value = super(Date, self).pre_save(value)
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
    """An abstract class for properties which contents are serialized."""

    def to_python(self, value):
        try:
            return self.deserialize(value)
        except Exception, e:
            raise ValidationError('Tried to deserialize value, got error "%s" '
                                  'with data: %s' % (unicode(e), value))

    def pre_save(self, value):
        value = super(SerializedProperty, self).pre_save(value)
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
    """A property which contents are serialized with YAML."""

    def deserialize(self, value):
        return yaml.load(value)

    def serialize(self, value):
        return yaml.dump(value)


class JSONProperty(SerializedProperty):
    """A property which contents are serialized with JSON."""

    def deserialize(self, value):
        return json.loads(value)

    def serialize(self, value):
        return json.dumps(value)
