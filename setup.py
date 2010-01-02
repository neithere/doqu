#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#    Models is a framework for mapping Python classes to semi-structured data.
#    Copyright © 2009  Andrey Mikhaylenko
#
#    This file is part of Models.
#
#    Models is free software: you can redistribute it and/or modify
#    it under the terms of the GNU Lesser General Public License as published
#    by the Free Software Foundation, either version 3 of the License, or
#    (at your option) any later version.
#
#    Models is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU Lesser General Public License for more details.
#
#    You should have received a copy of the GNU Lesser General Public License
#    along with Models.  If not, see <http://gnu.org/licenses/>.


from setuptools import setup
import models


setup(
    # overview
    name             = 'models',
    description      = 'Python models for schema-less databases.',
    long_description = ("Models is a lightweight framework for mapping Python "
                        "classes to schema-less databases. It is not an ORM as "
                        "it doesn't map existing schemata to Python objects but "
                        "instead defines them on a higher layer built upon a "
                        "schema-less storage (key/value or document-oriented). "
                        "You define models as a valuable subset of the whole "
                        "database and work with only certain parts of "
                        "existing entities -- the parts you need."),

    # technical info
    version  = models.__version__,
    packages = ['models'],
    requires = ['python (>= 2.5)'],
    provides = ['models'],

    # copyright
    author   = 'Andrey Mikhaylenko',
    author_email = 'andy@neithere.net',
    license  = 'GNU Lesser General Public License (LGPL), Version 3',

    # more info
    url          = 'http://bitbucket.org/neithere/models/',
    download_url = 'http://bitbucket.org/neithere/models/src/',

    # categorization
    keywords     = ('query database api model models orm key/value '
                    'document-oriented non-relational'),
    classifiers  = [
        'Development Status :: 2 - Pre-Alpha',
        'Environment :: Plugins',
        'Intended Audience :: Developers',
        'Intended Audience :: Education',
        'Intended Audience :: Information Technology',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: GNU Library or Lesser General Public License (LGPL)',
        'Programming Language :: Python',
        'Topic :: Database',
        'Topic :: Database :: Database Engines/Servers',
        'Topic :: Database :: Front-Ends',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
)
