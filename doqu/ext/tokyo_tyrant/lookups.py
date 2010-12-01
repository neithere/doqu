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

import datetime

from managers import lookup_manager, converter_manager


DEFAULT_OPERATION = 'equals'
mapping = {
    'between':      lambda k,v,p,n: {'%s__between'%k: [int(p(x)) for x in v]},
    'contains':     lambda k,v,p,n: {'%s__contains'%k: v},
    'contains_any': lambda k,v,p,n: {'%s__contains_any'%k: v},
    'endswith':     lambda k,v,p,n: {'%s__endswith'%k: v},
    'equals':       lambda k,v,p,n: {k: p(v)},
    'exists':       lambda k,v,p,n: {'%s__matches'%k: ''},
    'gt':           lambda k,v,p,n: {'%s__gt'%k: p(v)},
    'gte':          lambda k,v,p,n: {'%s__gte'%k: p(v)},
    'in':           lambda k,v,p,n: {'%s__in'%k: v},
    'like':         lambda k,v,p,n: {'%s__like'%k: v},
    'like_any':     lambda k,v,p,n: {'%s__like_any'%k: v},
    'lt':           lambda k,v,p,n: {'%s__lt'%k: p(v)},
    'lte':          lambda k,v,p,n: {'%s__lte'%k: p(v)},
    'matches':      lambda k,v,p,n: {'%s__matches'%k: v},
    'search':       lambda k,v,p,n: {'%s__search'%k: v},
    'startswith':   lambda k,v,p,n: {'%s__startswith'%k: v},
    'year':         lambda k,v,p,n: {'%s__matches'%k: '^%d....'%v},
    'month':        lambda k,v,p,n: {'%s__matches'%k: '^....%0.2d..'%v},
    'day':          lambda k,v,p,n: {'%s__matches'%k: '^......%0.2d'%v},
}
for operation, processor in mapping.items():
    default = operation == DEFAULT_OPERATION
    lookup_manager.register(operation, default=default)(processor)
