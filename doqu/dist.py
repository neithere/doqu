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
Distribution internals
======================

These are some distribution-related routines. It is doubtful that you would
ever need them unless you are developing Doqu itself.
"""
import pkg_resources


DEFAULT_GROUP = 'extensions'


def _get_entry_points(module_name, attr_name=None):
    """
    Returns an iterator on entry points for given module name and, optionally,
    attribute name.
    """
    group = DEFAULT_GROUP
    for entry_point in pkg_resources.iter_entry_points(group):
        if not entry_point.module_name == module_name:
            continue
        if attr_name and not attr_name in entry_point.attrs:
            continue
        yield entry_point

def check_dependencies(module_name, attr_name=None):
    """
    Checks module or attribute dependencies. Raises NameError if setup.py does
    not specify dependencies for given module or attribute.

    :param module_name:
        e.g. "doqu.ext.mongodb"
    :param attr_name:
        e.g. "bar" from "doqu.ext.foo:bar"

    """
    entry_points = list(_get_entry_points(module_name, attr_name))
    if not entry_points:
        msg = 'There are no entry points for module "{module_name}"'
        if attr_name:
            msg += 'and attribute "{attr_name}"'
        raise NameError(msg.format(**locals()))
    for entry_point in entry_points:
        entry_point.require()
