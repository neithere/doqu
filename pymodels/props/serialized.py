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


# for serialized properties:
import yaml
import json

from pymodels.base import Model
from pymodels.props import Property
from pymodels.exceptions import ValidationError


__all__ = ('YAMLProperty', 'JSONProperty')


class SerializedProperty(Property):
    """
    An abstract class for properties which contents are serialized.
    """

    # NOTE: python_type is not pre-determined

    def pythonize_non_empty(self, value):
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
