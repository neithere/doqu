#!/usr/bin/env python
# -*- coding: utf-8 -*-

import unittest

from docu import Document
from docu import validators


class BaseTestCase(unittest.TestCase):
    "Document base class"

    def test_no_subclassing(self):
        "document base class can be instantiated itself"
        document = Document(foo=123)

    def test_subclassing(self):
        "document can be subclassed"
        class Doc(Document):
            pass
        document = Doc(foo=123)

    def test_repr_default(self):
        "document representation can be changed"
        class Doc(Document):
            pass
        self.assertEqual(repr(Doc()), '<Doc: {}>')
        self.assertEqual(repr(Doc(foo=123)), "<Doc: {'foo': 123}>")

    def test_repr_custom(self):
        class Doc(Document):
            __unicode__ = lambda self: u'hello!'
        self.assertEqual(repr(Doc()), '<Doc: hello!>')

    def test_repr_custom_bad_type(self):
        class Doc(Document):
            __unicode__ = lambda self: 123
        self.assertEqual(repr(Doc()), '<Doc: [__unicode__ returned int]>')

    def test_repr_custom_bad_unicode(self):
        class Doc(Document):
            __unicode__ = lambda self: '\xa9'
        self.assertEqual(repr(Doc()), '<Doc: [bad unicode data]>')

    def test_repr_format(self):
        class Doc(Document):
            __unicode__ = lambda self: u'{name}'.format(**self)
        self.assertEqual(repr(Doc(name='foo')), '<Doc: foo>')


class AttributesTestCase(unittest.TestCase):
    "Accessing properties via getitem and getattr"

    def test_dict_proxy(self):
        "The document object acts as a proxy for the data dictionary"
        d = Document(name='John')
        # getitem proxy enabled
        self.assertEqual(d['name'], 'John')
        # getattr proxy enabled
        self.assertEqual(d.name, 'John')
        # "unconventional" names are accessible via getitem
        d['foo-bar'] = 'Quux'
        self.assertEqual(d['foo-bar'], 'Quux')


class StructureTestCase(unittest.TestCase):
    "Validating the structure"

    def test_structure_undefined(self):
        "Document structure not defined, any value will do"
        class Doc(Document):
           pass
        doc = Doc(name=u'foo')
        assert doc.is_valid()
        self.assertEqual(doc['name'], u'foo')

    def test_structure_correct(self):
        "Document structure is defined, data is valid"
        class Doc(Document):
           structure = {'name': unicode}
        doc = Doc(name=u'foo')
        assert doc.is_valid()
        self.assertEqual(doc['name'], u'foo')
        doc['name'] = u'bar'
        assert doc.is_valid()

    def test_structure_wrong_field(self):
        "Document structure is defined, wrong field ignored"
        class Doc(Document):
            structure = {'name': unicode}
        doc = Doc()
        # valid with no data:
        assert doc.is_valid()
        # invalidates on creation:
        self.assertRaises(KeyError, lambda: Doc(location=u'foo'))
        # invalidates on setitem:
        def set_wrong_item():
            doc['location'] = 'foo'
        self.assertRaises(KeyError, set_wrong_item)

    def test_structure_wrong_type(self):
        "Document structure is defined, wrong type skipped"
        class Doc(Document):
            structure = {'name': unicode}
        doc = Doc()
        # valid with no data:
        assert doc.is_valid()
        # doesn't break on creation:
        doc = Doc(name=123)
        # invalidates on setitem:
        def set_wrong_value():
            doc['name'] = 123
        self.assertRaises(validators.ValidationError, set_wrong_value)

    def test_structure_wrong_type_strict(self):
        "Document structure is defined, wrong type raises error"
        class Doc(Document):
            break_on_invalid_incoming_data = True   # strict mode
            structure = {'name': unicode}
        doc = Doc()
        # valid with no data:
        assert doc.is_valid()
        # invalidates on creation:
        self.assertRaises(validators.ValidationError, lambda: Doc(name=123))
        # invalidates on setitem:
        def set_wrong_value():
            doc['name'] = 123
        self.assertRaises(validators.ValidationError, set_wrong_value)


class ValidatorsTestCase(unittest.TestCase):

    def test_validators_undefined(self):
        "Validators not defined, any value will do"
        class Doc(Document):
            pass
        doc = Doc(name=u'foo')
        assert doc.is_valid()

    def test_validators_correct(self):
        "Validators defined, value passes test, document is valid"
        class Doc(Document):
            validators = {
                'name': [validators.Length(min=3)],
            }
        doc = Doc(name=u'foo')
        assert doc.is_valid()

    def test_validators_wrong(self):
        "Validators defined, value fails test, document is invalid"
        class Doc(Document):
            validators = {
                'name': [validators.Length(min=5)],
            }
        class StrictDoc(Doc):
            break_on_invalid_incoming_data = True
        # custom validator runs on document initialization
        # ...doesn't break by default:
        Doc(name=u'foo')
        # ...breaks in strict mode:
        self.assertRaises(validators.ValidationError,
                          lambda: StrictDoc(name=u'foo'))
        # custom validator runs on item assignment
        def set_wrong_value():
            doc = Doc()
            doc['name'] = 'bar'
        self.assertRaises(validators.ValidationError, set_wrong_value)


class StateTestCase(unittest.TestCase):
    "Document state"

#    def setUp(self):
#        self.db1 = get_db(backend='docu.ext.shove')
#        self.db2 = get_db(backend='docu.ext.shove')
#        assert self.db1 != self.db2
#
#    def tearDown(self):
#        self.db1.close()
#        self.db2.close()

    def test_equal_docs(self):
        pass

    def test_different_docs(self):
        pass

    def test_hash(self):
        # TODO: test if __hash__ works properly for saved and unsaved documents
        # including cross-database comparisons (storage AND key must be same)
        pass


class ReferenceTestCase(unittest.TestCase):
    "References between documents"

    pass


if __name__ == '__main__':
    unittest.main()
