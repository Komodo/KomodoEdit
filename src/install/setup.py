#!/usr/bin/env python
# Copyright (c) 2003-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

# setup.py to build customactions.exe (and supporting files) with py2exe

import os, sys

from distutils.core import setup
import py2exe

#---- win32com.shell + py2exe love from MarkH
# ModuleFinder can't handle runtime changes to __path__, but win32com
# uses them, particularly for people who build from sources.  Hook this
# in.
try:
    #XXX The 'import modulefinder' is failing every time so I don't know
    #    what happened to get this to start working because I don't
    #    believe any longer that it was this block of code. The reason
    #    it was borken in installer builds is because of PYTHONPATH
    #    pollution, but not so when hacking this in a dev build.
    #    ???
    #from py2exe.tools import modulefinder
    import modulefinder
    import win32com
    for p in win32com.__path__[1:]:
        modulefinder.AddPackagePath("win32com", p)
    # Not sure why this works for "win32com.mapi" for not "win32com.shell"!
    for extra in ["win32com.shell"]:
        __import__(extra)
        m = sys.modules[extra]
        for p in m.__path__[1:]:
            modulefinder.AddPackagePath(extra, p)
except ImportError:
    # no build path setup, no worries.
    pass


setup(
    name="customactions",
    windows=["customactions.py"],
    data_files=[(os.curdir, ["w9xpopen.exe"])],
    #options={
    #    "py2exe": {
    #        "includes": ["encodings", "encodings.latin_1"],
    #    },
    #},
)

