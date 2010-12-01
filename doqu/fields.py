# -*- coding: utf-8 -*-
#
#    Doqu is a lightweight schema/query framework for document databases.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of Docu.
#
#    Doqu is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Doqu is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Docu.  If not, see <http://gnu.org/licenses/>.
"""
Document Fields
===============

.. versionadded:: 0.23

.. note::

    This abstraction is by no means a complete replacement for the normal
    approach of semantic grouping. Please use it with care. Also note that the
    API can change. The class can even be removed in future versions of Docu.

"""
# python
try:
    import Image    # for ImageField
except ImportError:
    Image = None
import pickle
# doqu
from doqu import validators
from doqu.utils import cached_property


# TODO: extract file-related stuff to doqu.fields.files
__all__ = ['Field', 'FileField', 'ImageField']


class Field(object):
    """
    Representation of a document property. Syntax sugar for separate
    definitions of structure, validators, defaults and labels.

    Usage::

        class Book(Document):
            title = Field(unicode, required=True, default=u'Hi', label='Title')

    this is just another way to type::

        class Book(Document):
            structure = {
                'title': unicode
            }
            validators = {
                'title': [validators.Required()]
            }
            defaults = {
                'title': u'Hi'
            }
            labels = {
                'title': u'The Title'
            }

    Nice, eh? But be careful: the `title` definition in the first example
    barely fits its line. Multiple long definitions will turn your document
    class into an opaque mess of characters, while the semantically grouped
    definitions stay short and keep related things aligned together. "Semantic
    sugar" is sometimes pretty bitter, use it with care.

    Complex validators still need to be specified by hand in the relevant
    dictionary. This can be worked around by creating specialized field classes
    (e.g. `EmailField`) as it is done e.g. in Django.

    :param essential:
        if True, validator :class:`~doqu.validators.Exists` is added (i.e. the
        field may be empty but it must be present in the record).
    :param pickled:
        if True, the value is preprocessed with pickle's dumps/loads functions.
        This of course breaks lookups by this field but enables storing
        arbitrary Python objects.

    """
    def __init__(self, datatype, essential=False, required=False, default=None,
                 choices=None, label=None, pickled=False):
        self.choices = choices
        self.datatype = datatype
        self.essential = essential
        self.required = required
        self.default = default
        self.label = label
        self.pickled = pickled

    def get_item_get_processors(self):
        return None

    def get_item_set_processors(self):
        return None

    def get_incoming_processors(self):
        if self.pickled:
            # it is important to keep initial value as bytes; e.g. TC will
            # return Unicode so we make sure pickle loader gets a str
            return lambda v: pickle.loads(str(v)) if v else None
        else:
            return None

    def get_outgoing_processors(self):
        if self.pickled:
            return pickle.dumps
        else:
            return None

    def contribute_to_document_metadata(self, doc_meta, attr_name):
        doc_meta.structure[attr_name] = self.datatype

        if self.default is not None:
            doc_meta.defaults[attr_name] = self.default

        if self.label is not None:
            doc_meta.labels[attr_name] = self.label

        # validation

        def _add_validator(validator_class, *args, **kwargs):
            validator = validator_class(*args, **kwargs)
            vs = doc_meta.validators.setdefault(attr_name, [])
            if not any(isinstance(x, validator_class) for x in vs):
                vs.append(validator)

        if self.essential:
            _add_validator(validators.Exists)

        if self.required:
            _add_validator(validators.Required)

        if self.choices:
            _add_validator(validators.AnyOf, list(self.choices))

        # preprocessors (serialization, wrappers, etc.)

        for name in ['incoming_processors', 'outgoing_processors',
                     'item_get_processors', 'item_set_processors']:
            processor = getattr(self, 'get_{0}'.format(name))()
            if processor:
                getattr(doc_meta, name)[attr_name] = processor
            else:
                try:
                    del getattr(doc_meta, name)[attr_name]
                except KeyError:
                    pass

#--- Files --

class FileWrapper(unicode):
    def __init__(self, path):
        self.path = path
        self._fh = None

    @classmethod
    def from_file(cls, filehandle):
        obj = cls(filehandle.name)
        obj._fh = filehandle
        return obj

    @cached_property
    def file(self):
        return self._fh or open(self.path)

#    @cached_property
#    def data(self):
#        return self.file.read()

    def __repr__(self):
        return '<{cls}: {path}>'.format(
            cls=self.__class__.__name__, path=self.path)

    def __unicode__(self):
        return self.path


class ImageWrapper(FileWrapper):
    """
    A FileWrapper which deals fith files via PIL and provides advanced
    image-related methods (compared to FileWrapper). See :class:`Image` for
    details. The image is available as ``file`` attribute.
    """
    @cached_property
    def file(self):
        if Image is None:
            raise ImportError('PIL is not installed.')
        return Image.open(self.path)


class FileField(Field):
    """
    Handles externally stored files.

    .. warning::

        This field does *not* save files. Saving must be done in client code.

    """
    file_wrapper_class = FileWrapper

    def __init__(self, base_path, **kwargs):
        self.base_path = base_path
        self._data = None

        if 'pickled' in kwargs:
            raise KeyError('Pickling is not allowed for file fields.')

        super(FileField, self).__init__(self.file_wrapper_class, **kwargs)

    def get_item_set_processors(self):
        def wrap_file(value):
            if isinstance(value, file):
                return self.file_wrapper_class.from_file(value)
            elif isinstance(value, basestring):
                return self.file_wrapper_class(value)
            else:
                raise TypeError('Expected path or file handle, got {0}'.format(
                    repr(value)))
        return wrap_file

    def get_outgoing_processors(self):
        def unwrap_file(file_wrapper):
            return file_wrapper.path
        return unwrap_file

    def get_incoming_processors(self):
        def wrap_path(file_path):
            return self.file_wrapper_class(file_path)
        return wrap_path


class ImageField(FileField):
    file_wrapper_class = ImageWrapper
