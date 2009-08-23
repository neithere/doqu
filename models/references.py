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


from base import Model
from exceptions import ValidationError
from props import Property


__all__ = ['Reference']


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

    def to_python(self, value):
        if not value:
            return

        if isinstance(value, Model):
            return value

        storage = self.model_instance._storage
        return self.other_model(value, storage)  # a "blank" instance of referenced model, but with a key. TODO: autoreification?

    def pre_save(self, value):
        # TODO: check model class (though it's not that important as in rdbms)
        value = super(Reference, self).pre_save(value)
        if not value:
            return

        if not isinstance(value, Model):
            raise ValidationError('Expected a model intance, got %s' % value)

        # XXX this is ugly:
        if not value._saved:
            storage = value._storage or self.model_instance._storage
            value.save(storage)

        return value._key
