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


import re

from exceptions import ValidationError


__all__ = ['Property']


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
        # FIXME this validates AND cleans/prepares data. Must be separated.

        assert self.model_instance and self.attr_name, 'model must be initialized'

        # validate empty
        if value is None:
            if self.required:
                raise ValidationError('field is required')
            return
        # validate non-empty (will raise ValidationError on bad value)
        #self.to_python(value)
        if self.check(value):
            raise ValueError('pre_save() must return None or raise ValidationError')
        return value

    def check(self, value):
        pass
