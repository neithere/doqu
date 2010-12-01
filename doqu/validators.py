# -*- coding: utf-8 -*-
#
#    Doqu is a lightweight schema/query framework for document databases.
#    Copyright © 2009—2010  Andrey Mikhaylenko
#
#    This file is part of Docu.
#
#    Doqu is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Doqu is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Docu.  If not, see <http://gnu.org/licenses/>.

"""
Validators
==========

A validator simply takes an input and verifies it fulfills some criterion, such as
a maximum length for a string. If the validation fails, a
:class:`~ValidationError` is raised. This simple system allows chaining any
number of validators on fields.

The module is heavily inspired by (and partially ripped off from) the
`WTForms`_ validators. However, ours serve a bit different purpose. First,
error messages are not needed here (the errors will not be displayed to end
users). Second, these validators include **query filtering** capabilities.

Usage example::

    class Person(Document):
        validators = {
            'first_name': [required(), length(min=2)],
            'age': [number_range(min=18)],
        }

This document will raise :class:`ValidationError` if you attempt to save it
with wrong values. You can call :meth:`Document.is_valid` to ensure everything is OK.

Now let's query the database for all objects of `Person`::

    Person.objects(db)

Doqu does not deal with tables or collections, it follows the DRY (Don't
Repeat Yourself) principle and uses the same validators to determine what
database records belong to given document class. The schema defined above is
alone equivalent to the following query::

    ...where(first_name__exists=True, age__gte=18).where_not(first_name='')

This is actually the base query available as ``Person.objects(db)``.

.. note:: not all validators affect document-related queries. See detailed
    documentation on each validator.

.. _WTForms: http://wtforms.simplecodes.com

"""

import re


__all__ = [
    # exceptions
    'StopValidation', 'ValidationError',

    # validators
    'Email', 'email',
    'EqualTo', 'equal_to',
    'Equals', 'equals',
    'Exists', 'exists',
    'IPAddress', 'ip_address',
    'Length', 'length',
    'NumberRange', 'number_range',
    'Optional', 'optional',
    'Required', 'required',
    'Regexp', 'regexp',
    'URL', 'url',
    'AnyOf', 'any_of',
    'NoneOf', 'none_of'
    # TODO 'Unique', 'unique',
]


#--------------+
#  Exceptions  |
#--------------+


class StopValidation(Exception):
    """
    Causes the validation chain to stop.

    If StopValidation is raised, no more validators in the validation chain are
    called.
    """
    pass

class ValidationError(ValueError):
    """
    Raised when a validator fails to validate its input.
    """
    pass


#--------------+
#  Validators  |
#--------------+


class Equals(object):
    """
    Compares the value to another value.

    :param other_value:
        The other value to compare to.

    Adds conditions to the document-related queries.
    """
    def __init__(self, other_value):
        self.other_value = other_value

    def __call__(self, instance, value):
        if not self.other_value == value:
            raise ValidationError

    def filter_query(self, query, name):
        return query.where(**{
            name: self.other_value
        })


class EqualTo(object):
    """
    Compares the values of two fields.

    :param name:
        The name of the other field to compare to.
    """
    def __init__(self, name):
        self.name = name

    def __call__(self, instance, value):
        if not instance[self.name] == value:
            raise ValidationError


class Exists(object):
    """
    Ensures given field exists in the record. This does not affect validation
    of a document with pre-defined structure but does affect queries.

    Adds conditions to the document-related queries.
    """
    def __call__(self, instance, value):
        # of course it exists!
        pass

    def filter_query(self, query, name):
        return query.where(**{
            '{0}__exists'.format(name): True
        })


class Length(object):
    """
    Validates the length of a string.

    :param min:
        The minimum required length of the string. If not provided, minimum
        length will not be checked.
    :param max:
        The maximum length of the string. If not provided, maximum length
        will not be checked.
    """
    def __init__(self, min=None, max=None):
        assert not all(x is None for x in (min,max))
        self.min = min
        self.max = max

    def __call__(self, instance, value):
        if self.min is not None and len(value) < self.min:
            raise ValidationError
        if self.max is not None and self.max < len(value):
            raise ValidationError


class NumberRange(object):
    """
    Validates that a number is of a minimum and/or maximum value, inclusive.
    This will work with any comparable number type, such as floats and
    decimals, not just integers.

    :param min:
        The minimum required value of the number. If not provided, minimum
        value will not be checked.
    :param max:
        The maximum value of the number. If not provided, maximum value
        will not be checked.

    Adds conditions to the document-related queries.
    """
    def __init__(self, min=None, max=None):
        assert min is not None or max is not None
        self.min = min
        self.max = max

    def __call__(self, instance, value):
        if self.min is not None and value < self.min:
            raise ValidationError
        if self.max is not None and self.max < value:
            raise ValidationError

    def filter_query(self, query, name):
        conditions = {}
        if self.min is not None:
            conditions.update({'%s__gte'%name: self.min})
        if self.max is not None:
            conditions.update({'%s__lte'%name: self.max})
        return query.where(**conditions)


class Optional(object):
    """
    Allows empty value (i.e. ``bool(value) == False``) and terminates the
    validation chain for this field (i.e. no more validators are applied to
    it). Note that errors raised prior to this validator are not suppressed.
    """
    def __call__(self, instance, value):
        if not value:
            raise StopValidation


class Required(object):
    """
    Requires that the value is not empty, i.e. ``bool(value)`` returns `True`.
    The `bool` values can also be `False` (but not anything else).

    Adds conditions to the document-related queries: the field must exist and
    be not equal to an empty string.
    """
    def __call__(self, instance, value):
        if not value and value != False:
            raise ValidationError

    def filter_query(self, query, name):
        # defined and not empty
        return query.where(**{
            '{0}__exists'.format(name): True,
        }).where_not(**{
            '{0}__equals'.format(name): '',
        })


class Regexp(object):
    """
    Validates the field against a user provided regexp.

    :param regex:
        The regular expression string to use.
    :param flags:
        The regexp flags to use, for example `re.IGNORECASE` or `re.UNICODE`.

    .. note:: the pattern must be provided as string because compiled patterns
        cannot be used in database lookups.

    Adds conditions to the document-related queries: the field must match the
    pattern.
    """
    def __init__(self, pattern, flags=0):
        # pre-compiled patterns are not accepted because they can't be used in
        # database lookups
        assert isinstance(pattern, basestring)
        self.pattern = pattern
        self.regex = re.compile(pattern, flags)

    def __call__(self, instance, value):
        if not self.regex.match(value or ''):
            raise ValidationError

    def filter_query(self, query, name):
        return query.where(**{'{0}__matches'.format(name): True})


class Email(Regexp):
    """
    Validates an email address. Note that this uses a very primitive regular
    expression and should only be used in instances where you later verify by
    other means, such as email activation or lookups.

    Adds conditions to the document-related queries: the field must match the
    pattern.
    """
    def __init__(self):
        super(Email, self).__init__(r'^.+@[^.].*\.[a-z]{2,10}$', re.IGNORECASE)


class IPAddress(Regexp):
    """
    Validates an IP(v4) address.

    Adds conditions to the document-related queries: the field must match the
    pattern.
    """
    def __init__(self):
        super(IPAddress, self).__init__(r'^([0-9]{1,3}\.){3}[0-9]{1,3}$')


class URL(Regexp):
    """
    Simple regexp based url validation. Much like the email validator, you
    probably want to validate the url later by other means if the url must
    resolve.

    :param require_tld:
        If true, then the domain-name portion of the URL must contain a .tld
        suffix.  Set this to false if you want to allow domains like
        `localhost`.

    Adds conditions to the document-related queries: the field must match the
    pattern.
    """
    def __init__(self, require_tld=True):
        tld_part = (require_tld and ur'\.[a-z]{2,10}' or u'')
        regex = ur'^[a-z]+://([^/:]+%s|([0-9]{1,3}\.){3}[0-9]{1,3})(:[0-9]+)?(\/.*)?$' % tld_part
        super(URL, self).__init__(regex, re.IGNORECASE)


class Unique(object):
    def __call__(self, instance, value):
        # XXX TODO
        raise NotImplementedError


class AnyOf(object):
    """
    Compares the incoming data to a sequence of valid inputs.

    :param choices:
        A sequence of valid inputs.

    Adds conditions to the document-related queries.
    """
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, instance, value):
        if value not in self.choices:
            raise ValidationError

    def filter_query(self, query, name):
        return query.where(**{name+'__in': self.choices})


class NoneOf(object):
    """
    Compares the incoming data to a sequence of invalid inputs.

    :param choices:
        A sequence of invalid inputs.

    Adds conditions to the document-related queries.
    """
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, instance, value):
        if value in self.choices:
            raise ValidationError

    def filter_query(self, query, name):
        return query.where_not(**{name+'__in': self.choices})


email = Email
equals = Equals
equal_to = EqualTo
exists = Exists
ip_address = IPAddress
length = Length
number_range = NumberRange
optional = Optional
required = Required
regexp = Regexp
# TODO: unique = Unique
url = URL
any_of = AnyOf
none_of = NoneOf

