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
#
# Contributers (aka Blame):
# - Todd Whiteman
# - Trent Mick
#

"""Generate an API Catalog for the Komodo JavaScript API.

Processes the built Komodo JavaScript files to produce "komodo.cix".
"""

import os
from os.path import dirname, join, abspath, exists, normpath
import sys
from optparse import OptionParser
import logging

sys.path.insert(0, normpath(join(
    dirname(abspath(__file__)), "..", "..", "..", "..", "lib")))
from codeintel2.manager import Manager
from codeintel2.lang_javascript import JavaScriptCiler
from codeintel2.tree import tree_2_0_from_tree_0_1
from codeintel2.gencix_utils import *
del sys.path[0]


class Error(Exception):
    pass



#---- globals

log = logging.getLogger("komodo_to_cix")
log.setLevel(logging.INFO)
#log.setLevel(logging.DEBUG)

#TODO: the Komodo JS API should define a version somewhere
komodo_js_api_version = "0.2"



#---- internal support routines

# Recipe: paths_from_path_patterns (0.3.6)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            log.debug("exclude `%s' (matches no includes)", path)
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def _paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=[], excludes=[],
                              on_error=_NOT_SPECIFIED):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback
    """
    from os.path import basename, exists, isdir, join
    from glob import glob

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            paths = exists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if isdir(path):
                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in os.walk(path):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path


def _gen_komodo_js_api_files(javascript_dirlist):
    for path in _paths_from_path_patterns(javascript_dirlist,
                                          includes=["*.js"],
                                          excludes=["test"]):
        if path.lower().endswith(".unprocessed.js") \
           or path.lower().endswith(".p.js"):
            continue
        yield path

def _filter_namespaces(tree, keep_namespaces=None):
    for scope in list(tree.findall("file/scope")):
        for child in list(scope):
            name = child.get("name")
            if name and (not keep_namespaces or name not in keep_namespaces):
                #print "Removing: %r:%s" % (child.tag, name)
                scope.remove(child)

def _remove_private_elements(tree):
    parent_map = dict((c, p) for p in tree.getiterator() for c in p)
    for node in list(tree.getiterator()):
        attributes = node.get("attributes")
        if attributes and "private" in attributes.split(" "):
            # Remove it
            parentnode = parent_map.get(node)
            if parentnode is not None:
                parentnode.remove(node)


def _update_cix_file(path, content, p4_edit=False):
    if exists(path):
        existing_content = open(path, 'r').read()
        if existing_content == content:
            return
    if p4_edit:
        os.system('p4 edit "%s"' % path)
    open(path, "w").write(content)
    print "`%s' updated" % path

def _get_komodo_dev_dir():
    komodo_dev_dir = dirname(       # Komodo-devel/
                      dirname(      #  src/
                       dirname(     #   codeintel/
                        dirname(    #    support/
                         dirname(   #     gencix/
                          dirname(  #      javascript/
                           dirname( #       komodo_to_cix.py
                            abspath(__file__))))))))
    candidates = [
        komodo_dev_dir,
        dirname(komodo_dev_dir), # in a Komodo bk build
    ]
    for candidate in candidates:
        if exists(join(candidate, "Blackfile.py")):
            return candidate
    else:
        raise Error("non of the following look like the base Komodo src "
                    "dir: '%s'" % "', '".join(candidates))



#---- main module functionality

def komodo_to_cix(output_path, p4_edit=False):
    print "komodo_to_cix `%s'" % output_path
    
    cix_komodo = createCixRoot(name="Komodo",
        description="Komodo JavaScript API - version %s" % komodo_js_api_version)
    #cix_yui_file = createCixFile(cix_yui, "yui", lang="JavaScript")
    #cix_yui_module = createCixModule(cix_yui_file, "*", lang="JavaScript")

    # We use one JavaScript ciler instance for all the files we scan. This is
    # so we can record all variable/function/etc... information into one
    # komodo.cix file.
    mgr = Manager()
    jscile = JavaScriptCiler(mgr, "komodo")
    xtk_chrome_dir = join(_get_komodo_dev_dir(), "src", "chrome", "xtk",
                          "content")
    komodo_chrome_dir = join(_get_komodo_dev_dir(), "build", "release",
                             "chrome", "komodo", "content")
    for path in _gen_komodo_js_api_files([xtk_chrome_dir, komodo_chrome_dir]):
        #if path in ("utilities.js", "yahoo-dom-event.js"):
        #    # This is just a compressed up version of multiple files
        #    continue
        log.info("scanning `%s'" % path)
        try:
            # Slight hack to ensure the current filename stays correct for
            # cile logging.
            jscile.cile.name = path
            jscile.scan_puretext(file(path).read(), updateAllScopeNames=False)
        except Exception, e:
            # Report the file that had problems scanning.
            print "komodo_to_cix:: failed, exception scanning: %r, " \
                  "near line: %r" % (path, jscile.lineno)
            raise
    # Restore the filename before converting to CIX.
    jscile.cile.name = "komodo"
    jscile.cile.updateAllScopeNames()
    jscile.convertToElementTreeFile(cix_komodo, "JavaScript")

    #mergeElementTreeScopes(cix_yui_module)
    #remove_cix_line_numbers_from_tree(cix_komodo)
    _filter_namespaces(cix_komodo, keep_namespaces=["ko", "xtk"])
    # Don't remove the private elements, they are needed for codeintel. See:
    #   http://bugs.activestate.com/show_bug.cgi?id=72562
    #_remove_private_elements(cix_komodo)

    # Write out the tree
    _update_cix_file(output_path, get_cix_string(cix_komodo), p4_edit)

    # Finalize the codeintel manager.
    print "Finalizing the codeintel manager."
    mgr.finalize()

#---- mainline

def _prepare_xpcom():
    # If we are running with XPCOM available, some parts of the
    # codeintel system will *use* it to look for bits in extension dirs.
    # To do so some nsIDirectoryServiceProvider needs to provide the
    # "XREExtDL" list -- it isn't otherwise provided unless XRE_main()
    # is called.
    #
    # The Komodo test system provides a component for this.
    from codeintel2.common import _xpcom_
    if _xpcom_:
        from xpcom import components
        koTestSvc = components.classes["@activestate.com/koTestService;1"] \
            .getService(components.interfaces.koITestService)
        koTestSvc.init()

def main(argv):
    logging.basicConfig()

    parser = OptionParser(prog="komodo_to_cix", description=__doc__)
    parser.add_option("-e", "--p4-edit", action="store_true",
        help="'p4 edit' this file, if necessary")
    parser.add_option("-o", "--output-path",
        help="path to which to write CIX (defaults to 'komodo.cix')")
    parser.set_defaults(output_path="komodo.cix")
    opts, args = parser.parse_args()
    _prepare_xpcom()
    komodo_to_cix(opts.output_path, opts.p4_edit)

if __name__ == '__main__':
    sys.exit( main(sys.argv) )
