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

import datetime
from functools import wraps
import re

from docu.backend_base import LookupManager


__all__ = ['lookup_manager']


class MongoLookupManager(LookupManager):
    """
    Lookup manager for the Docu's MongoDB adapter.
    """
    def combine_conditions(self, conditions):
        """
        Expects a list of conditions, each returned by a lookup processor from
        the Docu MongoDB adapter.

        Returns the resulting `query document`_ ("spec").

        .. _query document: http://mongodb.org/display/DOCS/Querying

        """
        # we merge all conditions into a single dictionary; calling find() in a
        # sequence may be a better idea(?) because smth like:
        #  [{'foo': {'$gt': 0}}, {'foo': {'$lt': 5}}]
        # will yield an equivalent of `foo < 5` instead of `0 < foo < 5`.
        # We try to alleviate this issue by respecting an extra level but a
        # more complex structure can be crippled.
        spec = {}
        for condition in conditions:
            for name, clause in condition.iteritems():
                if isinstance(clause, dict):
                    spec.setdefault(name, {}).update(clause)
                else:
                    # exact or regex. Specifying multiple conditions against
                    # same fields will result in name clashes so we try to
                    # avoid that by wrapping "simple" conditions in an array.
                    # Note that this doesn't remove all possible problems, just
                    # the most common ones.
                    conds = spec.setdefault(name, {}).setdefault('$all', [])
                    conds.append(clause)
        #print 'MONGO spec', spec
        return spec


lookup_manager = MongoLookupManager()


DEFAULT_OPERATION = 'equals'


#----------------------------------------------------------------------------------
# See http://www.mongodb.org/display/DOCS/Advanced+Queries
#

lookup_processors = {
    'contains':     lambda v: (
        ('$all', [re.compile(x) for x in v])
        if isinstance(v, (list,tuple))
        else lookup_processors['matches'](v)
    ),
    'contains_any': lambda v: ('$in', [re.compile(x) for x in v]),
    'endswith':     lambda v: (None, re.compile('{0}$'.format(v))),
    'equals':       lambda v: (None, v),
    'exists':       lambda v: ('$exists', v),
    'gt':           lambda v: ('$gt',  v),
    'gte':          lambda v: ('$gte', v),
    'in':           lambda v: ('$in', v),
#   'like':         lambda a,b: NotImplemented,
#   'like_any':     lambda a,b: NotImplemented,
    'lt':           lambda v: ('$lt', v),
    'lte':          lambda v: ('$lte', v),
    'matches':      lambda v: (None, re.compile(v)),
#   'search':       lambda a,b: NotImplemented,
    'startswith':   lambda v: (None, re.compile('^{0}'.format(v))),
    'year':         lambda v: (None, re.compile(r'^{0}....'.format(v))),
    'month':        lambda v: (None, re.compile(r'^....{0:02}..'.format(v))),
    'day':          lambda v: (None, re.compile(r'^......{0:02}'.format(v))),
}
meta_lookups = {
    'between': lambda values: [('gt', values[0]),
                               ('lt', values[1])],
}
inline_negation = {
    'equals': '$ne',
    'in': '$nin',
    # XXX be careful with gt/lt/gte/lte: "not < 2" != "> 2"
}

def autonegated_lookup(processor, operation):
    "wrapper for lookup processors; handles negation"
    @wraps(processor)
    def inner(name, value, data_processor, negated):
        op, val = processor(value, data_processor)
        expr = {op: val} if op else val
        if negated:
            neg = inline_negation.get(operation)
            if neg:
                return {name: {neg: val}}
            return {name: {'$not': expr}}
        return {name: expr}
    return inner

def autocoersed_lookup(processor):
    "wrapper for lookup processors; handles value coersion"
    @wraps(processor)
    def inner(value, data_processor):   # negation to be handled outside
        return processor(data_processor(value))
    return inner

def meta_lookup(processor):
    """
    A wrapper for lookup processors. Delegates the task to multiple simple
    lookup processors (e.g. "between 1,3" can generate lookups "gt 1", "lt 3").
    """
    @wraps(processor)
    def inner(name, value, data_processor, negated):
        pairs = processor(value)
        for _operation, _value in pairs:
            p = lookup_manager.get_processor(_operation)
            yield p(name, _value, data_processor, negated)
    return inner

for operation, processor in lookup_processors.items():
    is_default = operation == DEFAULT_OPERATION
    processor = autocoersed_lookup(processor)
    processor = autonegated_lookup(processor, operation)
    lookup_manager.register(operation, default=is_default)(processor)

for operation, mapper in meta_lookups.items():
    processor = meta_lookup(mapper)#, operation)
    lookup_manager.register(operation)(processor)
