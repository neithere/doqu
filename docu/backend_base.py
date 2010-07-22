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

"""
Backend API
===========

Abstract classes for unified storage/query API with various backends.

Derivative classes are expected to be either complete implementations or
wrappers for external libraries. The latter is assumed to be a better solution
as Docu is only one of the possible layers. It is always a good idea to
provide different levels of abstraction and let others combine them as needed.

The backends do not have to subclass :class:`BaseStorageAdapter` and
:class:`BaseQueryAdapter`. However, they must closely follow their API.
"""

import logging

from document_base import Document


__all__ = [
    'BaseStorageAdapter', 'BaseQueryAdapter',
    'ProcessorDoesNotExist',
    'LookupManager', 'LookupProcessorDoesNotExist',
    'ConverterManager', 'DataProcessorDoesNotExist',
]

#log = logging.getLogger()#__name__)


class BaseStorageAdapter(object):
    """
    Abstract adapter class for storage backends.
    """

    # these must be defined by the backend subclass
    supports_nested_data = False
    converter_manager = None
    lookup_manager = None

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    def __contains__(self, key):
        raise NotImplementedError

    def __init__(self, **kw):
        "Typical kwargs: host, port, name, user, password."
        self._connection_options = kw
        self.connection = None
        self.connect()

    def __iter__(self):
        raise NotImplementedError

    def __len__(self):
        raise NotImplementedError

    def __nonzero__(self):
        if self.connection is not None:
            return True

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _decorate(self, model, key, data):
        """
        Populates a model instance with given data and initializes its state
        object with current storage and given key.
        """

        if model.meta.structure:
            pythonized_data = {}

            # NOTE: nested definitions are not supported here.
            # if you fix this, please check the BaseStorage.supports_nested_data
            for name, type_ in model.meta.structure.iteritems():
                value = data.get(name, None)
                try:
                    # FIXME this should be added as a separate symmetric wrapper;
                    # serialization is currently done is document_base
                    if name in model.meta.serialized:
                        if value is not None:
                            deserializer = model.meta.serialized[name][1]
                            value = self.value_from_db(str, value)
                            value = deserializer(value)
                    else:
                        value = self.value_from_db(type_, value)
                except ValueError as e:
                    logging.warn('could not convert %s.%s (primary key %s): %s'
                                 % (model.__name__, name, repr(key), e))
                    # If incoming value could not be converted to desired data
                    # type, it is left as is (and will cause invalidation of the
                    # model on save). However, user can choose to raise ValueError
                    # immediately when such broken record it retrieved:
                    if model.meta.break_on_invalid_incoming_data:
                        raise
                pythonized_data[name] = value
        else:
            # if the structure is unknown, just populate the document as is
            pythonized_data = data.copy()
        instance = model(**pythonized_data)
        # FIXME access to private attribute; make it public?
        instance._saved_state.update(storage=self, key=key, data=data)
        return instance

    def _fetch(self, primary_key):
        """
        Returns a dictionary representing the record with given primary key.
        """
        raise NotImplementedError # pragma: nocover

    #--------------+
    #  Public API  |
    #--------------+

    def clear(self):
        """
        Clears the whole storage from data, resets autoincrement counters.
        """
        raise NotImplementedError # pragma: nocover

    def connect(self):
        """
        Connects to the database. Raises RuntimeError if the connection is not
        closed yet. Use :meth:`reconnect` to explicitly close the connection
        and open it again.
        """
        raise NotImplementedError

    def delete(self, key):
        """
        Deletes record with given primary key.
        """
        raise NotImplementedError # pragma: nocover

    def disconnect(self):
        """
        Closes internal store and removes the reference to it.
        """
        # typical implementation:
        #   self.connection.close()
        #   self.connection = None
        raise NotImplementedError # pragma: nocover

    def get(self, doc_class, primary_key):
        """
        Returns document instance for given document class and primary key.
        Raises KeyError if there is no item with given key in the database.
        """
        logging.debug('fetching record "%s"' % primary_key)
        data = self._fetch(primary_key)
        return self._decorate(doc_class, primary_key, data)

    def get_or_create(self, doc_class, **kwargs):
        """
        Queries the database for records associated with given document class
        and conforming to given extra condtions. If such records exist, picks
        the first one (the order may be random depending on the database). If
        there are no such records, creates one.

        Returns the document instance and a boolean value "created".
        """
        assert kwargs
        query = doc_class.objects(self).where(**kwargs)
        if query.count():
            return query[0], False
        else:
            obj = doc_class(**kwargs)
            obj.save(self)
            return obj, True

    def get_query(self):
        """
        Returns a Query object bound to this storage.
        """
        raise NotImplementedError # pragma: nocover

    def reconnect(self):
        """
        Gracefully closes current connection (if it's not broken) and connects
        again to the database (e.g. reopens the file).
        """
        self.disconnect()
        self.connect()

    def save(self, model, data, primary_key=None):
        """
        Saves given model instance into the storage. Returns
        primary key.

        :param model: model class
        :param data: dict containing all properties
            to be saved
        :param primary_key: the key for given object; if undefined, will be
            generated

        Note that you must provide current primary key for a model instance
        which is already in the database in order to update it instead of
        copying it.
        """
        raise NotImplementedError # pragma: nocover

    def value_from_db(self, datatype, value):
        assert self.converter_manager, 'backend must provide converter manager'
        return self.converter_manager.from_db(datatype, value)

    def value_to_db(self, value):
        assert self.converter_manager, 'backend must provide converter manager'
        return self.converter_manager.to_db(value, self)


class BaseQueryAdapter(object):
    """
    Query adapter for given backend.
    """

    #--------------------+
    #  Magic attributes  |
    #--------------------+

    def __getitem__(self, key):
        raise NotImplementedError # pragma: nocover

    def __init__(self, storage, model):
        self.storage = storage
        self.model = model
        self._init()

    def __iter__(self):
        raise NotImplementedError # pragma: nocover

    def __len__(self):
        return len(self[:])

    def __or__(self, other):
        raise NotImplementedError # pragma: nocover

    def __repr__(self):
        # we make extra DB hits here because query representation is mostly
        # used for interactive debug sessions or tests, so performance is
        # barely an issue in this case.
        MAX_ITEMS_IN_REPR = 10
        cnt = self.count()
        if MAX_ITEMS_IN_REPR < cnt:
            # assuming the query object supports slicing...
            return (str(list(self[:MAX_ITEMS_IN_REPR]))[:-1] + ' ... (other %d items '
                    'not displayed)]' % (cnt - MAX_ITEMS_IN_REPR))
        else:
            return str(list(self))

    def __sub__(self, other):
        raise NotImplementedError # pragma: nocover

    #----------------------+
    #  Private attributes  |
    #----------------------+

    def _get_native_conditions(self, conditions, negate=False):
        """
        Returns a generator for backend-specific conditions based on a
        dictionary of backend-agnostic ones.
        """
        for lookup, value in conditions.iteritems():
            if '__' in lookup:
                name, operation = lookup.split('__')    # XXX check if there are 2 parts
            else:
                name, operation = lookup, None
            processor = self.storage.lookup_manager.get_processor(operation)
            # lookup processor may (not) want to convert value to the
            # database-friendly format; we pass the appropriate function along
            # with the intact "pythonized" value
            def preprocessor(x):
                return self.storage.converter_manager.to_db(x, self.storage)
            native = processor(name, value, preprocessor, negate)

            # yield name/value pair(s)
            if hasattr(native, 'next') or isinstance(native, (list, tuple)):
                for x in native:
                    yield x
            else:
                yield native  #(name, value)

    def _init(self):
        pass

    #--------------+
    #  Public API  |
    #--------------+

    def count(self):
        """
        Returns the number of records that match given query. The result of
        `q.count()` is exactly equivalent to the result of `len(q)`. The
        implementation details do not differ by default, but it is recommended
        that the backends stick to the following convention:

        - `__len__` executes the query, retrieves all matching records and
          tests the length of the resulting list;
        - `count` executes a special query that only returns a single value:
          the number of matching records.

        Thus, `__len__` is more suitable when you are going to iterate the
        records anyway (and do no extra queries), while `count` is better when
        you just want to check if the records exist, or to only use a part of
        matching records (i.e. a slice).
        """
        return len(self)    # may be inefficient, override if possible

    def delete(self):
        """
        Deletes all records that match current query.
        """
        raise NotImplementedError # pragma: nocover

    def order_by(self, name):
        """
        Returns a query object with same conditions but with results sorted by
        given column.

        :param name: string: name of the column by which results should be
            sorted. If the name begins with a ``-``, results will come in
            reversed order.

        """
        raise NotImplementedError # pragma: nocover

    def values(self, name):
        """
        Returns a list of unique values for given column name.
        """
        raise NotImplementedError # pragma: nocover

    def where(self, **conditions):
        """
        Returns Query instance filtered by given conditions.
        The conditions are specified by backend's underlying API.
        """
        raise NotImplementedError # pragma: nocover

    def where_not(self, **conditions):
        """
        Returns Query instance. Inverted version of `where()`.
        """
        raise NotImplementedError # pragma: nocover


#--- PROCESSORS


class ProcessorDoesNotExist(Exception):
    """
    This exception is raised when given backend does not have a processor
    suitable for given value. Usually you will need to catch a subclass of this
    exception.
    """
    pass


class ProcessorManager(object):
    """
    Abstract manager of named functions or classes that process data.
    """
    exception_class = ProcessorDoesNotExist

    def __init__(self):
        self.processors = {}
        self.default = None

    def register(self, key, default=False):
        """
        Registers given processor class with given datatype. Decorator. Usage::

            converter_manager = ConverterManager()

            @converter_manager.register(bool)
            class BoolProcessor(object):
                def from_db(self, value):
                    return bool(value)
                ...

        Does not allow registering more than one processor per datatype. You
        must unregister existing processor first.
        """
        def _inner(processor):
            if key in self.processors:
                raise RuntimeError(
                    'Cannot register %s as processor for %s: %s is already '
                    'registered as such.'
                    % (processor, key, self.processors[key]))
            self._validate_processor(processor)
            self.processors[key] = processor
            if default:
                self.default = processor
            return processor
        return _inner

    def unregister(self, key):
        """
        Unregisters and returns a previously registered processor for given
        value or raises :class:`ProcessorDoesNotExist` is none was
        registered.
        """
        try:
            processor = self.processors[key]
        except KeyError:
            raise DataProcessorDoesNotExist
        else:
            del self.processors[key]
            return processor

    def get_processor(self, value):
        """
        Returns processor for given value.

        Raises :class:`DataProcessorDoesNotExist` if no suitable processor is
        defined by the backend.
        """
        key = self._preprocess_key(value)
        try:
            if key:
                return self.processors[key]
            else:
                if self.default:
                    return self.default
                raise KeyError
        except KeyError:
            raise DataProcessorDoesNotExist(
                'Backend does not define a processor for %s.' % repr(key))

    def _validate_processor(self, processor):
        "Returns `True` if given `processor` is acceptable."
        return True

    def _preprocess_key(self, key):
        return key


class LookupProcessorDoesNotExist(ProcessorDoesNotExist):
    """
    This exception is raised when given backend does not support the requested
    lookup.
    """
    pass


class LookupManager(ProcessorManager):
    """
    Usage::

        lookup_manager = LookupManager()

        @lookup_manager.register('equals', default=True)  # only one lookup can be default
        def exact_match(name, value):
            '''
            Returns native Tokyo Cabinet lookup triplets for given
            backend-agnostic lookup triplet.
            '''
            if isinstance(value, basestring):
                return (
                    (name, proto.RDBQCSTREQ, value),
                )
            if isinstance(value, (int, float)):
                return (
                    (name, proto.RDBQCNUMEQ, value),
                )
            raise ValueError

    Now if you call ``lookup_manager.resolve('age', 'equals', 99)``, the
    returned value will be ``(('age', proto.RDBCNUMEQ, 99),)``.

    A single generic lookup may yield multiple native lookups because some
    backends do not support certain lookups directly and therefore must
    translate them to a combination of elementary conditions. In most cases
    :meth:`~LookupManager.resolve` will yield a single condition. Its format is
    determined by the query adapter.
    """
    exception_class = LookupProcessorDoesNotExist

    # TODO: yield both abstract and native lookups. Abstract lookups will be
    # then parsed further until a set of all-native lookups is collected.
    # (beware: 1. endless recursion, and 2. possible logic trees)

    def resolve(self, name, operation, value):
        """
        Returns a set of backend-specific conditions for given backend-agnostic
        triplet, e.g.::

            ('age', 'gt', 90)

        will be translated by the Tokyo Cabinet backend to::

            ('age', 9, '90')

        or by the MongoDB backend to::

            {'age': {'$gt': 90}}

        """
        # TODO: provide example in docstring
        datatype = type(value)
        processor = self.get_processor(operation)
        return processor(name, value)


class DataProcessorDoesNotExist(ProcessorDoesNotExist):
    """
    This exception is raised when given backend does not have a datatype
    processor suitable for given value.
    """
    pass


class ConverterManager(ProcessorManager):
    """
    An instance of this class can manage property processors for given backend.
    Processor classes must be registered against Python types or classes. The
    processor manager allows encoding and decoding data between a model
    instance and a database record. Each backend supports only a certain subset
    of Python datatypes and has its own rules in regard to how `None` values
    are interpreted, how complex data structures are serialized and so on.
    Moreover, there's no way to guess how a custom class should be processed.
    Therefore, each combination of data type + backend has to be explicitly
    defined as a set of processing methods (to and from).
    """
    def _preprocess_key(self, value):
        if issubclass(value, Document):
            return Document
        return value

    def _validate_processor(self, processor):
        if hasattr(processor, 'from_db') and hasattr(processor, 'to_db'):
            return True
        raise AttributeError('Converter class %s must have methods "from_db" '
                             'and "to_db".' % processor)

    def from_db(self, datatype, value):
        """
        Converts given value to given Python datatype. The value must be
        correctly pre-encoded by the symmetrical :meth:`PropertyManager.to_db`
        method before saving it to the database.

        Raises :class:`DataProcessorDoesNotExist` if no suitable processor is
        defined by the backend.
        """
        if isinstance(datatype, basestring):
            # probably lazy import path, noop will do, model will take care
            return value

        p = self.get_processor(datatype)
        return p.from_db(value)

    def to_db(self, value, storage):
        """
        Prepares given value and returns it in a form ready for storing in the
        database.

        Raises :class:`DataProcessorDoesNotExist` if no suitable processor is
        defined by the backend.
        """

        # XXX references declared with lazy imports?

        datatype = type(value)
        p = self.get_processor(datatype)
        return p.to_db(value, storage)


