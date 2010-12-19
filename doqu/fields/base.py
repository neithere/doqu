# python
import pickle
# doqu
from doqu import validators


class Field(object):
    """
    Representation of a document property. Syntax sugar for separate
    definitions of structure, validators, defaults and labels.

    Usage::

        class Book(Document):
            title = Field(unicode, required=True, default=u'Hi', label='Title')

    this is just another way to type::

        class Book(Document):
            structure = {
                'title': unicode
            }
            validators = {
                'title': [validators.Required()]
            }
            defaults = {
                'title': u'Hi'
            }
            labels = {
                'title': u'The Title'
            }

    Nice, eh? But be careful: the `title` definition in the first example
    barely fits its line. Multiple long definitions will turn your document
    class into an opaque mess of characters, while the semantically grouped
    definitions stay short and keep related things aligned together. "Semantic
    sugar" is sometimes pretty bitter, use it with care.

    Complex validators still need to be specified by hand in the relevant
    dictionary. This can be worked around by creating specialized field classes
    (e.g. `EmailField`) as it is done e.g. in Django.

    :param essential:
        if True, validator :class:`~doqu.validators.Exists` is added (i.e. the
        field may be empty but it must be present in the record).
    :param pickled:
        if True, the value is preprocessed with pickle's dumps/loads functions.
        This of course breaks lookups by this field but enables storing
        arbitrary Python objects.

    """
    def __init__(self, datatype, essential=False, required=False, default=None,
                 choices=None, label=None, pickled=False):
        self.choices = choices
        self.datatype = datatype
        self.essential = essential
        self.required = required
        self.default = default
        self.label = label
        self.pickled = pickled

    skip_type_conversion = False
    # These could be defined as no-op methods but we don't need to register
    # irrelevant stuff. See contribute_to_document_metadata().
    process_get_item = None
    process_set_item = None

    def process_incoming(self, value):
        if self.pickled:
            # it is important to keep initial value as bytes; e.g. TC will
            # return Unicode so we make sure pickle loader gets a str
            return pickle.loads(str(value)) if value else None
        else:
            return value

    def process_outgoing(self, value):
        return pickle.dumps(value) if self.pickled else value

    def contribute_to_document_metadata(self, doc_meta, attr_name):
        doc_meta.structure[attr_name] = self.datatype

        if self.default is not None:
            doc_meta.defaults[attr_name] = self.default

        if self.label is not None:
            doc_meta.labels[attr_name] = self.label

        # validation

        def _add_validator(validator_class, *args, **kwargs):
            validator = validator_class(*args, **kwargs)
            vs = doc_meta.validators.setdefault(attr_name, [])
            if not any(isinstance(x, validator_class) for x in vs):
                vs.append(validator)

        if self.essential:
            _add_validator(validators.Exists)

        if self.required:
            _add_validator(validators.Required)

        if self.choices:
            _add_validator(validators.AnyOf, list(self.choices))

        if self.skip_type_conversion or self.pickled:
            # not only automatic type conversion may damage pickled data, but
            # also the converter may break on unknown data type (while it can
            # be safely unpickled), so we just tell the backend to give us a
            # plain string
            if not attr_name in doc_meta.skip_type_conversion:
                doc_meta.skip_type_conversion.append(attr_name)

        # preprocessors (serialization, wrappers, etc.)
        for name in ['incoming', 'outgoing', 'get_item', 'set_item']:
            processor = getattr(self, 'process_{0}'.format(name))
            collection_name = '{0}_processors'.format(name)
            if processor:
                getattr(doc_meta, collection_name)[attr_name] = processor
            else:
                try:
                    del getattr(doc_meta, collection_name)[attr_name]
                except KeyError:
                    pass
