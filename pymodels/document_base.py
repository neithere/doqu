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

import abc
import logging
import re

#from backend import BaseStorage
from validators import StopValidation, ValidationError
from utils import camel_case_to_underscores
from utils.data_structures import DotDict, ProxyDict


__all__ = ['Document']


class DocumentState(object):
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


class DocumentMetadata(object):
    """
    Specifications of a document. They are defined in the document class but
    stored here for document isntances so that they don't interfere with
    document properties.
    """
    structure = {}
    validators = {}
    defaults = {}
    use_dot_notation = False
    break_on_invalid_incoming_data = False

    def __init__(self, name):
        # this is mainly for URLs and such stuff:
        self.lowercase_name = camel_case_to_underscores(name)
        # and this is for humans:    (TODO: allow to override, incl. i18n)
        self.label = self.lowercase_name.replace('_', ' ')
        self.label_plural = self.label + 's'


class DocumentMetaclass(abc.ABCMeta):
    """
    Metaclass for all models.
    """
    def __new__(cls, name, bases, attrs):

        # TODO:
        # inherit metadata from parent document classes
        # (all attributes are inherited automatically except for those we
        #  move to the metadata container in this method)
        #
        #parents = [b for b in bases if isinstance(b, cls)]

        # move special attributes to the metadata container
        # (extend existing attrs if they were already inherited)
        meta = DocumentMetadata(name)
        for attr in DocumentMetadata.__dict__:
            if not attr.startswith('_') and attr in attrs:
                value = attrs.pop(attr)
                setattr(meta, attr, value)

        # by default we use getitem, i.e. book['title'], but user can also opt
        # to use getattr, i.e. book.title to access document properties
        if meta.use_dot_notation:
            bases += (DotDict,)

        attrs['meta'] = meta

        return type.__new__(cls, name, bases, attrs)


class Document(ProxyDict):
    """
    Base class for document schemata.

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
    __metaclass__ = DocumentMetaclass

    #--------------------+
    #  Magic attributes  |
    #--------------------+

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

    def __getitem__(self, key):
        value = self._data[key]

        # handle references to other documents
        # XXX add support for nested structure?
        ref_model = self._get_related_document_class(key)
        if ref_model:
            if value and not isinstance(value, Document):
                # retrieve the record and replace the PK in the data dictionary
                value = self._state.storage.get(ref_model, value)
                self[key] = value # FIXME changes internal state!!! bad, bad, baaad
            return value
        else:
            # the DotDict stuff
            return super(Document, self).__getitem__(key)

    def __init__(self, **kw):
        if self.__class__ == Document:
            raise NotImplementedError('Document must be subclassed')

        # NOTE: state must be filled from outside
        self._state = DocumentState()

        self._data = dict((k, kw.pop(k, None)) for k in self.meta.structure)

        if kw:
            raise NameError('Unknown properties: %s' % ', '.join(kw.keys()))

        # add backward relation descriptors to related classes
        for field in self.meta.structure:
            ref_doc = self._get_related_document_class(field)
            if ref_doc:
                descriptor = BackwardRelation(self, field)
                rel_name = self.meta.lowercase_name + '_set'
                setattr(ref_doc, rel_name, descriptor)

    def __repr__(self):
        try:
            u = unicode(self)
        except (UnicodeEncodeError, UnicodeDecodeError):
            u = u'[bad unicode data]'
        except TypeError:
            u = u'[bad type in __unicode__]'
        r = u'<%s: %s>' % (type(self).__name__, u)
        return r.encode('utf-8')

    def __unicode__(self):
        return 'instance'

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _clone(self, as_document=None):
        """
        Returns an exact copy of current instance with regard to model metadata.
        """
        DocumentClass = as_document or type(self)
        new_instance = DocumentClass()
        new_instance._state = self._state.clone()

        for attr in new_instance.meta.structure:
            if attr in self.meta.structure:
                new_instance[attr] = self[attr]
            else:
                if not self._state.data:
                    continue
                value = self._state.data.get(attr, None)
                if self._state.storage:
                    value = self._state.storage.value_from_db(value)
                else:
                    assert value is None, ('record representation requires '
                                           'a storage adapter')
                new_instance[attr] = value

        return new_instance

    def _get_related_document_class(self, field):
        """
        Returns the relevant document class for given `field` depending on the
        declared document structure. (Field = property = column.)

        If the declared data type is a :class:`Document` subclass, it is
        returned. If the data type is a string, it is interpreted as a lazy
        import path (e.g. `myapp.models.Foo` or `self`). If the import fails,
        `ImportError` is raised.  If the data type is unrelated, `None` is
        returned.

        """
        datatype = self.meta.structure.get(field)

        # model class
        if issubclass(datatype, Document):
            return datatype

        # dotted path to the model class (lazy import)
        if isinstance(datatype, basestring):
            return self._resolve_model_path(datatype)

    def _resolve_model_path(self, path):
        # XXX make better docstring. For now see _get_related_document_class.
        if path == 'self':
            return type(self)
        if '.' in path:
            module_path, attr_name = path.rsplit('.', 1)
        else:
            module_path, attr_name = self.__module__, path
        module = __import__(module_path, globals(), locals(), [attr_name], -1)
        return getattr(module, attr_name)

    #---------------------+
    #  Public attributes  |
    #---------------------+

    def convert_to(self, other_schema, overrides=None):
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
            new_instance = self._state.storage.get(other_schema,
                                                   self._state.key)
        else:
            new_instance = self._clone(as_model=other_schema)

        if overrides:
            for attr, value in overrides.items():
                setattr(new_instance, attr, value)

        return new_instance

    def delete(self):
        """
        Deletes the object from the associated storage.
        """
        if not self._state.storage or not self._state.key:
            raise ValueError('Cannot delete object: not associated with '
                             'a storage and/or primary key is not defined.')
        self._state.storage.delete(self._state.key)

    def is_valid(self):
        try:
            self.validate()
        except ValidationError:
            return False
        else:
            return True

    @classmethod
    def objects(cls, storage):
        # get query for this storage; tell it to decorate all fetched records
        # with our current model
        query = storage.get_query(model=cls)

        # but hey, we don't need *all* records, we only want those that belong
        # to this model! let's use validators to filter the results:
        for name, validators in cls.meta.validators.iteritems():
            for validator in validators:
                if hasattr(validator, 'filter_query'):
                    query = validator.filter_query(query, name)

        #logging.debug(query._query._conditions)

        return query

    @property
    def pk(self):
        """
        Returns current primary key (if any) or None.
        """
        return self._state.key

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

        self.validate()    # will raise ValidationError if something is wrong

        # Dictionary self._data only keeps known properties. The database
        # record may contain other data. The original data is kept in the
        # dictionary self._state.data. Now we copy the original record, update
        # its known properties and try to save that:

        data = self._state.data.copy() if self._state.data else {}

        # prepare (validate) properties defined in the model
        # XXX only flat structure is currently supported:
        for name in self.meta.structure:
            value = self._data.get(name)
            logging.debug('converting %s (%s) -> %s' % (name, repr(value),
                          repr(storage.value_to_db(value))))
            data[name] = storage.value_to_db(value)

        # TODO: make sure we don't overwrite any attrs that could be added to this
        # document meanwhile. The chances are rather high because the same document
        # can be represented as different model instances at the same time (i.e.
        # Person, User, etc.). We should probably fetch the data and update only
        # attributes that make sense for the model being saved. The storage must
        # not know these details as it deals with whole documents, not schemata.
        # This introduces a significant overhead (roughly ×2 on Tyrant) and user
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

    def validate(self):
        """
        Checks if instance data is valid by calling all validators against it.
        Raises :class:`ValidationError` if something is wrong.
        """
        pairs = self.meta.validators or {}
        for name, validators in pairs.iteritems():
            value = getattr(self, name, None)
            for validator in validators:
                try:
                    validator(self, value)
                except StopValidation:
                    break
                except ValidationError:
                    # XXX should preserve call stack and add sensible message
                    raise ValidationError(
                        'Value %s is invalid for %s.%s (%s)'
                        % (repr(value), type(self).__name__, name, validator))


# TODO: replace this with simple getitem filter + cache + registering
# "referenced_by" as it's already done in prev. versions (but not DRY there)
class BackwardRelation(object):
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
