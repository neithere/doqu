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
WTForms extension
=================

Offers integration with `WTForms`_.

:status: beta
:dependencies: `wtforms`_

.. _WTForms: http://wtforms.simplecodes.com/

The extension provides two new field classes: :class:`QuerySetSelectField` and
:class:`DocumentSelectField` (inspired by `wtforms.ext.django.*`). They connect
the forms with the Docu API for queries. You can manually create forms with
these fields.

The easiest way to create a :class:`~docu.document_base.Document`-compliant
form is using the function :func:`document_form_factory`. It returns a form
class based on the document structure::

    from docu import Document
    from docu import validators
    from docu.ext.forms import document_form_factory

    class Location(Document):
        structure = {'name': unicode}

    class Person(Document):
        structure = {'name': unicode, 'age': int, 'location': Location}
        labels = {'name': 'Full name', 'age': 'Age', 'location': 'Location'}
        validators = {'name': [required()]}

    PersonForm = document_form_factory(Person)

The last line does the same as this code::

    from wtforms import TextField, IntegerField, validators
    from docu.ext.forms import DocumentSelectField

    class PersonForm(wtforms.Form):
        name = TextField('Full name', [validators.Required()])
        age = IntegerField('Age')
        location = DocumentSelectField('Location', [], Location)

.. warning:: currently only validators :class:`~docu.validators.Required` and
    :class:`~docu.validators.Optional` are translated to the form validators;
    in the future most of them can be translated automatically.

"""

import datetime
import wtforms

from docu import Document
from docu.validators import Required, Optional


__all__ = (
    'document_form_factory', 'QuerySetSelectField', 'DocumentSelectField'
)


TYPE_TO_FORM_FIELD = {
    int:               wtforms.fields.IntegerField,
    float:             wtforms.fields.DecimalField,
    datetime.date:     wtforms.fields.DateField,
    datetime.datetime: wtforms.fields.DateTimeField,
    bool:              wtforms.fields.BooleanField,
    unicode:           wtforms.fields.TextAreaField,
    # XXX what to do with wtforms.FileField?
    # XXX what about lists?
}

def document_form_factory(document_class, storage=None):
    """
    Expects a :class:`~docu.document_base.Document` instance, creates and
    returns a :class:`wtforms.Form` class for this model.

    The form fields are selected depending on the Python type declared by each
    property.

    :param document_class:
        the Docu document class for which the form should be created
    :param storage:
        a Docu-compatible storage; we need it to generate lists of choices
        for references to other models. If not defined, references will not
        appear in the form.

    Caveat: the ``unicode`` type can be mapped to TextField and TextAreaField.
    It is impossible to guess which one should be used unless maximum length is
    defined for the property. TextAreaField is picked by default. It is a good
    idea to automatically shrink it with JavaScript so that its size always
    matches the contents.
    """
    DocumentForm = type(type(document_class ).__name__ + 'Form',
                        (wtforms.Form,), {})
    for name, datatype in document_class.meta.structure.iteritems():
        defaults = {}
        # XXX private attr used, make it public?
        doc_ref = document_class._get_related_document_class(datatype)
        if doc_ref:
            if not storage:
                # we need a storage to fetch choices for the reference
                continue
            FieldClass = DocumentSelectField
            defaults.update(document_class=doc_ref, storage=storage)
        else:
            FieldClass = TYPE_TO_FORM_FIELD.get(datatype,
                                                wtforms.fields.TextField)
        label = document_class.meta.labels.get(name, pretty_label(name))
        validators = []

        field_validators = document_class.meta.validators.get(name, [])
        required = any(isinstance(x, Required) for x in field_validators)
        if required:
            validators.append(wtforms.validators.Required())
        else:
            validators.append(wtforms.validators.Optional())
            if issubclass(FieldClass, QuerySetSelectField):
                defaults['allow_blank'] = True
        form_field = FieldClass(label, validators, **defaults)
        setattr(DocumentForm, name, form_field)
    return DocumentForm


# FIXME this is already in utils, innit?
def pretty_label(string):
    return unicode(string).capitalize().replace('_', ' ') + ':'


#
# The code below is a modified version of wtforms.ext.django.fields.*
#

class QuerySetSelectField(wtforms.fields.Field):
    """
    Given a QuerySet either at initialization or inside a view, will display a
    select drop-down field of choices. The `data` property actually will
    store/keep an ORM model instance, not the ID. Submitting a choice which is
    not in the queryset will result in a validation error.

    Specifying `label_attr` in the constructor will use that property of the
    model instance for display in the list, else the model object's `__str__`
    or `__unicode__` will be used.

    If `allow_blank` is set to `True`, then a blank choice will be added to the
    top of the list. Selecting this choice will result in the `data` property
    being `None`.  The label for the blank choice can be set by specifying the
    `blank_text` parameter.
    """
    widget = wtforms.widgets.Select()

    def __init__(self, label=u'', validators=None, queryset=None,
                 label_attr='', allow_blank=False, blank_text=u'', **kw):
        super(QuerySetSelectField, self).__init__(label, validators, **kw)
        self.label_attr = label_attr
        self.allow_blank = allow_blank
        self.blank_text = blank_text
        self._set_data(None)
        # TODO:
        #if queryset is not None:
        #    self.queryset = queryset.all() # Make sure the queryset is fresh
        self.queryset = queryset

    def _get_data(self):
        if self._formdata is not None:
            for obj in self.queryset:
                #print 'formdata "%s" vs choice "%s"' %(self._formdata, obj.pk)
                if obj.pk == self._formdata:
                    self._set_data(obj)
                    break
        return self._data

    def _set_data(self, data):
        self._data = data
        self._formdata = None

    data = property(_get_data, _set_data)

    def iter_choices(self):
        if self.allow_blank:
            yield (u'__None', self.blank_text, self.data is None)

        for obj in self.queryset:
            label = self.label_attr and getattr(obj, self.label_attr) or obj
            yield (obj.pk, label, obj == self.data)

    def process_formdata(self, valuelist):
        if valuelist:
            if valuelist[0] == '__None': # FIXME: this in NOT safe for k/v DBs
                self.data = None
            else:
                self._data = None
                self._formdata = valuelist[0]

    def pre_validate(self, form):
        if not self.allow_blank or self.data is not None:
            for obj in self.queryset:
                if self.data == obj:
                    break
            else:
                raise wtforms.ValidationError('Not a valid choice')


class DocumentSelectField(QuerySetSelectField):
    """
    Like a QuerySetSelectField, except takes a document class instead of a
    queryset and lists everything in it.
    """
    def __init__(self, label=u'', validators=None, document_class=None,
                 storage=None, **kw):
        super(DocumentSelectField, self).__init__(
            label, validators, queryset=document_class.objects(storage), **kw
        )

