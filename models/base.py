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

from backends.base import BaseStorage


__all__ = ['Model']


DEFAULT_OPTIONS = ('must_have',)


class ModelOptions(object):
    "Model metadata" # not to be confused with metaclass ;)

    def __init__(self, custom_options_cls):
        self.props = {}
        self._prop_names_cache = None
        self.must_have = None    # conditions for searching model instances within a storage

        if custom_options_cls:    # the 'class Meta: ...' within model declaration
            custom_options = custom_options_cls.__dict__.copy()
            for name in custom_options_cls.__dict__:
                if name.startswith('_'):
                    del custom_options[name]
            for name in DEFAULT_OPTIONS:
                if name in custom_options:
                    setattr(self, name, custom_options.pop(name))
            if custom_options:
                s = ', '.join(custom_options.keys())
                raise TypeError("Invalid attribute(s) in 'class Meta': %s" % s)

    def add_prop(self, prop):
        self._prop_names_cache = None
        self.props[prop.attr_name] = prop

    @property
    def prop_names(self):
        """
        Returns names of model properties in the order in which they were declared.
        """
        if not self._prop_names_cache:
            self._prop_names_cache = sorted(self.props, key=lambda n: self.props[n].creation_cnt)
        return self._prop_names_cache


class ModelBase(type):
    "Metaclass for all models"

    def __new__(cls, name, bases, attrs):
        module = attrs.pop('__module__')
        model = type.__new__(cls, name, bases, attrs)

        parents = [b for b in bases if isinstance(b, ModelBase)]
        if not parents:
            return model

        # add empty model options (to be populated below)
        attr_meta = attrs.pop('Meta', None)
        setattr(model, '_meta', ModelOptions(attr_meta))

        # inherit model options from base classes
        # TODO: add extend=False to prevent inheritance (example: http://docs.djangoproject.com/en/dev/topics/forms/media/#extend)
        for base in bases:
            if hasattr(base, '_meta'):
                model._meta.props.update(base._meta.props)  # TODO: check if this is secure
                for name, prop in base._meta.props.iteritems():
                    model._meta.add_prop(prop)
                for name in DEFAULT_OPTIONS:
                    if hasattr(base._meta, name):
                        inherited_value = getattr(base._meta, name)
                        setattr(model._meta, name, inherited_value)

        # move prop declarations to model options
        for attr_name, value in attrs.iteritems():
            if hasattr(value, 'contribute_to_model'):
                value.contribute_to_model(model, attr_name)
            else:
                setattr(model, attr_name, value)

        # fill some attrs from default search query    XXX  may be undesirable
        if model._meta.must_have:
            for k, v in model._meta.must_have.items():
                setattr(model, k, v)

        return model


class Model(object):
    """
    Wrapper for a record with predefined metadata.
    """

    __metaclass__ = ModelBase

    # Python magic methods

    def __init__(self, key=None, storage=None, **kw):
        if self.__class__ == Model:
            raise NotImplementedError('Model must be subclassed')
        self._storage = storage
        self._key = key

        self._data = kw.copy() # store the original data intact, even if some of it is not be used

        names = [name for name in self._meta.prop_names if name in kw]

        self.__dict__.update((name, kw.pop(name)) for name in names)

    def __repr__(self):
        return u'<%s %s>' % (type(self).__name__, unicode(self))

    def __unicode__(self):
        return "instance" #str(hash(self))

    # Public methods

    @classmethod
    def query(cls, storage):    # less concise but more appropriate name: get_query_for()
        """
        Returns a Query instance for all model instances within given storage.
        """
        assert isinstance(cls, ModelBase), 'this method must be called with class, not instance'

        items = storage.get_query(model=cls)

        if cls._meta.must_have:
            return items.where(**cls._meta.must_have)
        return items

    def save(self, storage=None, sync=True):

        if not storage and not self._storage:
            raise AttributeError('cannot save model instance: storage is not '
                                 'defined neither in instance nor as argument '
                                 'for the save() method')

        if storage:
            assert isinstance(storage, BaseStorage), (
                'expected models.backends.base.BaseStorage subclass, got %s' % storage)

            # FIXME probably hack -- storage is required in Reference properties,
            #       but we want to avoid coupling model data with a storage
            #       (e.g. we may want to clone a record, etc.)
            #       However, this is the way it's done e.g. in Django.
            self._storage = storage
        else:
            storage = self._storage

        data = self._data.copy()

        # prepare properties defined in the model
        for name in self._meta.prop_names:
            value = self.pre_save_property(name, storage)   #, save_related=True)
            data[name] = value

        # make sure required properties will go into the storage
        if self._meta.must_have:
            for name in self._meta.must_have.keys():
                if name not in data:
                    data[name] = getattr(self, name)    # NOTE validation should be done using must_have constraints

        # let the storage backend prepare data and save it to the actual storage
        self._key = storage.save(
            model = type(self),
            data = data,
            primary_key = self._key,
        )
        return self._key

    def pre_save_property(self, name, storage):
        p = self._meta.props[name]
        value = getattr(self, name)
        return p.pre_save(value, storage) # will raise ValidationError if smth is wrong
