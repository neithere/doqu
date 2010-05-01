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

import re
from backends.base import BaseStorage


__all__ = ['Model']


IDENTITY_DICT_NAME = 'must_have'
NEGATED_IDENTITY_DICT_NAME = 'must_not_have'


def make_label(class_name):
    """
    Returns a pretty readable name based on the class name.
    """
    # This is taken from Django:
    # Calculate the verbose_name by converting from InitialCaps to "lowercase with spaces".
    return re.sub('(((?<=[a-z])[A-Z])|([A-Z](?![A-Z]|$)))', ' \\1',
                  class_name).lower().strip()


class ModelState(object):
    def __init__(self):
        self.storage = None
        self.key = None
        self.data = None

    def __eq__(self, other):
        if self.storage and self.key and other:
            if self.storage == other.storage and self.key == other.key:
                return True
        return False

    def clone(self):
        c = type(self)()
        c.update(**self.__dict__)
        return c

    def update(self, storage=None, key=None, data=None):
        """
        Updates model state with given values. Empty values are *ignored*. You
        cannot reset the state or its parts by passing None or otherwise "false"
        values to update(). Do it by modifying the attributes directly.
        """
        if not any([storage, key, data]):
            # ignore empty values
            return
        self.storage = storage or self.storage
        self.key = key or self.key
        self.data = self.data if data is None else data.copy()


class ModelOptions(object):
    "Model metadata" # not to be confused with metaclass ;)

    def __init__(self, custom_options_cls):
        self.props = {}
        self._prop_names_cache = None

        # conditions for searching model instances within a storage and
        # validating them before saving:
        self.must_have = None
        self.must_not_have = None

        self.label = None
        self.label_plural = None
        self.auto_label = None

        if custom_options_cls:    # the 'class Meta: ...' within model declaration
            custom_options = custom_options_cls.__dict__.copy()
            for name in custom_options_cls.__dict__:
                if name.startswith('_'):
                    del custom_options[name]
            if IDENTITY_DICT_NAME in custom_options:
                setattr(self, IDENTITY_DICT_NAME, custom_options.pop(IDENTITY_DICT_NAME))
            if NEGATED_IDENTITY_DICT_NAME in custom_options:
                setattr(self, NEGATED_IDENTITY_DICT_NAME,
                        custom_options.pop(NEGATED_IDENTITY_DICT_NAME))
            if custom_options:
                s = ', '.join(custom_options.keys())
                raise TypeError("Invalid attribute(s) in 'class Meta': %s" % s)

        self.referenced_by = {}    # { model: [attr_name1, attr_name2] }

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
        model = type.__new__(cls, name, bases, attrs)

        parents = [b for b in bases if isinstance(b, ModelBase)]
        if not parents:
            return model

        # add empty model options (to be populated below)
        attr_meta = attrs.pop('Meta', None)
        setattr(model, '_meta', ModelOptions(attr_meta))

        # provide a nice label    TODO: allow to override, add plural form
        model._meta.label = make_label(model.__name__)
        model._meta.label_plural = model._meta.label + 's'
        # this one is for URLs, automatically added relation descriptors, etc.,
        # so it must not contain spaces and must not depend on i18n:
        model._meta.auto_label = make_label(model.__name__).replace(' ', '_')

        # inherit model options from base classes
        # TODO: add extend=False to prevent inheritance (example: http://docs.djangoproject.com/en/dev/topics/forms/media/#extend)
        for base in bases:
            if hasattr(base, '_meta'):
                model._meta.props.update(base._meta.props)  # TODO: check if this is secure
                for name, prop in base._meta.props.iteritems():
                    model._meta.add_prop(prop)
                    #if hasattr(prop, 'ref_model'):
                    prop.contribute_to_model(model, name)
                for name in IDENTITY_DICT_NAME, NEGATED_IDENTITY_DICT_NAME:
                    if hasattr(base._meta, name):
                        inherited = getattr(base._meta, name) or {}
                        current = getattr(model._meta, name) or {}
                        combined = dict(inherited, **current)
                        setattr(model._meta, name, combined)

        # move prop declarations to model options
        for attr_name, value in attrs.iteritems():
            if hasattr(value, 'contribute_to_model'):
                value.contribute_to_model(model, attr_name)
            else:
                setattr(model, attr_name, value)

        # inherit relations so that backward relation descriptors are created
        # for each model in the inheritance chain (e.g. Goal.tasks and
        # Goal.delegated_tasks)
        #for base in bases:
        #    if hasattr(base, '_meta'):
        #        print base._meta.props

        # fill some attrs from default search query    XXX  may be undesirable
        if model._meta.must_have:
            for k, v in model._meta.must_have.items():
                if not '__' in k:
                    setattr(model, k, v)

        return model


class Model(object):
    """
    Wrapper for a record with predefined metadata.

    Usage::

        >>> from pymodels import Model, Property
        >>> class Note(Model):
        ...     text = Property()
        ...
        ...     class Meta:
        ...         must_have = {'is_note': True}
        ...
        ...     def __unicode__(self):
        ...         return unicode(self.text)

    To save model instances and retrieve them you will want a storage::

        >>> from pymodels import get_storage
        >>> db = get_storage(backend='pymodels.backends.tokyo_tyrant',
        ...                  port=1983)

        # and another one, just for testing (yep, the real storage is the same)
        >>> other_db = get_storage(backend='pymodels.backends.tokyo_tyrant',
        ...                        port=1983)

        # let's make sure the storage is empty
        >>> db.clear()

    See documentation on methods for more details.

    """

    __metaclass__ = ModelBase

    # Python magic methods

    def __eq__(self, other):
        """
        # unsaved instances are never equal
        >>> Note() == Note()
        False
        >>> Note(text='foo') == Note(text='bar')
        False

        # saved instances are equal if they have the same key in same storage
        # even if their data differs
        >>> note1 = Note(text='foo')
        >>> note1.save(db)
        u'1'
        >>> note1.text = 'quux'
        >>> note1_retrieved = db.get(Note, note1.pk)
        >>> note1 == note1_retrieved
        True

        # saved instances are different if they have different keys
        >>> note2 = Note(text='bar')
        >>> note2.save(db)
        u'2'
        >>> note1 == note2
        False

        # saved instances are different if they have different storages
        # even if their keys are the same
        >>> note2.save_as(note1.pk, other_db)
        <Note bar>
        >>> note1 == note2
        False

        """
        if not other:
            return False
        return self._state == other._state

    def __init__(self, **kw):
        if self.__class__ == Model:
            raise NotImplementedError('Model must be subclassed')

        # NOTE: state must be filled from outside
        self._state = ModelState()

        names = [name for name in self._meta.prop_names if name in kw]

        self.__dict__.update((name, kw.pop(name)) for name in names)

        if kw:
            raise NameError('Unknown properties: %s' % ', '.join(kw.keys()))

    def __repr__(self):
        try:
            u = unicode(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = u'[bad unicode data]'
        except TypeError:
            u = u'[bad type in __unicode__]'
        r = u'<%s %s>' % (type(self).__name__, u)
        return r.encode('utf-8')

    def __unicode__(self):
        return "instance" #str(hash(self))

    # Internal methods

    def _clone(self, as_model=None):
        """
        Returns an exact copy of current instance with regard to model metadata.
        """
        ModelClass = as_model or type(self)
        new_instance = ModelClass()
        new_instance._state = self._state.clone()

        for attr in new_instance._meta.prop_names:
            if attr in self._meta.prop_names:
                setattr(new_instance, attr,
                        getattr(self, attr))
            else:
                raw_value = self._state.data.get(attr) if self._state.data else None
                value = new_instance._meta.props[attr].to_python(raw_value)
                setattr(new_instance, attr, value)

        return new_instance

    # Public methods

    @classmethod
    def objects(cls, storage):    # XXX or: "items", "at", "saved_in", etc.
        """
        Returns a Query instance for all model instances within given storage.

        Usage::

            >>> db.clear()
            >>> Note.objects(db)
            []
            >>> Note(text="huh?").save(db)
            u'1'
            >>> Note(text="hmmm...").save(db)
            u'2'
            >>> Note.objects(db)
            [<Note huh?>, <Note hmmm...>]
            >>> Note.objects(db).where(text__contains='uh')
            [<Note huh?>]

        """
        assert isinstance(cls, ModelBase), 'this method must be called with class, not instance'

        items = storage.get_query(model=cls)

        if cls._meta.must_have:
            items = items.where(**cls._meta.must_have)
        if cls._meta.must_not_have:
            items = items.where_not(**cls._meta.must_not_have)
        return items

    @classmethod
    def query(cls, storage):
        import warnings
        warnings.warn("Model.query() is deprecated, use Model.objects() instead.",
                      DeprecationWarning)
        return cls.objects(storage)

    @property
    def pk(self):
        """
        Returns current primary key (if any) or None.
        """
        return self._state.key

    def convert_to(self, other_model, overrides=None):
        """
        Returns the document as an instance of another model. Copies attributes
        of current instance that can be applied to another model (i.e. only
        overlapping attributes -- ones that matter for both models). All other
        attributes are re-fetched from the database (if we know the key).

        .. note:: The document key is *preserved*. This means that the new
            instance represents *the same document*, not a new one. Remember
            that models are "views", and to "convert" a document does not mean
            copying; it can however imply *adding* attributes to the existing
            document.

        Neither current instance nor the returned one are saved automatically.
        You will have to do it yourself.

        Please note that trying to work with the same document via different
        instances of models whose properties overlap can lead to unpredictable
        results: some properties can be overwritten, go out of sync, etc.

        :param other_model: the model to which the instance should be converted.
        :param overrides: a dictionary with attributes and their values that
            should be set on the newly created model instance. This dictionary
            will override any attributes that the models have in common.

        Usage::

            >>> class Contact(Note):
            ...     name = Property()
            ...
            ...     class Meta:
            ...         must_have = {'name__exists': True}  # merged with Note's
            ...     def __unicode__(self):
            ...         return u"%s (%s)" % (self.name, self.text)

            >>> note = Note(text='phone: 123-45-67')
            >>> note
            <Note phone: 123-45-67>

            # same document, contact-specific data added
            >>> contact = note.convert_to(Contact, {'name': 'John Doe'})
            >>> contact
            <Contact John Doe (phone: 123-45-67)>
            >>> contact.name
            'John Doe'
            >>> contact.text
            'phone: 123-45-67'

            # same document, contact-specific data ignored
            >>> note2 = contact.convert_to(Note)
            >>> note2
            <Note phone: 123-45-67>
            >>> note2.name
            Traceback (most recent call last):
            ...
            AttributeError: 'Note' object has no attribute 'name'
            >>> note2.text
            'phone: 123-45-67'

        """
        if self._state.storage and self._state.key:
            new_instance = self._state.storage.get(other_model, self._state.key)
        else:
            new_instance = self._clone(as_model=other_model)

        if overrides:
            for attr, value in overrides.items():
                setattr(new_instance, attr, value)

        return new_instance

    def save_as(self, key=None, storage=None, **kwargs):
        """
        Saves the document under another key (specified as `key` or generated)
        and returns the newly created instance.

        :param key: the key by which the document will be identified in the
            storage. Use with care: any existing record with that key will be
            overwritten. Pay additional attention if you are saving the document
            into another storage. Each storage has its own namespace for keys
            (unless the storage objects just provide different ways to access a
            single real storage). If the key is not specified, it is generated
            automatically by the storage.

        See `save()` for details on other params.

        Usage::

            >>> db.clear()
            >>> note = Note(text="hello")   # just create the item

            # WRONG:

            >>> note.save()               # no storage; don't know where to save
            Traceback (most recent call last):
            ...
            AttributeError: cannot save model instance: storage is not defined neither in instance nor as argument for the save() method
            >>> note.save_as()            # same as above
            Traceback (most recent call last):
            ...
            AttributeError: cannot save model instance: storage is not defined neither in instance nor as argument for the save() method

            # CORRECT:

            >>> new_key = note.save(db)                   # storage provided, key generated
            >>> new_key
            u'1'
            >>> new_obj = note.save_as(storage=db)        # same as above
            >>> new_obj
            <Note hello>
            >>> new_obj.pk  # new key
            u'2'
            >>> new_obj.text  # same data
            'hello'
            >>> new_key = note.save()                     # same storage, same key
            >>> new_key
            u'1'
            >>> new_obj = note.save_as()                  # same storage, autogenerated new key
            >>> new_obj.pk
            u'3'
            >>> new_obj = note.save_as('custom_key')      # same storage, key "123"
            >>> new_obj.pk
            'custom_key'

            >>> note.save_as(123, other_db)     # other storage, key "123"
            <Note hello>
            >>> note.save_as(storage=other_db)  # other storage, autogenerated new key
            <Note hello>


        """
        new_instance = self._clone()
        new_instance._state.update(storage=storage)
        new_instance._state.key = key    # reset to None
        new_instance.save(**kwargs)
        return new_instance

    def save(self, storage=None):   #, sync=True):
        """
        Saves instance to given storage.

        :param storage: the storage to which the document should be saved. If
            not specified, default storage is used (the one from which the
            document was retrieved of to which it this instance was saved
            before).
        """

        if not storage and not self._state.storage:
            raise AttributeError('cannot save model instance: storage is not '
                                 'defined neither in instance nor as argument '
                                 'for the save() method')

        if storage:
            assert hasattr(storage, 'save'), (
                'Storage %s does not define method save(). Storage must conform '
                'to the API of pymodels.backends.base.BaseStorage.' % storage)
        else:
            storage = self._state.storage

        data = self._state.data.copy() if self._state.data else {}

        # prepare properties defined in the model
        for name in self._meta.prop_names:
            value = self.pre_save_property(name, storage)   #, save_related=True)
            data[name] = value

        # make sure required properties will go into the storage
        if self._meta.must_have:
            for name in self._meta.must_have.keys():
                # TODO validation using must_have constraints (regardless whether
                # it's an attr or a query lookup).
                # FIXME query details exposed. Query should provide some
                # validation or introspection functionality
                if '__' in name:
                    # attribute name + operator
                    pass
                else:
                    # attribute name
                    if name not in data:
                        data[name] = getattr(self, name)
        if self._meta.must_not_have:
            for name, value in self._meta.must_not_have.iteritems():
                # FIXME see above for must_have
                if '__' in name:
                    pass
                else:
                    if name in data and getattr(self, name) == value:
                        raise ValidationError(
                            'cannot save object: it has %s set to "%s", this '
                            'violates model constraints.' % (name, value)
                        )

        # TODO: make sure we don't overwrite any attrs that could be added to this
        # document meanwhile. The chances are rather high because the same document
        # can be represented as different model instances at the same time (i.e.
        # Person, User, etc.). We should probably fetch the data and update only
        # attributes that make sense for the model being saved. The storage must
        # not know these details as it deals with whole documents, not schemata.
        # This introduces a significant overhead (roughly x2 on Tyrant) and user
        # should be able switch it off by "granular=False" (or "full_data=True",
        # or "per_property=False", or whatever).

        # let the storage backend prepare data and save it to the actual storage
        key = storage.save(
            model = type(self),
            data = data,
            primary_key = self.pk,
        )
        assert key, 'storage must return primary key of saved item'
        # okay, update our internal representation of the record with what have
        # been just successfully saved to the database
        self._state.update(key=key, storage=storage, data=data)
        # ...and return the key, yep
        return self.pk

    def pre_save_property(self, name, storage):
        p = self._meta.props[name]
        value = getattr(self, name)
        return p.pre_save(value, storage) # will raise ValidationError if smth is wrong

    def delete(self):
        """
        Deletes the object from the associated storage.
        """
        if not self._state.storage or not self._state.key:
            raise ValueError('Cannot delete object: not associated with '
                             'a storage and/or primary key is not defined.')
        self._state.storage.delete(self._state.key)

