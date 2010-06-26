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

import unittest

from docu import Document
from docu.ext.forms import document_form_factory
from docu.validators import required


class FormTestCase(unittest.TestCase):
    def test_basic(self):
        "just some very basic test to make sure it doesn't break on start :)"
        class Person(Document):
            structure = {'name': unicode, 'age': int}
            validators = {'name':[required()]}
        john = Person()
        PersonForm = document_form_factory(Person)
        form = PersonForm(name='John Doe', age=123)
        form.populate_obj(john)
        assert john.name == 'John Doe'
        assert john.age == 123
        # TODO: check if validator Required is translated, etc.
