#!/usr/bin/env python
# Copyright (c) 2006 ActiveState Software Inc.

"""Distutils setup script for 'rst2html.py'."""

import sys
import os
import shutil
from distutils.core import setup

import rst2html


#---- setup mainline

setup(name="rst2html",
      version=rst2html.__version__,
      description="a quicky Python module/script for converting ReST to HTML",
      author="Trent Mick",
      author_email="trentm@activestate.com",
      platforms=["Windows", "Linux", "Mac OS X", "Unix"],
      long_description="""\
A quicky Python module/script for converting ReST markup to HTML.
Requires the docutils package.

Usage:
    python -m rst2html -b foo.txt
""",
      keywords=["ReST", "reStructuredText", "HTML", "markup"],

      py_modules=["rst2html"],
     )

