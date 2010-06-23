Usage examples
==============

A few words on what a model is
------------------------------

First off, what is a model? Well, it's something that represents an object. The
object can be stored in a database. We can fetch it from there, modify and push
back.

How is a model different from a Python dictionary then? Easy. Dictionaries know
nothing about where the data came from, what parts of it are important for us,
how the values should be converted to and fro, and how should the data be
validated before it is stored somewhere. A model of an apple *does* know what
properties should an object have to be a Proper Apple; what can be done the
apple so that it does not stop being a Proper Apple; and where does the apple
belong so it won't be in the way when it isn't needed anymore.

In other words, the model is an answer to questions *what*, *where* and *how*
about a document. And a dictionary *is* a document (or, more precisely, a
simple representation of the document in given environment).

Defining models
---------------

The simplest possible model::

    class Thing(Document):
        pass

Just a Python class. Not very useful as it does not specify any property. Let's
observe the object thoroughly and conclude that colour is an important
distinctive feature of this... um, sort of thing::

    class Thing(Document):
        structure = {
            'colour': unicode
        }

Great, now *that's* a model. It recognizes a property as significant. Now we
can compare, search and distinguish *objects* by colour (and its presence or
lack). Obviously, if colour is an applicable property for an object, then it
*belongs* to this model.

A more complete example which will look familiar to those who had ever used an
ORM (e.g. the Django one)::

    import datetime
    from docu import *

    class Country(Document):
        structure = {
            'name': unicode    # any Python type; default is unicode
        }
        validators = {
            'type': [AnyOf(['country'])]
        }

        def __unicode__(self):
            return self['name']

    class Person(Document):
        structure = {
            'first_name': unicode,
            'last_name': unicode,
            'gender': unicode,
            'birth_date': datetime.date,
            'birth_place': Country,    # reference to another model
        }
        validators = {
            'first_name': [required()],
            'last_name': [required()],
        }
        use_dot_notation = True

        def __unicode__(self):
            return u'{first_name} {last_name}'.format(**self)

        @property
        def age(self):
            return (datetime.datetime.now().date() - self.birth_date).days / 365

The interesting part is the Meta subclass. It contains a must_have attribute
which actually binds the model to a subset of data in the storage.
``{'first_name__exists': True}`` states that a data row/document/... must
have the field `first_name` defined (not necessarily non-empty). You can easily
define any other query conditions (currently with respect to the backend's
syntax but we hope to unify things). When you create an empty model instance, it
will have all the "must haves" pre-filled if they are not complex lookups (e.g.
`Country` will have its `type` set to `True`, but we cannot do that with
`Person`'s constraints). 

Inheritance
-----------

Let's define another model::

    class Woman(Person):
        class Meta:
            must_have = {'gender': 'female'}

Or even that one::

    today = datetime.datetime.now()
    day_16_years_back = now - datetime.timedelta(days=16*365)

    class Child(Person):
        parent = Reference(Person)

        class Meta:
            must_have = {'birth_date__gte': day_16_years_back}

Note that our `Woman` or `Child` models are subclasses of `Person` model. They
inherit all attributes of `Person`. Moreover, `Person`'s metaclass is inherited
too. The `must_have` dictionaries of `Child` and `Woman` models are `merged`
into the parent model's dictionary, so when we query the database for records
described by the `Woman` model, we get all records that have `first_name` and
`last_name` defined and `gender` set to "female". When we edit a `Person`
instance, we do not care about the `parent` attribute; we actually don't even
have access to it.

Model is a query, not a container
---------------------------------

We can even deal with data described above without model inheritance. Consider
this valid model -- `LivingBeing`::

    class LivingBeing(Model):
        species = Property()
        birth_date = Property()

        class Meta:
            must_have = {'birth_date__exists': True}

The data described by `LivingBeing` overlaps the data described by `Person`.
Some people have their birth dates not deifined and `Person` allows that.
However, `LivingBeing` requires this attribute, so not all people will appear
in a query by this model. At the same time `LivingBeing` does not require names,
so anybody and anything, named or nameless, but ever born, is a "living being".
Updating a record through any of these models will not touch data that the model
does not know. For instance, saving an entity as a `LivingBeing` will not remove
its name or parent, and working with it as a `Child` will neither expose nor
destroy the information about species.

These examples illustrate how models are more "views" than "schemata".

Now let's try these models with a Tokyo Cabinet database::

    >>> db = docu.get_db(
    ...     backend = 'docu.ext.tokyo_cabinet',
    ...     path = 'test.tct'
    ... )
    >>> guido = Person(first_name='Guido', last_name='van Rossum')
    >>> guido
    <Person Guido van Rossum>
    >>> guido.first_name
    Guido
    >>> guido.birth_date = datetime.date(1960, 1, 31)
    >>> guido.save(db)    # returns the autogenerated primary key
    'person_0'
    >>> ppl_named_guido = Person.objects(db).where(first_name='Guido')
    >>> ppl_named_guido
    [<Person Guido van Rossum>]
    >>> guido = ppl_named_guido[0]
    >>> guido.age    # calculated on the fly -- datetime conversion works
    49
    >>> guido.birth_place = Country(name='Netherlands')
    >>> guido.save()    # model instance already knows the storage it belongs to
    'person_0'
    >>> guido.birth_place
    <Country Netherlands>
    >>> Country.objects(db)    # yep, it was saved automatically with Guido
    [<Country Netherlands>]
    >>> larry = Person(first_name='Larry', last_name='Wall')
    >>> larry.save(db)
    'person_2'
    >>> Person.objects(db)
    [<Person Guido van Rossum>, <Person Larry Wall>]

...and so on.

Note that relations are supported out of the box.
