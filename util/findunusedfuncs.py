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

from __future__ import generators

import re
import os

# Find JS functions which appear to never be called.

def findallfiles(dirname):
    """Generate all files in given directory or children thereof."""
    contents = os.listdir(dirname)
    for f in contents:
        fullpath = os.path.join(dirname, f)
        if os.path.isfile(fullpath):
            yield fullpath
        if os.path.isdir(fullpath):
            for subdirname in findallfiles(fullpath):
                yield subdirname


def find_files(basedir, pattern):
    files = []
    for file in findallfiles(basedir):
        if fnmatch.fnmatch(file, pattern):
            files.append(file)
    return files

file_contents = {}

jsfuncdef = re.compile("prototype.(\w\w*)\s*=\s*function\s*\(", re.MULTILINE)
function_definitions = {}

function_calls = {}

filenames = list(findallfiles('src/chrome/komodo/content'))
for file in filenames:
    file_contents[file] = open(file).read()

for filename, data in file_contents.items():
    funcs = jsfuncdef.findall(data)
    for func in funcs:
        if func in function_definitions:
            function_definitions[func].append(filename)
        else:
            function_definitions[func] = [filename]


for funcname in function_definitions.keys():
    # If it starts with is_cmd or do_, skip it
    if funcname.startswith('is_cmd_') or funcname.startswith('do_cmd_'): continue
    jsfunccall = re.compile(funcname + "\s*\(", re.MULTILINE)
    print 'looking for calls to', funcname, "found", 
    function_calls[funcname] = 0
    for filename, data in file_contents.items():
        calls = jsfunccall.findall(data)
        function_calls[funcname] += len(calls)
    print function_calls[funcname]


call_distribution = function_calls.items()
def sort_items(item1, item2):
    return -cmp(item1[1], item2[1])
call_distribution.sort(sort_items)
for function, hit in call_distribution:
    if hit == 0:
        print '%3d hits for %s (defined in %s)' % (hit, function, function_definitions[function])

#import pprint
#pprint.pprint(function_definitions)