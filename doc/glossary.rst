Glossary
========

.. glossary::

    storage
        A place where data is stored. Provides a single namespace. Key/value
        stores can be represented with a single storage object, some other
        databases will require multiple storage objects (e.g. each "database"
        of CouchDB or each "collection" of MongoDB). Docu does not use nested
        namespaces because in document databases they mean nothing anyway.

        Doqu offers a uniform API for different databases by providing
        "storage adapters". See :doc:`backend_base` for technical details and
        :doc:`ext` for a list of adapters bundled with Docu.

    record
        A piece of data identified by an arbitrary unique primary key in a
        :term:`storage`. In key/value stores the body of the record will be
        called "value" (usually serialized to a string); in other databases it
        is called "document" (also serialized as JSON, BSON, etc.). To avoid
        confusion we call all these things "records". In Python the record is
        represented as a dictionary of :term:`fields <field>`.

    field
        A named property of a :term:`record` or :term:`document`. Records are
        actually containers for fields. There can be only one field with given
        name in the same record/document.

    document
        An dictionary with metadata. Can be associated with a :term:`record` in
        a :term:`storage`. The structure can be restricted by :term:`schema`.
        Optional :term:`validators <validator>` determine how should the
        document look before it can be saved into the storage, or what records
        can be associated with documents of given class. Special behaviour can
        abe added with methods of the Document subclass (see :doc:`document`).
        
        The simplest document is just a dictionary with some metadata. The
        metadata can be empty or contain information about where the document
        comes from, what does its :term:`record` look like, etc.

        A document without schema or validators is equal to its record. A
        document *with* schema is only equal to the record if they have the
        same sets of fields and these fields are valid (i.e. have correct data
        types and pass certain tests).
        
        As you see, there is a difference between documents and records but
        sometimes it's very subtle.

    schema
        A mapping of field names to Python data types. Prescribes the structure
        of a :term:`document`.

    validator
        Contains a certain test. When associated with a :term:`field` of a
        :term:`document`, determines whether given value is suitable for the
        field and, therefore, whether the document is valid in general. An
        invalid document cannot be saved to the :term:`storage`. A validator
        can also contribute to the :term:`document query`. See
        :doc:`validators` for details on how this works.

    document query
        A query that yields all :term:`records <record>` within given
        :term:`storage` that can be associated with certain :term:`document`. A
        document without :term:`validators <validator>` does not add any
        conditions to the query, i.e. yields *all* records whatever structure
        they have. Validators can require that some fields are present or pass
        certain tests.
