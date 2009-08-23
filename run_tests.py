#!/usr/bin/python -O
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

import os
import unittest
import doctest

TESTS_DIRS = ('tests', 'models')

def _test():
    # collect files for testing
    def _add_files(test_files, dirname, fnames):
        for f in fnames:
            if f.endswith('.py') and not f.startswith('__'):
                test_files.append(os.path.join(dirname, f))
    files = []
    for directory in TESTS_DIRS:
        os.path.walk(directory, _add_files, files)

    # set up suite
    suite = unittest.TestSuite()
    for f in files:
        suite.addTest(doctest.DocFileSuite(f))
    runner = unittest.TextTestRunner()
    runner.run(suite)

if __name__ == '__main__':
    _test()
