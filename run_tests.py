#!/usr/bin/python -O
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
import unittest
import doctest

TESTS_DIRS = ('tests', 'pymodels')

# A sandbox Tyrant instance parametres:
TYRANT_HOST = '127.0.0.1'
TYRANT_PORT = '1983'    # default is 1978 so we avoid clashes
TYRANT_FILE = os.path.abspath('test123.tct')   # NOTE: this file will be purged during testing!
TYRANT_PID  = os.path.abspath('test123.pid')


def _start_tyrant():
    assert not os.path.exists(TYRANT_FILE), 'Cannot proceed if test database already exists'
    cmd = 'ttserver -dmn -host %(host)s -port %(port)s -pid %(pid)s %(file)s'
    os.popen(cmd % {'host': TYRANT_HOST, 'port': TYRANT_PORT,
                    'pid': TYRANT_PID, 'file': TYRANT_FILE}).read()
    if __debug__:
        print '# sandbox Tyrant started with %s...' % TYRANT_FILE
        print

def _stop_tyrant():
    print # keep test suite results visible

    cmd = 'ps -e -o pid,command | grep "ttserver" | grep "\-port %s"' % TYRANT_PORT
    line = os.popen(cmd).read()
    try:
        pid = int(line.strip().split(' ')[0])
    except ValueError:
        'Expected "pid command" format, got %s' % line

    os.popen('kill %s' % pid)
    if __debug__:
        print '# sandbox Tyrant stopped.'

    os.unlink(TYRANT_FILE)
    if __debug__:
        print '# sandbox database %s deleted.' % TYRANT_FILE

def _test():
    _start_tyrant()

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

    _stop_tyrant()

if __name__ == '__main__':
    _test()
