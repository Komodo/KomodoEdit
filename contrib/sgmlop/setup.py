#!/usr/bin/env python
#
# Setup script for sgmlop
# $Id$
#
# Usage: python setup.py install
#

from distutils.core import setup, Extension

setup(
    name="sgmlop",
    version="1.1.1-20040207",
    author="Fredrik Lundh",
    author_email="fredrik@pythonware.com",
    description="SGMLOP -- a small and fast SGML/XML parser",
    url="http://www.effbot.org/zone/sgmlop-index.htm",
    download_url="http://www.effbot.org/downloads#sgmlop",
    ext_modules = [
        Extension("sgmlop", ["sgmlop.c"])
        ]
    )
