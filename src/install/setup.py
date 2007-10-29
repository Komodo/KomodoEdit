#!/usr/bin/env python
# ***** BEGIN LICENSE BLOCK *****
# Version: MPL 1.1/GPL 2.0/LGPL 2.1
# 
# The contents of this file are subject to the Mozilla Public License
# Version 1.1 (the "License"); you may not use this file except in
# compliance with the License. You may obtain a copy of the License at
# http://www.mozilla.org/MPL/
# 
# Software distributed under the License is distributed on an "AS IS"
# basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
# License for the specific language governing rights and limitations
# under the License.
# 
# The Original Code is Komodo code.
# 
# The Initial Developer of the Original Code is ActiveState Software Inc.
# Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
# ActiveState Software Inc. All Rights Reserved.
# 
# Contributor(s):
#   ActiveState Software Inc
# 
# Alternatively, the contents of this file may be used under the terms of
# either the GNU General Public License Version 2 or later (the "GPL"), or
# the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
# in which case the provisions of the GPL or the LGPL are applicable instead
# of those above. If you wish to allow use of your version of this file only
# under the terms of either the GPL or the LGPL, and not to allow others to
# use your version of this file under the terms of the MPL, indicate your
# decision by deleting the provisions above and replace them with the notice
# and other provisions required by the GPL or the LGPL. If you do not delete
# the provisions above, a recipient may use your version of this file under
# the terms of any one of the MPL, the GPL or the LGPL.
# 
# ***** END LICENSE BLOCK *****

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

