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

"""
Generate Code-Intelligence XML (CIX) for the python standard library and
the common platform installed libraries.

Generation guide:
* Needs to be run on all three platforms (Windows, Linux and Mac).
* Run on Windows first, as this is the most commonly used platform,
  which will give the priority of CIX information to the Windows
  generated version.
1) Start off with a non-existant python-x.y.cix
2) Include the ci2 python libraries (ciElementTree and codeintel2) in your
   PYTHONPATH environment.
3) Run "genallcix.py". The version of python you run this script with determines the
   filename(s) that are used and generated.
4) After completion, copy the python-x.y.cix file to another platform,
   ensuring to copy across to the same directory location.
5) Repeat from step 2 for all platforms that have not yet run the genallcix
   script.
"""

## TODOs:
# * Figure out an Eggs strategy
# * Have a mechanism to override modules and elements, like the "re."
# Update citdl/returns expressions of the form "x.__dict__" to "dict".

import gencix, os, re, sys, time, string
from ciElementTree import Element, SubElement, ElementTree, parse
from codeintel2 import pythoncile
from codeintel2.tree import tree_from_cix

major, minor = sys.version_info[:2]
if sys.platform == 'win32':
    EXTENSIONS = [".py", ".pyd", ".dll"]
else:
    EXTENSIONS = [".py", ".so"]
    
# modules that we want to skip, usually because they have side effects
# or just because they're not seen as providing enough value for the size
# XXX: move the mac ones to a pymac.cix?
skip_regexen = ['test\.', '.*Mozilla', '__phello__',
            'bsddb\.test', 'encodings\..*', 'distutils\.tests', 'ctypes\.test',
            '_ctypes_test', 'this', 'xmllib', 'regex', 'regsub', 'macfs',
            'posixfile', 'statcache', 'tzparse', 'whrandom', 'bgenlocations',
            'aepack', 'aetypes', 'argvemulator', 'aetools', 'macerrors',
            'EasyDialogs', 'FrameWork', 'WASTEconst', '_testcapi',
            'appletrunner', 'appletrawmain', 'Audio_mac', 'MiniAEFrame',
            'PixMapWrapper', 'plat-mac\..*', 'lib-old\..*', 'Carbon',
            'CodeWarrior.*', 'Explorer.*', 'Finder.*', 'Netscape.*',
            'StdSuites.*', 'SystemEvents.*', 'Terminal.*', 'sqlite3\.test',
            'email\.test\.', '_AE', '_AH', '_App', '_CF', '_CG', '_CarbonEvt',
            '_Cm', '_Ctl', '_Dlg', '_Drag', '_Evt', '_File', '_Fm', '_Folder',
            '_Help', '_IBCarbon', '_Icn', '_Launch', '_List', '_Menu', '_Mlte',
            '_OSA', '_Qd', '_Qdoffs', '_Qt', '_Res', '_Scrap', '_Snd', '_TE',
            '_Win', '_codecs_cn', '_codecs_hk', '_codecs_iso2022', '_codecs_jp',
            '_codecs_kr', '_codecs_tw', '_LWPCookieJar', 'idlelib\.ToolTip',
            'idlelib\.\.*']

if sys.platform.startswith("linux"):
    skip_regexen += ["CDROM", "DLFCN", "TYPES"]

# Used to store the file path of modules.
module_paths = {}

_moduleNameCache = {}
def keep_module(mod):
    for regex in skip_regexen:
        if re.match(regex, mod):
            #print "skipping:", mod
            return False

    if mod in _moduleNameCache: return False
    _moduleNameCache[mod] = True
    return True

def pywin32_filter(mod):
    path = module_paths.get(mod)
    if path:
        path_split = os.path.normpath(path).split(os.sep)
        if "win32" in path_split or \
           "win32com" in path_split or \
           "win32comext" in path_split:
            return True
    return False


# builtins to start
module_names = ["*", "time", "sys", "gc", "operator", "cPickle", "marshal", "imp", "new",
    "struct", "cStringIO", "unicodedata", "math", "cmath", "_random",
    "array", "itertools", "strop", "datetime", "thread", "errno", "signal",
    "binascii", "_hotshot", "md5", "sha", "imp", "audioop",
    "os.path", "string", "re"]
# include platform builtins and special modules
ignore_modules = ["__main__", "xxsubtype"]
module_names = list(set(module_names).union(sys.builtin_module_names).difference(ignore_modules))

_already_processed_filepaths = {}
# find modules in standard library that aren't in site packages
def gen_modules():
    paths = sys.path[:]
    # go backwards so that e.g. the modules in lib-dynload aren't
    # thought of as "lib-dynload.foo" but as "foo"
    paths = [path for path in paths]
    paths.sort()
    paths.reverse()

    for path in paths:
        # filter out junk like '' and things in user's PYTHONPATH
        if not path.lower().startswith(sys.prefix.lower()): 
            print "SKIPPING", path
            continue

        print "EXPLORING", path
        for (dirpath, dirnames, filenames) in os.walk(path, True):
            dirnames[:] = [d for d in dirnames if d.lower() not in ('demo', 'demos', 'test', 'tests')]

            if ("win32" not in dirpath and "site-packages" in dirpath): continue
            for filename in filenames:
                extension = os.path.splitext(filename)[1]
                if extension in EXTENSIONS:
                    fullpath = os.path.join(dirpath, filename)
                    if fullpath in _already_processed_filepaths: continue # already dealt with it
                    _already_processed_filepaths[fullpath] = True
                    assert fullpath.startswith(path), (path, fullpath)
                    # get rid of early part of path
                    shortpath = fullpath[len(path)+1:]
                    # get rid of extension and convert slashes to dots
                    modpath = shortpath[:-len(extension)].replace(os.path.sep, '.')
                    if modpath.endswith('.__init__'):  # special case __init__.py
                        # XXX need to think about this for 2.5 changes?
                        modpath = modpath[:-len('.__init__')]
                    yield modpath, os.path.join(dirpath, filename)

for mod, path in gen_modules():
    module_names.append(mod)
    module_paths[mod] = path

if sys.version_info >= (2, 4):
    module_names.sort(key=string.lower) # canonicalize the sort order
else:
    # Necessary for earlier versions of python, before 2.4.
    def module_name_cmp(a, b):
        return cmp(a.lower, b.lower)
    module_names.sort(module_name_cmp)

print "Found %d modules" % len(module_names)

if sys.platform.startswith('win'):
    pywin32_module_names = (filter(pywin32_filter, module_names))
    print "Found %d PyWin32 modules" % len(pywin32_module_names)

module_names = filter(keep_module, module_names)

print "Kept %d modules" % len(module_names)

if sys.platform.startswith('win'):
    # Remove the pywin32 names from the default scan.
    module_names = list(set(module_names).difference(pywin32_module_names))

# update as neeeded
num_expected_modules = 390
if sys.version_info >= (2, 4):
    if sys.platform.startswith("linux"):
        num_expected_modules = 370
elif sys.version_info >= (2, 3):
    num_expected_modules = 350
assert len(module_names) > num_expected_modules

def merge_cix_elements(elem1, elem2, appendChildrenAsPrivate=False):
    """Merge additional details from elem2 into elem1"""
    # Add better docs if they exist.
    doc = elem2.get("doc")
    if doc is not None and elem1.get("doc") is None:
        elem1.set("doc", doc)

    # Add line numbers.
    line = elem2.get("line")
    if line is not None and elem1.get("line") is None:
        elem1.set("line", line)
    lineend = elem2.get("lineend")
    if lineend is not None and elem1.get("lineend") is None:
        elem1.set("lineend", lineend)

    # Add variable type information.
    if elem1.tag == "variable" and elem2.tag == "variable":
        citdl = elem2.get("citdl")
        if citdl is not None and elem1.get("citdl") is None:
            elem1.set("citdl", citdl)

    # Add function return type information
    citdl = elem2.get("returns")
    if citdl:
        elem1.set("returns", citdl)
    # Add function signature information
    signature = elem2.get("signature")
    if signature is not None and elem1.get("signature") is None:
        elem1.set("signature", signature)

    names1 = set(elem1.names.keys())
    names2 = set(elem2.names.keys())
    # Iterate over the shared children and merge these as well.
    for child_name in names1.intersection(names2):
        merge_cix_elements(elem1.names[child_name], elem2.names[child_name])
    # Iterate over the names only in elem2 and add these to elem1.
    for child_name in names2.difference(names1):
        child = elem2.names[child_name]
        if appendChildrenAsPrivate:
            attributes = child.get("attributes") or ""
            attr_split = attributes.split()
            if "__hidden__" not in attr_split:
                attr_split.append("__hidden__")
                child.set("attributes", " ".join(attr_split))
        elem2.remove(child)
        elem1.append(child)

def merge_module_scopes(mod, root, tree, use_init_fallback=False, log=False):
    # Find the right blob name to merge with.
    root_file = root.find("file")
    tree_file = tree.find("file")
    if log:
        print "mod: %r" % (mod, )
        print "root_file names"
        print root_file.names[mod]
        print
        print "tree names"
        print tree_file.names
        print
    lastname = mod.split(".")[-1]
    try:
        try:
            merge_cix_elements(root_file.names[mod], tree_file.names[lastname],
                               appendChildrenAsPrivate=True)
        except KeyError:
            print "%r not found in tree" % (mod, ),
            if not use_init_fallback:
                raise
            print ", trying '__init__'",
            # Try the "__init__" package name then.
            # http://bugs.activestate.com/show_bug.cgi?id=76056
            merge_cix_elements(root_file.names[mod], tree_file.names["__init__"],
                               appendChildrenAsPrivate=True)
            print ", found it"
    except KeyError:
        print ", *not found*"
        pass

def merge_trees(tree1, tree2):
    # Merge all the elements of tree2 into tree1.
    file_elem1 = tree1.find("file")
    file_elem2 = tree2.find("file")
    merge_cix_elements(file_elem1, file_elem2)

def process_module_list(module_list, fname, catalog_name=None,
                        catalog_description=None):
    root = Element("codeintel", version="2.0")
    if catalog_name:
        root.set("name", catalog_name)
    if catalog_description:
        root.set("description", catalog_description)
    cixfile = SubElement(root, "file",
                      lang="Python",
                      mtime=str(0),
                      path=os.path.basename(fname))

    print "Generating CIX Info: ",
    for mod in module_list:
        print mod
        sys.stdout.flush()
        try:
            # Introspect the module.
            gencix.docmodule(mod, cixfile, False)
            # Cile it as well, then merge the cile and introspect data. This
            # gives us additional information, including return type info,
            # docs strings, line numbers...
            mod_path = module_paths.get(mod)
            if mod_path and os.path.splitext(mod_path)[1] == ".py":
                cix = pythoncile.scan(file(mod_path, "r").read(), mod_path)
                tree = tree_from_cix(cix)
                merge_module_scopes(mod, root, tree, use_init_fallback=
                                          (mod_path.endswith("__init__.py")),
                                    log=False)
        except Exception, e:
            import traceback
            print "\nEXCEPTION:", e, "when processing", mod
            traceback.print_exc()

    gencix.writeCixFileForElement(fname, root)

    print 'Removing references to 0xF...'
    f = open(fname, 'rb')
    data = f.read()
    f.close()
    data = re.sub(r"&lt;(.*?) at 0x[0-9a-fA-F]+&gt;", "&lt;\\1&gt;", data)
    f = open(fname, 'wb')
    f.write(data)
    f.close()
    print "done writing generic bits: %r." % fname


fname = '../../../lib/codeintel2/stdlibs/python-%d.%d.cix' % (major, minor)
pywin32fname = '../../../lib/codeintel2/catalogs/pywin32.cix' 

# Remember the original cix, we'll merge with it after the current scan.
try:
    orig_root = parse(fname).getroot()
except (IOError, SyntaxError):
    # When the CIX file does not yet exist (new scan), create an empty root.
    orig_root = Element("codeintel", version="2.0")
    SubElement(orig_root, "file", lang="Python", mtime=str(0),
               path=os.path.basename(fname))

process_module_list(module_names, fname)

if sys.platform.startswith('win'):
    # Generate the windows specific bits into separate CIX files.
    process_module_list(pywin32_module_names, pywin32fname, 
                        catalog_name="PyWin32",
                        catalog_description="Python Extensions for Windows")

# Read in the just generated CIX.
main_root = parse(fname).getroot()
file_elem = main_root[0]

def fixup_cgi_module(cgi_elem):
    # Remove the environment strings that get set in these function signatures.
    #   http://bugs.activestate.com/show_bug.cgi?id=67610
    el = cgi_elem.names.get("parse")
    if el:
        el.set("signature", "parse(fp=None, environ=os.environ, keep_blank_values=0, strict_parsing=0)")

    el = cgi_elem.names.get("print_environ")
    if el:
        el.set("signature", "print_environ(environ=os.environ)")

    el = cgi_elem.names.get("test")
    if el:
        el.set("signature", "test(environ=os.environ)")

def fixup_platform_module(platform_elem):
    # Remove the filename location strings that get set in these function
    # signatures.
    #   http://bugs.activestate.com/show_bug.cgi?id=67610
    el = platform_elem.names.get("architecture")
    if el:
        el.set("signature", "architecture(...)")

    el = platform_elem.names.get("libc_ver")
    if el:
        el.set("signature", "libc_ver(...)")

# Fixup the CIX for specific modules.
if "cgi" in file_elem.names:
    fixup_cgi_module(file_elem.names["cgi"])
if "platform" in file_elem.names:
    fixup_platform_module(file_elem.names["platform"])

# Update the citdl information.
gencix.perform_smart_analysis(main_root)

# Merge any existing CIX data with what we have just generated.
print "Merging old cix file with the new one..."
merge_trees(orig_root, main_root)

gencix.writeCixFileForElement(fname, orig_root)

print "Please run 'ci2 test python stdlib'\n"
