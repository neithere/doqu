#!/usr/bin/env python
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


import os
from setuptools import find_packages, setup

from _version import version


readme = open(os.path.join(os.path.dirname(__file__), 'README')).read()

setup(
    # overview
    name             = 'doqu',
    description      = 'Document-query: models for schema-less databases.',
    long_description = readme,

    # technical info
    version  = version,
    packages = find_packages(),
    requires = ['python (>= 2.6)'],
    provides = ['doqu'],
    obsoletes = ['pymodels', 'docu'],

    # optional features
    #   NOTE: if e.g. Sphinx or nosetests die because of endpoints, try:
    #   $ rm -rf doqu.egg-info
    #   $ pip install .
    extras_require = {
        'TC': ['tokyo-python>=0.6'],
        'TT': ['pyrant>=0.6.3'],
        'Shove': ['shove>=0.2.1'],
        'Mongo': ['pymongo>=1.7'],
        'WTForms': ['wtforms>=0.6.1dev'],  # 0.6 has bug in dateutil ext
    },
    entry_points = {
        'extensions': [
            'tc = doqu.ext.tokyo_cabinet [TC]',
            'tt = doqu.ext.tokyo_tyrant [TT]',
            'shove = doqu.ext.shove_db [Shove]',
            'mongo = doqu.ext.mongodb [Mongo]',
            'wtforms = doqu.ext.forms [WTForms]',
        ],
    },

    # copyright
    author   = 'Andrey Mikhaylenko',
    author_email = 'andy@neithere.net',
    license  = 'GNU Lesser General Public License (LGPL), Version 3',

    # more info
    url          = 'http://bitbucket.org/neithere/doqu/',
    download_url = 'http://bitbucket.org/neithere/doqu/src/',

    # categorization
    keywords     = ('document query database api model models orm key/value '
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

    # release sanity check
    test_suite = 'nose.collector',
)
