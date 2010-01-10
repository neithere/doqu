# -*- coding: utf-8 -*-
#
#    Models is a framework for mapping Python classes to semi-structured data.
#    Copyright © 2009—2010  Andrey Mikhaylenko
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

__doc__ = """
>>> import datetime
>>> from models import Model, Property, Date, Reference
>>> from models.backends.tyrant import Storage
>>> storage = Storage()

>>> class Country(Model):
...     name = Property()
...
...     def __unicode__(self):
...         return self.name
...
...     class Meta:
...         must_have = {'type': 'country___test'}

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
...         must_have = {'type': 'person___test'}

>>> class User(Person):
...     username = Property(required=True)
...
...     def __unicode__(self):
...         return u'%s "%s" %s' % (self.first_name, self.username, self.last_name)

## creating a model instance, accessing fields, saving instance (with validation)

>>> john = Person('test___0001', first_name='John', birth_date=datetime.date(1901, 2, 3))
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
ValidationError: Bad date value "WRONG VALUE": 'str' object has no attribute 'isoformat'
>>> john.birth_date = datetime.date(1901, 2, 3)
>>> john.save(storage)
'test___0001'
>>> john.birth_place = Country('test___0002', name='TestCountry')
>>> john.save(storage)
'test___0001'
>>> john.birth_place
<Country TestCountry>
>>> Country.query(storage)
[<Country TestCountry>]

## properties of saved instance are correctly restored to Python objects:

>>> Person.query(storage)
[<Person John Doe>]
>>> john_db = Person.query(storage)[0]
>>> john.full_name == john_db.full_name
True
>>> john.birth_date == john_db.birth_date
True

## Inherited properties:

>>> u = User()
>>> hasattr(u, 'first_name')
True
>>> hasattr(u, 'username')
True
>>> hasattr(u, '_meta')
True
>>> u._meta.must_have
{'type': 'person___test'}

## Inherited identification query (Model.Meta.must_have):

>>> User.query(storage)
[<User John "None" Doe>]

>>> User.query(storage)
[<User John "None" Doe>]

>>> user = User.query(storage)[0]
>>> user.username = 'johnny'
>>> user
<User John "johnny" Doe>
>>> user.save(storage)
u'test___0001'
>>> User.query(storage)
[<User John "johnny" Doe>]

"""
