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

import datetime
from functools import wraps
import re

from pymodels.backend_base import LookupManager


__all__ = ['lookup_manager']


lookup_manager = LookupManager()


DEFAULT_OPERATION = 'equals'

# we define operations as functions that expect
mapping = {
#    'between':      lambda a,b: b is not None and a[0] <= b <= a[1],
    'contains':     lambda k,v,p,n: {},# TODO {k: {'$nin' if n else '$in': p(v)}},
#    'contains_any': lambda a,b: b is not None and any(x in b for x in a),
#    'endswith':     lambda a,b: b is not None and b.endswith(a),
    'equals':       lambda k,v,p,n: {k: {'$ne':p(v)} if n else p(v)},
    'exists':       lambda k,v,p,n: {k: {'$exists': not n}},
    'gt':           lambda k,v,p,n: {k: {'$lt' if n else '$gt': p(v)}},
    'gte':          lambda k,v,p,n: {k: {'$lte' if n else '$gte': p(v)}},
#    'gt':           lambda a,b: b is not None and a < b,
#    'gte':          lambda a,b: b is not None and a <= b,
    'in':           lambda k,v,p,n: {k: {'$in': p(v)}},
#   'like':         lambda a,b: NotImplemented,
#   'like_any':     lambda a,b: NotImplemented,
    'lt':           lambda k,v,p,n: {k: {'$gt' if n else '$gt': p(v)}},
    'lte':          lambda k,v,p,n: {k: {'$gte' if n else '$gte': p(v)}},
#    'lte':          lambda a,b: b is not None and b <= a,
#    'matches':      lambda a,b: re.search(a, b),   # XXX pre-compile?
#   'search':       lambda a,b: NotImplemented,
#    'startswith':   lambda a,b: b and b.startswith(a),
#    'year':         lambda a,b: b and b.year == a,
#    'month':        lambda a,b: b and b.month == a,
#    'day':          lambda a,b: b and b.day == a,
}
"""
def autonegated_processor(processor):
    "decorator for processors; handles negation"
    @wraps(processor)
    def inner(name, value, data_processor, negated):
        cond = processor(na
        def condition(data):
            if name in data:
                value_in_data = data.get(name, None)
                matches = processor(value, value_in_data)
            else:
                matches = False
            return not matches if negated else matches
        return condition
    return inner
"""

for operation, processor in mapping.items():
    is_default = operation == DEFAULT_OPERATION
    #processor = autonegated_processor(processor)
    lookup_manager.register(operation, default=is_default)(processor)

