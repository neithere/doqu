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
import tokyo.cabinet as tc

from docu.backend_base import LookupManager


__all__ = ['lookup_manager']


lookup_manager = LookupManager()


DEFAULT_OPERATION = 'equals'

# some operations are translated depending on value type
# so we extract this logic from the functions
str_or_num_operations = {
    'equals': (tc.TDBQCSTREQ, tc.TDBQCNUMEQ),
    'in': (tc.TDBQCSTROREQ, tc.TDBQCNUMOREQ),
}
def str_or_num(operation):
    str_op, num_op = str_or_num_operations[operation]
    def parse(k, v, p):
        # if value is iterable, peek at its first element
        test = v[0] if isinstance(v, (list, tuple)) else v
        op = num_op if isinstance(test, (int, float)) else str_op
        return k, op, p(v)
    return parse

str_or_list_operations = {
    'contains': (tc.TDBQCSTRAND, tc.TDBQCSTRINC),
    'like': (tc.TDBQCFTSPH, tc.TDBQCFTSAND),
}
def str_or_list(operation):
    str_op, list_op = str_or_list_operations[operation]
    def parse(k, v, p):
        op = list_op if isinstance(v, (list, tuple)) else str_op
        return k, op, p(v)
    return parse

mapping = {
    'between':      lambda k,v,p: (k, tc.TDBQCNUMBT, [int(p(x)) for x in v]),
    'contains':     str_or_list('contains'),
    'contains_any': lambda k,v,p: (k, tc.TDBQCSTROR, p(v)),
    'endswith':     lambda k,v,p: (k, tc.TDBQCSTREW, p(v)),
    'equals':       str_or_num('equals'),
    'exists':       lambda k,v,p: (k, tc.TDBQCSTRRX, ''),
    'gt':           lambda k,v,p: (k, tc.TDBQCNUMGT, p(v)),
    'gte':          lambda k,v,p: (k, tc.TDBQCNUMGE, p(v)),
    'in':           str_or_num('in'),
    'like':         str_or_list('like'),
    'like_any':     lambda k,v,p: (k, tc.TDBQCFTSOR, p(v)),
    'lt':           lambda k,v,p: (k, tc.TDBQCNUMLT, p(v)),
    'lte':          lambda k,v,p: (k, tc.TDBQCNUMLE, p(v)),
    'matches':      lambda k,v,p: (k, tc.TDBQCSTRRX, p(v)),
    'search':       lambda k,v,p: (k, tc.TDBQCFTSEX, p(v)),
    'startswith':   lambda k,v,p: (k, tc.TDBQCSTRBW, p(v)),
    'year':         lambda k,v,p: (k, tc.TDBQCSTRRX, '^%d....'%v),
    'month':        lambda k,v,p: (k, tc.TDBQCSTRRX, '^....%0.2d..'%v),
    'day':          lambda k,v,p: (k, tc.TDBQCSTRRX, '^......%0.2d'%v),
}
def smart_processor(processor):
    "decorator for processors; handles negation"
    @wraps(processor)
    def inner(k, v, p, n):
        k, o, v = processor(k, v, p)
        if n:
            o = o | tc.TDBQCNEGATE
        return k, o, v
    return inner

for operation, processor in mapping.items():
    default = operation == DEFAULT_OPERATION
    # handle negation automatically so processors don't care about it
    processor = smart_processor(processor)
    lookup_manager.register(operation, default=default)(processor)
