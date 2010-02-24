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



__doc__ = """
>>> import datetime
>>> from pymodels import Model, Property, Date, Reference, get_storage

>>> SETTINGS_TYRANT = {
...     'backend': 'pymodels.backends.tokyo_tyrant',
...     'host': 'localhost',
...     'port': 1983,
... }

#>>> SETTINGS_CABINET = {
#...     'backend': 'pymodels.backends.tokyo_cabinet',
#...     'kind': 'TABLE',
#...     'path': '_test.tct',
#... }

>>> storage = get_storage(SETTINGS_TYRANT)


>>> class Country(Model):
...     name = Property()
...
...     def __unicode__(self):
...         return self.name
...
...     class Meta:
...         must_have = {'is_location': True}

>>> class Person(Model):
...     first_name = Property(required=True)
...     middle_name = Property()
...     last_name = Property(required=True)
...     gender = Property()
...     birth_date = Date()
...     birth_place = Reference(Country)
...     nick = Property()
...     website = Property()
...     residence = Reference(Country)
...
...     @property
...     def age(self):
...         return (datetime.datetime.now().date() - self.birth_date).days / 365
...
...     @property
...     def full_name(self):
...         return ('%s %s' % (self.first_name, self.last_name)).strip()
...
...     def __unicode__(self):
...         return self.full_name
...
...     class Meta:
...         must_have = {'first_name__exists': True, 'last_name__exists': True}

>>> class User(Person):
...     username = Property(required=True)
...
...     def __unicode__(self):
...         return u'%s "%s" %s' % (self.first_name, self.username, self.last_name)
...
...     class Meta:
...         must_have = {'username__exists': True}

## creating a model instance, accessing fields, saving instance (with validation)

>>> john = Person(first_name='John', birth_date=datetime.date(1901, 2, 3))
>>> john.save(storage)
Traceback (most recent call last):
...
ValidationError: property Person.last_name is required
>>> john.last_name = 'Doe'
>>> john
<Person John Doe>
>>> john.birth_date
datetime.date(1901, 2, 3)
>>> john.birth_date = 'WRONG VALUE'
>>> john.save(storage)
Traceback (most recent call last):
...
ValidationError: Expected a datetime.date instance, got "WRONG VALUE"
>>> john.birth_date = datetime.date(1901, 2, 3)
>>> john.save(storage)
'person_0'
>>> john.birth_place = Country(name='TestCountry')
>>> john.save(storage)
'person_0'
>>> john.birth_place
<Country TestCountry>
>>> Country.objects(storage)
[<Country TestCountry>]
>>> Country(name='Another Country').save(storage)
'country_1'
>>> Country(name='Yet Another Country').save(storage)
'country_2'

## properties of saved instance are correctly restored to Python objects:

>>> Person.objects(storage)
[<Person John Doe>]
>>> john_db = Person.objects(storage)[0]
>>> john_db == john
True
>>> john.full_name == john_db.full_name
True
>>> john.birth_date == john_db.birth_date
True
>>> john_db_2 = storage.get(Person, john.pk)
>>> john_db_2 == john
True

## Inherited properties:

>>> u = User()
>>> hasattr(u, 'first_name')
True
>>> hasattr(u, 'username')
True
>>> hasattr(u, '_meta')
True
>>> u._meta.must_have == {'first_name__exists': True,
...                       'last_name__exists': True,
...                       'username__exists': True}
True

## Inherited identification query (Model.Meta.must_have):

>>> User.objects(storage)
[]

>>> user = john.convert_to(User)
>>> user.username = 'johnny'
>>> user
<User John "johnny" Doe>
>>> user.save(storage)
'person_0'
>>> User.objects(storage)
[<User John "johnny" Doe>]
>>> Person.objects(storage)
[<Person John Doe>]

"""
