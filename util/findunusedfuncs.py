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