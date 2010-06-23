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


lookup_manager = LookupManager()


DEFAULT_OPERATION = 'equals'

# we define operations as functions that expect
mapping = {
    'between':      lambda a,b: b is not None and a[0] <= b <= a[1],
    'contains':     lambda a,b: a in b,
    'contains_any': lambda a,b: b is not None and any(x in b for x in a),
    'endswith':     lambda a,b: b is not None and b.endswith(a),
    'equals':       lambda a,b: a.pk == b if hasattr(a, 'pk') else a == b,
    'exists':       lambda a,b: True,
    'gt':           lambda a,b: b is not None and a < b,
    'gte':          lambda a,b: b is not None and a <= b,
    'in':           lambda a,b: b in a,
#   'like':         lambda a,b: NotImplemented,
#   'like_any':     lambda a,b: NotImplemented,
    'lt':           lambda a,b: b is not None and b < a,
    'lte':          lambda a,b: b is not None and b <= a,
    'matches':      lambda a,b: re.search(a, b),   # XXX pre-compile?
#   'search':       lambda a,b: NotImplemented,
    'startswith':   lambda a,b: b and b.startswith(a),
    'year':         lambda a,b: b and b.year == a,
    'month':        lambda a,b: b and b.month == a,
    'day':          lambda a,b: b and b.day == a,

}
def autonegated_processor(processor):
    "decorator for processors; handles negation"
    @wraps(processor)
    def inner(name, value, data_processor, negated):
        def condition(data):
            if name in data:
                value_in_data = data_processor(data.get(name, None))
                matches = processor(value, value_in_data)
            else:
                matches = False
            return not matches if negated else matches
        return condition
    return inner

for operation, processor in mapping.items():
    is_default = operation == DEFAULT_OPERATION
    processor = autonegated_processor(processor)
    lookup_manager.register(operation, default=is_default)(processor)

