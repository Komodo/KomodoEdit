#!/usr/bin/env python

import ez_setup
ez_setup.use_setuptools()

from setuptools import setup, find_packages, Extension, Feature
from distutils.command.build_ext import build_ext
from distutils.errors import CCompilerError

VERSION = '1.7.1'
DESCRIPTION = "Simple, fast, extensible JSON encoder/decoder for Python"
LONG_DESCRIPTION = """
simplejson is a simple, fast, complete, correct and extensible
JSON <http://json.org> encoder and decoder for Python 2.3+.  It is
pure Python code with no dependencies, but includes an optional C
extension for a serious speed boost.

simplejson was formerly known as simple_json, but changed its name to
comply with PEP 8 module naming guidelines.

The encoder may be subclassed to provide serialization in any kind of
situation, without any special support by the objects to be serialized
(somewhat like pickle).

The decoder can handle incoming JSON strings of any specified encoding
(UTF-8 by default).
"""

CLASSIFIERS = filter(None, map(str.strip,
"""                 
Intended Audience :: Developers
License :: OSI Approved :: MIT License
Programming Language :: Python
Topic :: Software Development :: Libraries :: Python Modules
""".splitlines()))


BUILD_EXT_WARNING="""
WARNING: The C extension could not be compiled, speedups are not enabled.

Above is the output showing how the compilation failed.
"""

class ve_build_ext(build_ext):
    # This class allows C extension building to fail.
    def build_extension(self, ext):
        try:
            build_ext.build_extension(self, ext)
        except CCompilerError, x:
            print ('*'*70+'\n')
            print BUILD_EXT_WARNING
            print ('*'*70+'\n')

speedups = Feature(
    "options C speed-enhancement modules",
    standard=True,
    ext_modules = [
        Extension("simplejson._speedups", ["simplejson/_speedups.c"]),
    ],
)

setup(
    name="simplejson",
    version=VERSION,
    description=DESCRIPTION,
    long_description=LONG_DESCRIPTION,
    classifiers=CLASSIFIERS,
    author="Bob Ippolito",
    author_email="bob@redivi.com",
    url="http://undefined.org/python/#simplejson",
    license="MIT License",
    packages=find_packages(exclude=['ez_setup']),
    platforms=['any'],
    test_suite="nose.collector",
    zip_safe=True,
    entry_points={
        'paste.filter_app_factory': ['json = simplejson.jsonfilter:factory'],
    },
    features={'speedups': speedups},
    cmdclass={'build_ext': ve_build_ext},
)
