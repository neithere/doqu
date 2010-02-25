#!/usr/bin/env python
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


import os
from setuptools import find_packages, setup
import pymodels


readme = open(os.path.join(os.path.dirname(__file__), 'README')).read()

setup(
    # overview
    name             = 'pymodels',
    description      = 'Python models for schema-less databases.',
    long_description = readme,

    # technical info
    version  = pymodels.__version__,
    packages = find_packages(exclude=('tests',)),
    requires = ['python (>= 2.5)'],
    provides = ['pymodels'],

    # copyright
    author   = 'Andrey Mikhaylenko',
    author_email = 'andy@neithere.net',
    license  = 'GNU Lesser General Public License (LGPL), Version 3',

    # more info
    url          = 'http://bitbucket.org/neithere/pymodels/',
    download_url = 'http://bitbucket.org/neithere/pymodels/src/',

    # categorization
    keywords     = ('query database api model models orm key/value '
                    'document-oriented non-relational tokyo cabinet mongodb'),
    classifiers  = [
        'Development Status :: 4 - Beta',
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
