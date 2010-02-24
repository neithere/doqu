# -*- coding: utf-8 -*-
"""
>>> import datetime
>>> from pymodels import *

>>> today = datetime.datetime.now().date()

>>> class Document(Model):
...     title = Property()
...     text = Property()
...
...     class Meta:
...         must_have = {'title__exists': True, 'text__exists': True}
...
...     def __unicode__(self):
...         return unicode(self.title)
...
...     foo = 123    # a random attr unrelated to PyModels must be inherited

>>> class BlogPost(Document):
...     pub_date = Date()
...
...     class Meta:
...         must_have = {'pub_date__exists': True}

>>> class Publication(BlogPost):
...
...     class Meta:
...         must_have = {'pub_date__gt': 0}
...
...     def save(self, *args, **kwargs):
...         self.pub_date = today
...         super(Document, self).save(*args, **kwargs)
...
...     foo = 456    # a random attr unrelated to PyModels must be overloaded

>>> class Draft(BlogPost):
...
...     class Meta:
...         must_have = {'pub_date': None}

>>> class CategorizedPublication(Publication):
...     category = Property()
...
...     class Meta:
...         must_have = {'category__exists': True}


# NON PYMODELS-RELATED ATTRIBUTES ARE INHERITED AND OVERLOADED

>>> Draft.foo
123
>>> Publication.foo
456
>>> CategorizedPublication.foo
456

# MODEL PROPERTIES ARE INHERITED:

>>> Document._meta.prop_names
['title', 'text']
>>> BlogPost._meta.prop_names
['title', 'text', 'pub_date']
>>> Publication._meta.prop_names
['title', 'text', 'pub_date']
>>> Draft._meta.prop_names
['title', 'text', 'pub_date']
>>> CategorizedPublication._meta.prop_names
['title', 'text', 'pub_date', 'category']

# MODEL IDENTITY IS INHERITED:

>>> Document._meta.must_have == {'title__exists': True, 'text__exists': True}
True
>>> BlogPost._meta.must_have == dict(Document._meta.must_have,
...                                  pub_date__exists=True)
True
>>> Publication._meta.must_have == dict(BlogPost._meta.must_have, pub_date__gt=0)
True
>>> Draft._meta.must_have == dict(BlogPost._meta.must_have, pub_date=None)
True
>>> CategorizedPublication._meta.must_have == dict(Publication._meta.must_have,
...                                                category__exists=True)
True

# OBJECTS BEHAVE CORRECTLY:

>>> db = get_storage(backend='pymodels.backends.tokyo_tyrant', port=1983)

>>> draft = Draft(title='Hello', text='What a beautiful world!')
>>> draft.save(db)
'draft_0'
>>> bool(draft.pub_date)
False
>>> Document.objects(db)
[<Document Hello>]
>>> doc = Document.objects(db)[0]
>>> doc == draft
True
>>> doc, draft
(<Document Hello>, <Draft Hello>)

>>> pub = draft.convert_to(Publication)
>>> isinstance(pub, Publication)
True
>>> pub.pub_date == draft.pub_date == None    # not changed until saved again
True
>>> pub.save(db)
>>> pub.pub_date == today
True

>>> cp = pub.convert_to(CategorizedPublication, {'category': 'exclamations'})
>>> cp.pub_date == pub.pub_date
True
>>> cp.title == 'Hello'
True
>>> cp.category == 'exclamations'
True

>>> sorted(cp._meta.props.keys()) == sorted(CategorizedPublication._meta.prop_names)
True
>>> cp._meta.must_have == CategorizedPublication._meta.must_have
True

"""
