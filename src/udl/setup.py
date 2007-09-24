#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.

"""Distutils setup script for luddite.py"""

import sys
import os
from distutils.core import setup


#---- support routines

def _getVersion():
    import luddite
    return luddite.__version__


#---- setup mainline

setup(name="luddite",
      version=_getVersion(),
      description="A tool for building Komodo UDL-based language extensions",
      author="ActiveState Komodo Team",
      author_email="komodo-feedback@ActiveState.com",
      url="http://www.activestate.com/Products/Komodo/",
      license="Komodo License",
      platforms=["Windows", "Linux", "Mac OS X"],
      long_description="""\
UDL (User-Defined Languages) is a system for building custom language
extensions for Komodo. Luddite (this package) is a tool for working with
UDL: compiling UDL resources, packaging bits into Komodo extensions.
""",
      keywords="udl komodo extension languages".split(),

      scripts=["luddite.py"],
      packages=["ludditelib"],
      package_dir={"ludditelib": "ludditelib"},
      package_data={"ludditelib": ["install.rdf.in"]},
     )

