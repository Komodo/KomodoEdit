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

"""support for Komodo test modules"""

import sys
from os.path import join, dirname, exists, abspath
from glob import glob

from testlib import TestError, TestSkipped, TestFailed
import platinfo



#---- public iface

__config_cache = None
def get_config():
    global __config_cache
    if __config_cache is None:
        bkconfig_py_path = join(dirname(dirname(abspath(__file__))),
                                "bkconfig.py")
        __config_cache = _module_from_path(bkconfig_py_path)
    return __config_cache

def get_prebuilt_dir(dir):
    ko_dir = dirname(dirname(abspath(__file__)))
    def prebuiltdir(plat):
        return join(ko_dir, "prebuilt", plat, "release")
    prebuilt_dirs_from_platname = {
        "linux-x86":      [prebuiltdir("linux-libcpp5"),
                           prebuiltdir("linux")],
        "macosx-x86":     [prebuiltdir("macosx-x86")],
        "macosx-powerpc": [prebuiltdir("darwin")],
        "win32-x86":      [prebuiltdir("win")],
        "solaris-sparc":  [prebuiltdir("solaris")],
    }
    platname = platinfo.platname()
    for base_dir in prebuilt_dirs_from_platname[platname]:
        full_path = join(base_dir, dir)
        if exists(full_path):
            return full_path
    else:
        raise TestError("could not find '%s' prebuilt dir for '%s'"
                        % (dir, platname))


def get_php_interpreter_path(ver):
    config = get_config()
    candidates = [
        join(config.phpsBaseDir, ver+"*"),
        join(config.phpsBaseDir, "php-%s*" % ver),
    ]
    for pattern in candidates:
        base_dirs = glob(pattern)
        if base_dirs:
            base_dir = base_dirs[0]
            break
    else:
        raise TestSkipped("could not find PHP %s for testing: '%s' don't "
                          "exist" % (ver, "', '".join(candidates)))
    if sys.platform == "win32":
        candidates = [
            join(base_dir, "php.exe"),
            join(base_dir, "Release_TS", "php.exe"),
        ]
        for candidate in candidates:
            if exists(candidate):
                return candidate
        else:
            raise TestSkipped("could not find PHP %s for testing: '%s' "
                              "don't exist"
                              % (ver, "', '".join(candidates)))
    else:
        return join(base_dir, "bin", "php")


# Recipe: indent (0.2.1)
def indent(s, width=4, skip_first_line=False):
    """indent(s, [width=4]) -> 's' indented by 'width' spaces

    The optional "skip_first_line" argument is a boolean (default False)
    indicating if the first line should NOT be indented.
    """
    lines = s.splitlines(1)
    indentstr = ' '*width
    if skip_first_line:
        return indentstr.join(lines)
    else:
        return indentstr + indentstr.join(lines)

# Recipe: dedent (0.1.2)
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines
    
        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG: 
        print "dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line)
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line: continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: print "dedent: indent=%d: %r" % (indent, line)
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG: print "dedent: margin=%r" % margin

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: print "dedent: %r: EOL -> strip up to EOL" % line
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print "dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin)
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
            else:
                if removed:
                    lines[i] = lines[i][removed:]
    return lines

def dedent(text, tabsize=8, skip_first_line=False):
    """dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)



#---- internal support stuff

# Recipe: module_from_path (1.0.1)
def _module_from_path(path):
    import imp, os
    dir = os.path.dirname(path) or os.curdir
    name = os.path.splitext(os.path.basename(path))[0]
    iinfo = imp.find_module(name, [dir])
    return imp.load_module(name, *iinfo)

