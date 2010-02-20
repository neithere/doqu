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

# Some ideas/code for caching of results are taken from django.db.models.query.QuerySet.
# This file was initially created as a part of Datashaping.


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
        if upper <= idx:
            self._fill_cache(idx - upper + self._chunk_size)
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
