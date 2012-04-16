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

try:
    # Codeintel's specialized elementtree.
    import ciElementTree as ET
    from ciElementTree import Element, SubElement, ElementTree, parse
except ImportError:
    #import warnings
    #warnings.warn("Could not import ciElementTree", category="codeintel")
    try:
        # Python 2.5 or 2.6
        import xml.etree.cElementTree as ET
        from xml.etree.cElementTree import Element, SubElement, ElementTree, parse
    except ImportError:
        try:
            import cElementTree as ET
            from cElementTree import Element, SubElement, ElementTree, parse
        except ImportError:
            import ElementTree as ET
            from ElementTree import Element, SubElement, ElementTree, parse

major, minor = sys.version_info[:2]
lang = "Python"
if major >= 3:
    lang += str(major)

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
            'idlelib\.\.*', 'antigravity', 'turtledemo.*', 'tkinter.__main__',
            'unittest.__main__']

if sys.platform.startswith("linux"):
    skip_regexen += ["CDROM", "DLFCN", "TYPES"]

# Used to store the file path of modules.
module_paths = {}

_moduleNameCache = {}
def keep_module(mod):
    for regex in skip_regexen:
        if re.match(regex, mod):
            #print("skipping:", mod)
            return False

    if mod in _moduleNameCache: return False
    _moduleNameCache[mod] = True
    return True

CIX_VERSION = "2.0"
def tree_from_cix(cix):
    """Return a (ci)tree for the given CIX content.

    Raises pyexpat.ExpatError if the CIX content could not be parsed.
    """
    if sys.version_info[0] >= 3:
        cix = str(cix, "UTF-8")
    else:
        if isinstance(cix, unicode):
            cix = cix.encode("UTF-8", "xmlcharrefreplace")
    tree = ET.XML(cix)
    version = tree.get("version")
    if version == CIX_VERSION:
        return tree
    elif version == "0.1":
        from codeintel2.tree import tree_2_0_from_tree_0_1
        return tree_2_0_from_tree_0_1(tree)
    else:
        raise CodeIntelError("unknown CIX version: %r" % version)

def create_names_dict(elem):
    names_dict = {}
    for child in elem.getchildren():
        name = child.get('name')
        if name is not None:
            names_dict[child.get('name')] = child
    return names_dict

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
            print("SKIPPING: %r" % (path, ))
            continue

        print("EXPLORING %r" % (path, ))
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

print("Found %d modules" % len(module_names))

if sys.platform.startswith('win'):
    pywin32_module_names = list(filter(pywin32_filter, module_names))
    # Manually add certain win32 modules - bug 87357.
    pywin32_module_names += ["win32ui", "win32uiole", "dde"]
    print("Found %d PyWin32 modules" % len(pywin32_module_names))

module_names = list(filter(keep_module, module_names))

print("Kept %d modules" % len(module_names))

if sys.platform.startswith('win'):
    # Remove the pywin32 names from the default scan.
    module_names = list(set(module_names).difference(pywin32_module_names))

# update as neeeded
num_expected_modules = 390
if sys.platform.startswith("linux"):
    num_expected_modules = 370
assert len(module_names) > num_expected_modules

# Sort the module names.
if sys.version_info >= (2, 6):
    import operator
    module_names.sort(key=operator.methodcaller('lower')) # canonicalize the sort order
else:
    # Python 2.5 doesn't have "operator.methodcaller"
    def sort_cmp(a, b):
        return cmp(a.lower(), b.lower())
    module_names.sort(cmp=sort_cmp)

def apply_module_overrides(modname, modelem):
    assert modelem is not None
    helpername = os.path.join("helpers", modname + '_helper.py')
    namespace = {}
    if os.path.exists(helpername):
        sys.stderr.write("Found helper module: %r\n" % helpername)
        if major >= 3:
            exec(compile(open(helpername).read(), os.path.basename(helpername), 'exec'), namespace, namespace)
        else:
            execfile(helpername, namespace, namespace)

        childelems = create_names_dict(modelem)
        function_overrides = namespace.get('function_overrides')
        if function_overrides is not None:
            for name in function_overrides:
                override_elem = childelems[name]
                overrides = function_overrides[name]
                for setting, value in overrides.items():
                    if override_elem.get(setting) != value:
                        print("  overriding %s.%s %s attribute from %r to %r" % (modname, name, setting, override_elem.get(setting), value))
                        override_elem.set(setting, value)

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

    children1 = create_names_dict(elem1)
    children2 = create_names_dict(elem2)
    names1 = set(children1.keys())
    names2 = set(children2.keys())

    # Iterate over the shared children and merge these as well.
    for child_name in names1.intersection(names2):
        merge_cix_elements(children1[child_name], children2[child_name])
    # Iterate over the names only in elem2 and add these to elem1.
    for child_name in names2.difference(names1):
        child = children2[child_name]
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
        print("mod: %r" % (mod, ))
        print("root_file names")
        print([x.get("name") for x in root_file.getchildren()])
        print
        print("tree names")
        print([x.get("name") for x in tree.getchildren()])
        print
    lastname = mod.split(".")[-1]
    try:
        root_file_children = create_names_dict(root_file)
        tree_file_children = create_names_dict(tree_file)

        try:
            merge_cix_elements(root_file_children[mod],
                               tree_file_children[lastname],
                               appendChildrenAsPrivate=True)
        except KeyError:
            print("  %r not found in tree" % (mod, ))
            if not use_init_fallback:
                raise
            print("    trying '__init__'")
            # Try the "__init__" package name then.
            # http://bugs.activestate.com/show_bug.cgi?id=76056
            merge_cix_elements(root_file_children[mod],
                               tree_file_children["__init__"],
                               appendChildrenAsPrivate=True)
            print("      found it")

        # Need to re-apply module overrides, as the ciling gets priority from
        # the above merge, e.g. "string.split" method.
        apply_module_overrides(mod, root_file_children[mod])

    except KeyError:
        print("      *not found*")
        pass

_py_ci_executable = None
def get_py_ci_executable():
    global _py_ci_executable
    if _py_ci_executable is None:
        from glob import glob
        from os.path import abspath, dirname, join
        ci_dir = dirname(dirname(dirname(dirname(abspath(__file__)))))
        eggfiles = glob(join(ci_dir, "lib", "ciElementTree-*.egg-info"))
        if not eggfiles:
            raise RuntimeError("No ciElementTree .egg-info file found in %r" %
                               (join(ci_dir, "lib")))
        if len(eggfiles) > 1:
            raise RuntimeError("Too many ciElementTree .egg-info files in %r" %
                               (join(ci_dir, "lib")))
        wanted_version = re.match(".*-py(\d.\d).egg-info$", eggfiles[0]).group(1)
        import subprocess
        try:
            import which
        except ImportError:
            # Try adding support to the PYTHONPATH.
            sys.path.append(join(ci_dir, "support"))
            import which
        python_exe = "python"
        if sys.platform.startswith('win'):
            python_exe = "python.exe"
        for python_exe in which.whichall(python_exe):
            version = ""
            cwd = os.path.dirname(python_exe)
            argv = [python_exe, "-c", "import sys; sys.stdout.write(sys.version)"]
            p = subprocess.Popen(argv, cwd=cwd, stdout=subprocess.PIPE)
            stdout, stderr = p.communicate()
            if not p.returncode:
                # Some example output:
                #   2.0 (#8, Mar  7 2001, 16:04:37) [MSC 32 bit (Intel)]
                #   2.5.2 (r252:60911, Mar 27 2008, 17:57:18) [MSC v.1310 32 bit (Intel)]
                #   2.6rc2 (r26rc2:66504, Sep 26 2008, 15:20:44) [MSC v.1500 32 bit (Intel)]
                version_re = re.compile("^(\d+\.\d+)")
                if sys.version_info[0] >= 3:
                    stdout = str(stdout, "ascii")
                match = version_re.match(stdout)
                if match:
                    version = match.group(1)
            if version.startswith(wanted_version):
                _py_ci_executable = python_exe
                break
        if _py_ci_executable is None:
            raise RuntimeError("No Python %s executable found for ciling." %
                               (wanted_version, ))
    return _py_ci_executable

def get_pythoncile_cix_tree_for_path(mod_path):
    try:
        from codeintel2 import pythoncile
        # In process ciling.
        return pythoncile.scan_et(file(mod_path, "r").read(), mod_path)
    except (ImportError, SyntaxError):
        # Need to perform the ciling using a Python 2.6 interpreter.
        from os.path import abspath, dirname, join
        import subprocess
        ci_dir = dirname(dirname(dirname(dirname(abspath(__file__)))))
        ko_dir = dirname(dirname(ci_dir))
        ci2_path = join(ci_dir, "ci2.py")
        env = os.environ.copy()
        pypaths = [join(ci_dir, "lib"),
                   join(ci_dir, "support"),
                   join(ko_dir, "src", "python-sitelib"),
                   join(ko_dir, "src", "find"),
                   join(ko_dir, "util"),
                   join(ko_dir, "contrib", "smallstuff"),
                  ]
        env['PYTHONPATH'] = os.pathsep.join(pypaths)
        if sys.platform == "darwin":
            # Komodo only has 32-bit versions on the Mac.
            env['VERSIONER_PYTHON_PREFER_32_BIT'] = 'yes'

        if major < 3:
            # Convert env to strings (not unicode).
            encoding = sys.getfilesystemencoding()
            _enc_env = {}
            for key, value in env.items():
                try:
                    _enc_env[key.encode(encoding)] = value.encode(encoding)
                except UnicodeEncodeError:
                    # Could not encode it, warn we are dropping it.
                    log.warn("Could not encode environment variable %r "
                             "so removing it", key)
            env = _enc_env

        cmd = [get_py_ci_executable(), ci2_path, "scan", mod_path]
        p = subprocess.Popen(cmd, cwd=ci_dir, env=env, stdout=subprocess.PIPE)
        cix, stderr = p.communicate()
        tree = tree_from_cix(cix)
        return tree

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
                      lang=lang,
                      mtime=str(0),
                      path=os.path.basename(fname))

    print("Generating CIX Info: ")
    for mod in module_list:
        print(mod)
        sys.stdout.flush()
        try:
            # Introspect the module.
            gencix.docmodule(mod, cixfile, False)
            # Cile it as well, then merge the cile and introspect data. This
            # gives us additional information, including return type info,
            # docs strings, line numbers...
            mod_path = module_paths.get(mod)
            if mod_path and os.path.splitext(mod_path)[1] == ".py":
                # Need Python 2.6 to perform the cile.
                tree = get_pythoncile_cix_tree_for_path(mod_path)
                merge_module_scopes(mod, root, tree, use_init_fallback=
                                          (mod_path.endswith("__init__.py")),
                                    log=False)
        except Exception:
            import traceback
            print("\nEXCEPTION:", sys.exc_info()[1], "when processing", mod)
            traceback.print_exc()

    gencix.writeCixFileForElement(fname, root)

    print("done writing generic bits: %r." % fname)


fname = '../../../lib/codeintel2/stdlibs/%s-%d.%d.cix' % (lang.lower(), major, minor)
pywin32fname = '../../../lib/codeintel2/catalogs/pywin32.cix' 

# Remember the original cix, we'll merge with it after the current scan.
try:
    orig_root = parse(fname).getroot()
except (IOError, SyntaxError):
    # When the CIX file does not yet exist (new scan), create an empty root.
    orig_root = Element("codeintel", version="2.0")
    SubElement(orig_root, "file", lang=lang, mtime=str(0),
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
    cgi_elem_names = create_names_dict(cgi_elem)
    el = cgi_elem_names.get("parse")
    if el:
        el.set("signature", "parse(fp=None, environ=os.environ, keep_blank_values=0, strict_parsing=0)")

    el = cgi_elem_names.get("print_environ")
    if el:
        el.set("signature", "print_environ(environ=os.environ)")

    el = cgi_elem_names.get("test")
    if el:
        el.set("signature", "test(environ=os.environ)")

def fixup_platform_module(platform_elem):
    # Remove the filename location strings that get set in these function
    # signatures.
    #   http://bugs.activestate.com/show_bug.cgi?id=67610
    platform_elem_names = create_names_dict(platform_elem)
    el = platform_elem_names.get("architecture")
    if el:
        el.set("signature", "architecture(...)")

    el = platform_elem_names.get("libc_ver")
    if el:
        el.set("signature", "libc_ver(...)")

# Fixup the CIX for specific modules.
file_elem_from_name = create_names_dict(file_elem)
if "cgi" in file_elem_from_name:
    fixup_cgi_module(file_elem_from_name["cgi"])
if "platform" in file_elem_from_name:
    fixup_platform_module(file_elem_from_name["platform"])

# Update the citdl information.
gencix.perform_smart_analysis(main_root)

# Merge any existing CIX data with what we have just generated.
print("Merging old cix file with the new one...")
merge_trees(orig_root, main_root)

gencix.writeCixFileForElement(fname, orig_root)

print("Please run 'ci2 test python stdlib'\n")
