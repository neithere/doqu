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


class ValidationError(Exception):
    pass


class Property(object):
    "A model property"

    creation_cnt = 0

    def __init__(self, required=False, *args, **kw):
        self.required = required

        # info about model we are assigned to -- to be filled from outside
        self.model_instance = None
        self.attr_name = None

        # count field instances to preserve order in which they were declared
        self.creation_cnt = Property.creation_cnt
        Property.creation_cnt += 1

    def to_python(self, value):
        "Converts incoming data into correct Python form."
        return value

    def validate(self, value):
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
            raise ValueError('validate() must return None or raise ValidationError')
        return value

    def check(self, value):
        pass

class Reference(Property):
    """A reference to another model instance. Note that its class is not necessary
    as in ORMs because of relational databases' rigid schemata, but is required
    to represent data at least somehow. However, in the future some generi
    catch-all model may be introduced here.
    Another caveat is the namespace: we can easily reference an item located in
    another database but we need to keep the reference alive or proxied; anyway
    namespace should be somehow noted.
    """

    def __init__(self, model, *args, **kw):
        super(Reference, self).__init__(*args, **kw)
        # TODO check if other_model is a Model subclass
        self.other_model = model

    def validate(self, value):
        value = super(Reference, self).validate(value)
        # TODO check if value is a Model instance, if it's saved, try to save, etc.
        return value._key

    def to_python(self, value):
        storage = self.model_instance._storage
        return self.other_model(value, storage)  # a "blank" instance of referenced model, but with a key. TODO: autoreification?
