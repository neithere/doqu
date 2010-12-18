#!/usr/bin/env python
# -*- coding: utf-8 -*-

import datetime
import unittest2 as unittest

from doqu import Document, get_db
from doqu.fields import Field
from doqu.validators import ValidationError
from doqu.backend_base import DataProcessorDoesNotExist


class CustomObj(object):
    "For testing custom types in pickled fields"
    def __init__(self, value):
        self._value = value
    def __eq__(self, other):
        return self._value == other._value if hasattr(other,'_value') else False


class FieldTestCase(unittest.TestCase):
    def setUp(self):
        self.db = get_db(backend='doqu.ext.shove_db')

    def test_unicode_field(self):
        "Unicode is supported by default backend type converters"
        class D(Document):
            foo = Field(unicode)
            break_on_invalid_incoming_data = True
        with self.assertRaisesRegexp(ValidationError, 'expected a unicode'):
            d = D(foo='string')
        d = D(foo=u'hello')
        self.assertEquals(d['foo'], u'hello')
        d.save(self.db)
        d2 = self.db.get(D, d.pk)
        self.assertEquals(d.foo, d2.foo)

    def test_int_field(self):
        "Integer is supported by default backend type converters"
        class D(Document):
            foo = Field(int)
            break_on_invalid_incoming_data = True
        with self.assertRaisesRegexp(ValidationError, 'expected a int'):
            d = D(foo='string')
        d = D(foo=123)
        self.assertEquals(d['foo'], 123)
        d.save(self.db)
        d2 = self.db.get(D, d.pk)
        self.assertEquals(d.foo, d2.foo)

    def test_datetime_field(self):
        "Datetime is supported by default backend type converters"
        class D(Document):
            foo = Field(datetime.datetime)
            break_on_invalid_incoming_data = True
        with self.assertRaisesRegexp(ValidationError, 'expected a datetime'):
            d = D(foo='string')
        guido_birth_date = datetime.datetime(1956, 1, 31)
        d = D(foo=guido_birth_date)
        self.assertEquals(d['foo'], guido_birth_date)
        d.save(self.db)
        d2 = self.db.get(D, d.pk)
        self.assertEquals(d.foo, d2.foo)

    def test_pickled_list_field(self):
        "When pickled, a list can be safely saved and retrieved"
        class D(Document):
            foo = Field(list, pickled=True)
        d = D(foo=[1,2])
        self.assertEquals(d['foo'], [1,2])
        d.save(self.db)
        d2 = self.db.get(D, d.pk)
        self.assertEquals(d.foo, d2.foo)

    @unittest.expectedFailure  # FIXME dict is always wrapped in DotDict so type check fails
    def test_pickled_dict_field(self):
        "When pickled, a dictionary can be safely saved and retrieved"
        class D(Document):
            foo = Field(dict, pickled=True)
        d = D(foo={'bar': 'quux'})
        self.assertEquals(d['foo'], {'bar': 'quux'})
        d.save(self.db)
        d2 = self.db.get(D, d.pk)
        self.assertEquals(d.foo, d2.foo)

    def test_unpickled_custom_field(self):
        "Custom data type cannot be saved unless a converter is defined for it"
        class D(Document):
            foo = Field(CustomObj)
        d = D(foo=CustomObj(123))
        with self.assertRaises(DataProcessorDoesNotExist):
            d.save(self.db)

    def test_pickled_custom_field(self):
        "Any datatype that can be pickled can be safely saved and retrieved"
        class D(Document):
            foo = Field(CustomObj, pickled=True)
        d = D(foo=CustomObj(123))
        self.assertEquals(d['foo'], CustomObj(123))
        d.save(self.db)
        d2 = self.db.get(D, d.pk)
        self.assertEquals(d.foo, d2.foo)


if __name__ == '__main__':
    unittest.main()
