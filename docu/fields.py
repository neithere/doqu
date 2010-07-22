# -*- coding: utf-8 -*-
#
#    Docu is a lightweight schema/query framework for document databases.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of Docu.
#
#    Docu is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Docu is distributed in the hope that it will be useful,
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

.. warning::

    This abstraction is by no means a complete replacement for the normal
    approach of semantic grouping. Please use it with care. Also note that the
    API can change. The class can even be removed in future versions of Docu.

"""
import pickle
import validators


__all__ = ['Field']


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
        if True, validator :class:`~docu.validators.Exists` is added (i.e. the
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

        # serialization

        if self.pickled:
            # it is important to keep initial value as bytes; e.g. TC will
            # return Unicode so we make sure pickle loader gets a str
            deserializer = lambda v: pickle.loads(str(v)) if v else None
            serializer = pickle.dumps
            doc_meta.serialized[attr_name] = serializer, deserializer
        else:
            try:
                del doc_meta.serialized[attr_name]
            except KeyError:
                pass
