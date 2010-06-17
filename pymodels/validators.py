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

"""
Validators
~~~~~~~~~~

Inspired by (and partially ripped off from) the `WTForms`_ validators. However,
this module serves a bit different purpose. First, error messages are not
needed here (the errors will not be displayed to end users). Second, these
validators include query filtering capabilities. When a validator is added to
the document definition, the document objects are filtered with regard to such
validator.

.. _WTForms: http://wtforms.simplecodes.com

"""

import re


__all__ = [
    # exceptions
    'StopValidation', 'ValidationError',

    # validators
    'Email', 'email',
    'EqualTo', 'equal_to',
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


# validators
# XXX see http://bitbucket.org/simplecodes/wtforms/src/tip/wtforms/validators.py
# we can almost copy that, just replace form with model instance and drop
# accumulation or errors because we don't have to display them, we just die on
# first unrecoverable validation error (i.e. when all validators fail with
# ValidationError or one validator raises StopValidation)
# What's interesting is that non-class validators can be more or less easily
# converted to actual queries!
#
# http://bitbucket.org/simplecodes/wtforms/src/tip/wtforms/validators.py -- WTForms validators
# http://bitbucket.org/namlook/mongokit/wiki/html/tutorial.html#validate-keys -- MongoKit validators
# http://bitbucket.org/namlook/mongokit/src


#--------------+
#  Exceptions  |
#--------------+


class StopValidation(Exception):
    pass

class ValidationError(Exception):
    pass


#--------------+
#  Validators  |
#--------------+


class EqualTo(object):
    def __init__(self, name):
        self.name = name

    def __call__(self, instance, value):
        if not instance[self.name] == value:
            raise ValidationError


class Length(object):
    def __init__(self, min=None, max=None):
        self.min = min
        self.max = max

    def __call__(self, instance, value):
        if self.min is not None and len(value) < self.min:
            raise ValidationError
        if self.max is not None and self.max < len(value):
            raise ValidationError


class NumberRange(object):
    def __init__(self, min, max):
        self.min = min
        self.max = max

    def __call__(self, instance, value):
        if self.min <= value <= self.max:
            return
        raise ValidationError


class Optional(object):
    def __call__(self, instance, value):
        if not value:
            raise StopValidation


class Required(object):
    def __call__(self, instance, value):
        if not value and value != False:
            raise ValidationError

    def filter_query(self, query, name):
        # defined and not empty
        return query.where(**{
            '%s__exists'%name: True,
        }).where_not(**{
            '%s__equals'%name: '',
        })


class Regexp(object):
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
        return query.where(**{'%s__matches'%name: True})


class Email(Regexp):
    """
    Validates an email address. Note that this uses a very primitive regular
    expression and should only be used in instances where you later verify by
    other means, such as email activation or lookups.
    """
    def __init__(self):
        super(Email, self).__init__(r'^.+@[^.].*\.[a-z]{2,10}$', re.IGNORECASE)


class IPAddress(Regexp):
    """
    Validates an IP(v4) address.
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
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, instance, value):
        if value not in self.choices:
            raise ValidationError

    def filter_query(self, query, name):
        return query.where(**{name+'__in': self.choices})


class NoneOf(object):
    def __init__(self, choices):
        self.choices = choices

    def __call__(self, instance, value):
        if value in self.choices:
            raise ValidationError

    def filter_query(self, query, name):
        return query.where_not(**{name+'__in': self.choices})


email = Email
equal_to = EqualTo
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

