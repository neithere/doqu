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

# TODO: m2m (multiple keys listed as tokens <--> list of Model instances)

from pymodels.base import Model
from pymodels.exceptions import ValidationError
from pymodels.props import Property


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

    def __init__(self, ref_model, related_name=None, *args, **kw):
        assert ref_model == RECURSIVE_RELATIONSHIP or issubclass(ref_model, Model), (
            'expected Model subclass or "self", but got %s' % ref_model)
        super(Reference, self).__init__(*args, **kw)
        self._ref_model = ref_model
        self.related_name = related_name
    
    def contribute_to_model(self, model, attr_name):
        super(Reference, self).contribute_to_model(model, attr_name)

        value = LazyReference(self.ref_model, attr_name)

        setattr(model, attr_name, value)

        # contribute to the referenced model too
        related_name = self.related_name or model._meta.auto_label + 's'
        if related_name in self.ref_model._meta.props:
            raise NameError('Cannot define backward relation to %s: model %s '
                            'already has an attribute named "%s"'
                            % (model, self.ref_model, related_name))
        descriptor = BackwardRelation(model, attr_name)
        setattr(self.ref_model, related_name, descriptor)
        # allow introspection
        referenced_by = self.ref_model._meta.referenced_by
        referenced_by.setdefault(model, []).append(attr_name)

    def pre_save(self, related_instance, storage):
        value = super(Reference, self).pre_save(related_instance, storage)

        # TODO: check model class (though it's not that important as in rdbms)
        if not related_instance:
            return None

        if not isinstance(related_instance, Model):
            raise ValidationError(u'Expected a model instance, got %s' % related_instance)

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
            raise AttributeError(u'%s must be accessed via instance' % self.attr_name)

        self.cache[instance] = None

        if not related_instance:
            return

        if not isinstance(related_instance, self.related_model):
            raise AttributeError(u'cannot assign %s: %s must be a %s instance'
                                 % (related_instance, self.attr_name,
                                    self.related_model.__name__))

        # value is a related model instance
        self.cache[instance] = related_instance

        instance.__dict__[self.attr_name] = related_instance.pk

    def _get_related(self, instance, value):
        if not instance._state.storage:
            raise ValueError(u'cannot fetch related objects for model instance '
                             'which does not define a storage')

        try:
            return instance._state.storage.get(self.related_model, value)
        except KeyError:
            raise ValueError(u'could not find %s object with primary key "%s"'
                             % (self.related_model.__name__, value))


class BackwardRelation(LazyReference):
    """
    Prepares and returns a query on objects that reference given instance by
    given attribute. Basic usage::

        class Author(Model):
            name = Property()
        
        class Book(Model):
            name = Property()
            author = Reference(Author, related_name='books')
        
        john = Author(name='John Doe')
        book_one = Book(name='first book', author=john)
        book_two = Book(name='second book', author=john)
        
        # (...save them all...)

        print john.books   # -->   [<Book object>, <Book object>]
    
    """
    def __init__(self, related_model, attr_name):
        self.cache = {}
        self.related_model = related_model
        self.attr_name = attr_name

    def __get__(self, instance, owner):
        if not instance._state.storage:
            raise ValueError(u'cannot fetch referencing objects for model'
                             ' instance which does not define a storage')

        if not instance.pk:
            raise ValueError(u'cannot search referencing objects for model'
                             ' instance which does not have primary key')

        query = self.related_model.objects(instance._state.storage)
        return query.where(**{self.attr_name: instance.pk})

    def __set__(self, instance, new_references):
        # TODO: 1. remove all existing references, 2. set new ones.
        # (there may be validation issues)
        raise NotImplementedError('sorry')

