Tutorial
========

.. warning:: this document must be rewritten from scratch

What does Docu do?
------------------

Why document-oriented?
----------------------

Why not just use the library X for database Y?
----------------------------------------------

Native Python bindings exist for most databases. It is preferable to use a
dedicated library if you are absolutely sure that your code will never be used
with another database. But there are two common use cases when Docu is much
more preferable:

a) prototyping: if you are unsure about which database fits your requirements
   best and wish to test various databases against your code, just write your
   code with Docu and then try switching backends to see which performs best.
   Then optimize the code for it.
b) reusing the code: if you expect the module to be plugged into an application
   with unpredictable settings, use Docu.

Of course we are talking about document databases. For relational databases you
would use an ORM.

What are "backends"?
--------------------

.. warning:: this section is out of date

Docu can be used with a multitude of databases providing a uniform API for
retrieving, storing, removing and searching of records. To couple Docu with
a database, a storage/query backend is needed.

A "**backend**" is a module that provides two classes: `Storage` and `Query`.
Both must conform to the basic specifications (see basic specs below).
Backends may not be able to implement all default methods; they may also
provide some extra methods.

The **Storage** class is an interface for the database. It allows
to add, read, create and update records by primary keys. You will not use this
class directly in your code.

The **Query** class is what you will talk
to when filtering objects of a model. There are no constraints on how the
search conditions should be represented. This is likely to cause some problems
when you switch from one backend to another. Some guidlines will be probably
defined to address the issue of portability. For now we try to ensure that all
default backends share the conventions defined by the Tokyo Tyrant backend.

Switching backends
------------------

.. warning:: this section is out of date

Let's assume we have a Tokyo Cabinet database. You can choose the TC backend to
use the DB file :doc:`directly <ext_tokyo_cabinet>` or access the same file
:doc:`through the manager <ext_tokyo_tyrant>`. The first option is great
for development and some other cases where you would use SQLite; the second
option is important for most production environments where multiple connections
are expected. The good news is that there's no more import and export,
dump/load sequences, create/alter/drop and friends. Having tested the
application against the database `storage.tct` with Cabinet backend, just run
`ttserver storage.tct` and switch the backend config.

Let's create our application::

    import docu
    import settings
    from models import Country, Person

    storage = docu.get_storage(settings.DATABASE)

    print Person.objects(storage)   # prints all Person objects from DB

Now define settings for both backends (settings.py)::

    # direct access to the database (simple, not scalable)
    TOKYO_CABINET_DATABASE = {
        'backend': 'docu.ext.tokyo_cabinet',
        'kind': 'TABLE',
        'path': 'storage.tct',
    }

    # access through the Tyrant manager (needs daemon, scalable)
    TOKYO_TYRANT_DATABASE = {
        'backend': 'docu.ext.tokyo_tyrant',
        'host': 'localhost',
        'port': 1978,
    }

    # this is the *only* line you need to change in order to change the backend
    DATABASE = TOKYO_CABINET_DATABASE


A few words on what a model is
------------------------------

.. warning:: this section is out of date

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

Working with documents
----------------------

.. warning:: this section is out of date

A :term:`document` is basically a "dictionary on steroids". Let's create a
document::

    >>> from docu import *
    >>> document = Document(foo=123, bar='baz')
    >>> document['foo']
    123
    >>> document['foo'] = 456

Well, any dictionary can do that. But wait::

    >>> db = get_db(backend='docu.ext.shove')
    >>> document.save(db)
    'new-primary-key'
    >>> Document.objects(db)
    [<Document: instance>]
    >>> fetched = Document.objects(db)[0]
    >>> document == fetched
    True
    >>> fetched['bar']
    'baz'

Aha, so :class:`~docu.document_base.Document` supports persistence! Nice. By
the way, how about some syntactic sugar? Here::

    class MyDoc(Document):
        use_dot_notation = True

That's the same good old `Document` but with "dot notation" switched on. It
allows access to keys with ``__getattr__`` as well as with ``__getitem__``::

    >>> my_doc = MyDoc(foo=123)
    >>> my_doc.foo
    123

Of course this will only work with alphanumeric keys.

Now let's say we are going to make a little address book. We don't want any
"foo" or "bar, just the relevant information. And the "foo" key should not be
allowed in such documents. Can we restrict the :term:`structure <schema>` to
certain keys and data types? Let's see::

    class Person(Document):
        structure = {'name': unicode, 'email': unicode}

Great, now the names and values are controlled. The document will raise an
exception when someone, say, attempts to put a number instead of the email.

.. note::

    Any built-in type will do; some classes are also accepted (like
    `datetime.date` et al). Even Document instances are accepted: they are
    interpreted as references. The exact set of supported types and classes is
    defined per storage backend because the data must be (de)serialized. It is
    possible to register custom converters in runtime.

(Note that the values can  be `None`.) But what if we need to mark some fields
as required? Or what if the email is indeed a unicode string but its content
has nothing to do with RFC 5322? We need to prevent malformed data from being
saved into the database. That's the daily job for :term:`validators
<validator>`::

    from docu.validators import *

    class Person(Document):
        structure = {
            'name': unicode,
            'email': unicode,
        }
        validators = {
            'name': [required()],
            'email': [optional(), email()],
        }

This will only allow correct data into the storage.

.. note::
    
    At this point you may ask why are the definitions so verbose. Why not Field
    classes à la Django? Well, they *can* be added on top of what's described
    here. Actually Docu ships with :doc:`fields` so you can easily write::

        class Person(Document):
            name = Field(unicode, required=True)
            email = EmailField()    # this class is not implemented but can be
    
    Why isn't this approach used by default? Well, it turned out that such
    classes introduce more problems than they solve. Too much magic, you know.
    Also, they quickly become a name + clutter thing. Compact but unreadable.
    So we adopted the MongoKit approach, i.e. semantic grouping of attributes.
    And — guess what? — the document classes became **much** easier to
    understand. Despite the definitions are a bit longer. And remember, it is
    always possible to add syntax sugar, but it's usually extremely hard to
    *remove* it.

And now, surprise: validators do an extra favour for us! Look::

    XXX an example of query; previously defined documents are not shown because
    records are filtered by validators

More questions?
---------------

If you can't find the answer to your questions on Docu in the documentation,
feel free to ask in the `discussion group`_.

.. _discussion group: http://groups.google.com/group/docu-users

------------ XXXXXXXXXX The part below is outdated ----------------

The Document behaves Let's
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

.. warning:: this section is out of date

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

.. warning:: this section is out of date

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
