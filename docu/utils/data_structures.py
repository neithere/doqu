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

from collections import MutableMapping


__all__ = ['ProxyDict', 'DotDict', 'CachedIterator', 'LazySorted']


#---------------+
#  Collections  |
#---------------+


class ProxyDict(MutableMapping):
    """
    A dictionary-like wrapper for a real dictionary. Makes it easy to
    preprocess values on access.
    """
    def __contains__(self, key):
        return key in self._data

    def __delitem__(self, key):
        del self._data[key]

    def __getitem__(self, key):
        return self._data[key]
#        value = self._data[key]
#        return self._preprocess_get_value(key, value)

    def __init__(self, obj):
        self._data = obj

    def __iter__(self):
        return iter(self._data)

    def __len__(self):
        return len(self._data)

    def __repr__(self):
        return 'ControlledProxyDict(%s)' % repr(self._data)

    def __setitem__(self, key, value):
        #value = self._preprocess_set_value(key, value)
        self._data[key] = value

#    def _preprocess_get_value(self, key, value):
#        return value
#
#    def _preprocess_set_value(self, key, value):
#        return value


class DotDict(ProxyDict):
    """
    A dictionary-like object that provides access to its items via both
    traditional ``__getitem__`` and nested dot lookups. Usage::

        >>> foo = DotDict({'bar': {'baz': 'quux'}})
        >>> foo['bar']['baz']
        quux
        >>> foo.bar.baz
        quux

    Note that *new* dictionary keys can only be added via ``__setitem__``.
    However, existing keys can be changed also via ``__setattr__``.

    .. note: if a key starts with an underscore (``_``), it cannot be accessed
        via dot lookup due to security reasons.

    """

    def __contains__(self, key):
        return key in self._data

    #def _preprocess_item_value(self, key, value):
    #    if isinstance(value, (dict, DotDict)):
    #        return DotDict(value)
    #    else:
    #        return value

    def __getattr__(self, name):
        try:
            if name.startswith('_'):
                raise AttributeError
            return self[name]
        except (AttributeError, KeyError):
            raise AttributeError('%s object has not attribute "%s"'
                                 % (type(self).__name__, name))

    def __getitem__(self, key):
        value = super(DotDict, self).__getitem__(key)
        if isinstance(value, (dict, DotDict)):
            return DotDict(value)
        return value

    def __setattr__(self, key, value):
        try:
            # assuming our obj is a dictionary and it contains given key
            if key in self._data:
                self._data[key] = value
            else:
                raise AttributeError
        except AttributeError:
            # either obj is not a dictionary or it doesn't have that key
            super(DotDict, self).__setattr__(key, value)

    def __repr__(self):
        return 'DotDict(%s)' % repr(self._data)


# Some ideas/code for caching of results are taken from
#   django.db.models.query.QuerySet.
# The CachedIterator was initially created as a part of Datashaping.

ITER_CHUNK_SIZE = 100 # how many items to cache while iterating


class CachedIterator(object):

    def __init__(self, *args, **kw):
        self._iter  = kw.pop('iterable', None)
        self._chunk_size = kw.pop('chunk_size', ITER_CHUNK_SIZE)
        self._cache = []
        self._init(*args, **kw)

    def _init(self, *args, **kw):
        pass

    #------------------------+
    #  Python magic methods  |
    #------------------------+

    __repr__ = lambda self: str(self._to_list())
    __len__  = lambda self: len(self._to_list())

    def __iter__(self):
        if not self._cache:
            self._fill_cache()
        pos = 0
        while 1:
            upper = len(self._cache)
            # iterate over cache
            while pos < upper:
                yield self._cache[pos]
                pos += 1
            # cache exhausted
            if not self._iter:
                # iterable exhausted too
                raise StopIteration
            # refill cache
            self._fill_cache()

    def __getitem__(self, idx):
        # fill cache up to requested index
        upper = len(self._cache)
        if isinstance(idx, slice):
            assert upper <= slice.start
            # we don't fully support slices here, just fill the cache from the
            # possible minimum till the requested maximum
            max_elem = idx.stop
        else:
            max_elem = idx
        if upper <= max_elem:
            self._fill_cache(max_elem - upper + self._chunk_size)
        return self._cache[idx]

    def _prepare_item(self, item):
        """
        Prepares item just before returning it; can be useful in subclasses.
        """
        return item

    #-------------------+
    #  Private methods  |
    #-------------------+

    def _prepare(self):
        """
        Does not do anything here but can be useful in subclasses to prepare the
        iterable before first iteration, e.g. find intersection between sets, etc.
        """
        pass

    def _to_list(self):
        """
        Coerces the iterable to list, caches result and returns it.
        """
        self._prepare()
        self._cache = self._cache or [self._prepare_item(x) for x in self._iter]
        return self._cache

    def _fill_cache(self, num=None):
        """
        Fills the result cache with 'num' more entries (or until the results
        iterator is exhausted).
        """
        self._prepare()
        if self._iter:
            try:
                for i in range(num or self._chunk_size):
                    self._cache.append(self._prepare_item(self._iter.next()))
            except StopIteration:
                self._iter = None


class LazySorted(object):
    """
    A lazily sorted iterable. Usage::

        >>> items = ['b', 'a', 'c']
        >>> items2 = LazySorted(items)
        >>> list(items2)  # items were not sorted until now

    This class does not act as a true proxy, it just wraps an iterable and
    publishes its sorted version through the iteration API.

    The constructor mimics the signature of the built-in function
    :func:`sorted`.
    """
    def __init__(self, data, key=None, reverse=False):
        self._data = data
        self._sort_key = key
        self._reverse = reverse
        # cache:
        self._sorted_data = None

    def __iter__(self):
        if self._sorted_data is None:
            self._sorted_data = sorted(
                self._data,
                key=self._sort_key,
                reverse=self._reverse)
        return iter(self._sorted_data)
