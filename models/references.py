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

# TODO: m2m (multiple keys listed as tokens <--> list of Model instances)

from base import Model
from exceptions import ValidationError
from props import Property


__all__ = ['Reference']


RECURSIVE_RELATIONSHIP = 'self'


class Reference(Property):
    """
    A reference to another model instance. Note that its class is not necessary
    as in ORMs because of relational databases' rigid schemata, but is required
    to represent data at least somehow. However, in the future some generic
    catch-all model may be introduced here.
    Another caveat is the namespace: we can easily reference an item located in
    another database but we need to keep the reference alive or proxied; anyway
    namespace should be somehow noted.

    `Reference(SomeModel)` is exactly equivalent to `Property(SomeModel)`.
    However, `Reference` provides additional features such as recursive
    relationships: `Reference('self')`.

    :param ref_model: referenced model: a Model subclass or the string "self"
    """

    def __init__(self, ref_model, *args, **kw):
        assert ref_model == RECURSIVE_RELATIONSHIP or issubclass(ref_model, Model), (
            'expected Model subclass or "self", but got %s' % ref_model)
        super(Reference, self).__init__(*args, **kw)
        self._ref_model = ref_model

    def contribute_to_model(self, model, attr_name):
        super(Reference, self).contribute_to_model(model, attr_name)

        value = LazyReference(self.ref_model, attr_name)

        setattr(model, attr_name, value)

    def pre_save(self, related_instance, storage):
        value = super(Reference, self).pre_save(related_instance, storage)

        # TODO: check model class (though it's not that important as in rdbms)
        if not related_instance:
            return None

        if not isinstance(related_instance, Model):
            raise ValidationError('Expected a model instance, got %s' % related_instance)

        return related_instance.save(storage)

    @property
    def ref_model(self):
        """
        Returns class of referenced model. It can be another model of the same
        (if the property was defined with "self" instead of model class).
        """
        assert self.model
        if self._ref_model == RECURSIVE_RELATIONSHIP:
            return self.model
        else:
            return self._ref_model


class LazyReference(object):
    """
    Refence descriptor. Allows to defer fetching model data from DB.
    """
    def __init__(self, related_model, attr_name):
        self.cache = {}
        self.related_model = related_model
        self.attr_name = attr_name

    def __get__(self, instance, owner):
        if not instance:
            return self

        cached = self.cache.get(instance, None)
        if cached:
            return cached

        if not self.attr_name in instance.__dict__:
            return

        value = instance.__dict__[self.attr_name]

        if not value:
            return None

        return self._get_related(instance, value)

    def __set__(self, instance, related_instance):
        if instance is None:
            raise AttributeError('%s must be accessed via instance' % self.attr_name)

        self.cache[instance] = None

        if not related_instance:
            return

        if not isinstance(related_instance, self.related_model):
            raise AttributeError('cannot assign %s: %s must be a %s instance'
                                 % (related_instance, self.attr_name,
                                    self.related_model.__name__))

        # value is a related model instance
        self.cache[instance] = related_instance

        instance.__dict__[self.attr_name] = related_instance._key

    def _get_related(self, instance, value):

        assert instance._storage, 'cannot fetch related objects if storage is not defined'

        try:
            return instance._storage.get(self.related_model, value)
        except KeyError:
            raise ValueError(u'could not find %s object with primary key "%s"'
                             % (self.related_model.__name__, value))
