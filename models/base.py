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


from props import Property


__all__ = ['Model']

DISALLOWED_ATTRS = ('__dict__', '__metaclass__', '__module__')
DEFAULT_OPTIONS = ('must_have',)


class ModelOptions(object):
    "Model metadata" # not to be confused with metaclass ;)

    def __init__(self, custom_options_cls):
        self.model_instance = None
        self.prop_names = []
        self.props = {}
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
                raise TypeError, "'class Meta' got invalid attribute(s): %s" % ','.join(custom_options.keys())

    def set_model_instance(self, instance):
        self.model_instance = instance
        for prop in self.props.values():
            prop.model_instance = instance

    def add_prop(self, attr_name, prop):
        self.props[attr_name] = prop

        # inform prop about its model
        prop.attr_name = attr_name

        # preserve order in which attributes were declared
        self.prop_names = sorted(self.prop_names + [attr_name],
                                  key=lambda n: self.props[n].creation_cnt)

    def pre_save_property(self, name, save_related=False):
        assert self.model_instance
        p = self.props[name]
        value = getattr(self.model_instance, name)
        if p.is_reference:
            value.save
        return p.pre_save(value) # will raise ValidationError if smth is wrong


class ModelBase(type):
    "Metaclass for all models"

    def __new__(cls, name, bases, attrs):
        module = attrs.pop('__module__')
        new_class = type.__new__(cls, name, bases, attrs)

        parents = [b for b in bases if isinstance(b, ModelBase)]
        if not parents:
            return new_class

        # add empty model options (to be populated below)
        attr_meta = attrs.pop('Meta', None)
        setattr(new_class, '_meta', ModelOptions(attr_meta))

        # inherit model options from base classes
        # TODO: add extend=False to prevent inheritance (example: http://docs.djangoproject.com/en/dev/topics/forms/media/#extend)
        for base in bases:
            if hasattr(base, '_meta'):
                for name in base._meta.prop_names:
                    new_class._meta.add_prop(name, base._meta.props[name])
                if hasattr(base._meta, 'must_have'):
                    new_class._meta.must_have = base._meta.must_have

        # move prop declarations to model options
        for attr, value in attrs.iteritems():
            if attr not in DISALLOWED_ATTRS:
                if isinstance(value, Property):
                    new_class._meta.add_prop(attr, value)
                    setattr(new_class, attr, None)

        # fill some attrs from default search query    XXX  may be undesirable
        if new_class._meta.must_have:
            for k, v in new_class._meta.must_have.items():
                setattr(new_class, k, v)

        return new_class


class Model(object):
    "Wrapper for a record with predefined metadata."

    __metaclass__ = ModelBase

    # Python magic methods

    def __init__(self, key=None, storage=None, **kw):
        if self.__class__ == Model:
            raise NotImplementedError('Model must be subclassed')
        self._meta.set_model_instance(self)
        self._storage = storage
        self._key = key
        self._saved = storage and key

        ## FIXME Tyrant-/shelve-specific!
        if self._storage and self._key and not kw:
            kw = storage[self._key]
        ##

        self._data = kw.copy() # store the original data intact, even if some of it is not be used

        for name in self._meta.prop_names:
            if name in kw:
                raw_value = kw.pop(name)
                value = self._meta.props[name].to_python(raw_value) # FIXME not necessarily from storage come the value -- user could type it!
                setattr(self, name, value)
        #if kw:
        #    raise TypeError('"%s" is invalid keyword argument for model init.' % kw.keys()[0])

    def __repr__(self):
        return u'<%s %s>' % (self.__class__.__name__, unicode(self))

    def __unicode__(self):
        return "instance" #str(hash(self))

    # Public methods

    @classmethod
    def query(cls, storage):    # less concise but more appropriate name: get_query_for()
        "Returns a Query instance for all model instances within given storage."
        assert isinstance(cls, ModelBase), 'this method must be called with class, not instance'

        query = storage.query

        def _decorate_item(pk, data):
            normalized_data = dict((str(k), v) for k, v in data.iteritems())
            return cls(key=pk, storage=storage, **normalized_data)
                                           #if k in cls._meta.prop_names))
        # FIXME make this more flexible or just rely on backend wrapper:
        query._decorate = _decorate_item

        if cls._meta.must_have:
            return query.filter(**cls._meta.must_have)
        return query

    def save(self, storage, sync=True):

        # FIXME probably hack -- storage is required in Reference properties,
        #       but we want to avoid coupling model data with a storage
        #       (e.g. we may want to clone a record, etc.)
        self._storage = storage

        data = self._data.copy()

        for name in self._meta.prop_names:
            value = self._meta.pre_save_property(name, save_related=True)
            ## FIXME Tyrant-specific: None-->'None' is bad, force None-->''
            if value is None:
                value = ''
            ##
            data[name] = value

        if self._meta.must_have:
            for name in self._meta.must_have.keys():
                if name not in data:
                    data[name] = getattr(self, name)    # NOTE validation should be done using must_have constraints

        ### FIXME Tyrant- or shelve-specific! a backend wrapper should be introduced.
        #         TODO check if this is a correct way of generating an autoincremented pk
        #         ...isn't! Table database supports "setindex", "search", "genuid".
        if not self._key:
            model_label = self.__class__.__name__.lower()
            max_key = len(storage.prefix_keys(model_label))
            self._key = '%s_%s' % (model_label, max_key)
        storage[self._key] = data
        if sync:
            storage.sync()
        ###

        # If object A references B, it must ensure that B exists in the database.
        # B can have a primary key but not be saved yet, so we require a special
        # attribute that is set to True a) on save, or b) if B is instantiated
        # with both storage and PK provided. If A founds out that B is not in
        # the database, it forces saving. If B is in the database, A does not
        # care if B is synced -- it is only important that it exists at all.
        self._saved = True
