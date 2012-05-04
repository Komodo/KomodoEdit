##############################################################################
#
# Copyright (c) 2006 Zope Corporation and Contributors.
# All Rights Reserved.
#
# This software is subject to the provisions of the Zope Public License,
# Version 2.1 (ZPL).  A copy of the ZPL should accompany this distribution.
# THIS SOFTWARE IS PROVIDED "AS IS" AND ANY AND ALL EXPRESS OR IMPLIED
# WARRANTIES ARE DISCLAIMED, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF TITLE, MERCHANTABILITY, AGAINST INFRINGEMENT, AND FITNESS
# FOR A PARTICULAR PURPOSE.
#
##############################################################################
# This package is developed by the Zope Toolkit project, documented here:
# http://docs.zope.org/zopetoolkit
# When developing and releasing this package, please follow the documented
# Zope Toolkit policies as described by this documentation.
##############################################################################
"""Setup for zope.cachedescriptors package

$Id$
"""
import os
#from setuptools import setup, find_packages
from distutils.core import setup

def read(*rnames):
    return open(os.path.join(os.path.dirname(__file__), *rnames)).read()

setup(
    name='zope.cachedescriptors',
    version='3.5.1',
    url='http://pypi.python.org/pypi/zope.cachedescriptors',
    author='Zope Corporation and Contributors',
    author_email='zope-dev@zope.org',
    license='ZPL 2.1',
    classifiers=[
        'Development Status :: 5 - Production/Stable',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: Zope Public License',
        'Programming Language :: Python',
        'Operating System :: OS Independent',
        'Topic :: Internet :: WWW/HTTP',
        'Topic :: Software Development',
        ],
    description='Method and property caching decorators',
    long_description=\
        '.. contents::\n\n' +
        read('src', 'zope', 'cachedescriptors', 'README.txt')
        + '\n' +
        read('src', 'zope', 'cachedescriptors', 'property.txt')
        + '\n' +
        read('src', 'zope', 'cachedescriptors', 'method.txt')
        + '\n' +
        read('CHANGES.txt'),

    packages=['zope', 'zope.cachedescriptors'],
    package_dir={'zope': 'src/zope',
                 'zope.cachedescriptor': 'src/zope/cachedescriptor'},
    )
