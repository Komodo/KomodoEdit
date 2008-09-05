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

# gencix.py: create a CIX file from introspection of a Python module or package.

# TODO:
#  - properties & slots?  (how frequent in binary modules??)
#  - go through std library looking for .so's to test this on.

import optparse
import inspect
import types
import pydoc
from ciElementTree import Element, SubElement, ElementTree
import sys, time, os, __builtin__
from pydoc import visiblename, classname, _split_list, isdata, ispackage, getdoc
import sys
import re
from parsedocs import parseDocSummary, parsePyFuncDoc
import logging

log = logging.getLogger("stdcix")

_gPyModelineOrHashBangPat = re.compile(r"^#(\s+\-\*\-\s+.*\s+-\*-)|(!.*)$")

try:
    sorted = sorted
except NameError:
    # Basic sorted implementation for python < 2.4
    def sorted(items, cmp=None):
        result = list(items)
        result.sort(cmp)
        return result

# Add .text and .tail values to an Element tree to make the output
# pretty. (Only have to avoid "doc" tags: they are the only ones with
# text content.)
def prettify(elem, level=0, indent='  ', youngestsibling=0):
    if elem and elem.tag != "doc":
        elem.text = '\n' + (indent*(level+1))
    for i in range(len(elem)):
        prettify(elem[i], level+1, indent, i==len(elem)-1)
    elem.tail = '\n' + (indent*(level-youngestsibling))

_gPyNamesFromCitdl = {
    'bool':         'bool',
    'true':         'bool',
    'false':        'bool',
    'buffer':       'buffer',
    'classobj':     None,
    'code':         'code',
    'complex':      'complex',
    'dict':         'dict',
    'dictionary':   'dict',
    'dictproxy':    'dictproxy',
    'ellipsis':     'ellipsis',
    'file':         'file',
    'float':        'float',
    'frame':        'frame',
    'generator':    'generator',
    'instance':     None,
    'int':          'int',
    'integer':      'int',
    'number':       'int',
    'list':         'list',
    'long':         'long',
    'function':     'function',
    'instancemethod': 'function',
    'module':       'module',
    'none':         None,
    'object':       'object',
    'slice':        'slice',
    'str':          'str',
    'string':       'str',
    'char':         'str',
    'character':    'str',
    'traceback':    'traceback',
    'tuple':        'tuple',
    'type':         'type',
    'unicode':      'unicode',
    'xrange':       'xrange',
}

# Perform some cleanup and type inferencing.
def improve_citdl_expression(citdl):
    """Returns a tuple (found_an_improvement, improved_citdl)"""
    if citdl.endswith(".__dict__"):
        return (True, "dict")
    if citdl.startswith("__builtins__."):
        return (True, citdl[len("__builtins__."):])
    return (False, citdl)

_gPyCitdlFromSignature = re.compile(r'^(.*)\s+->\s+((a|the|returns)\s+)?(.*)$')

# Improve the code intelligence data where possible.
def perform_smart_analysis(elem):
    citdl = elem.get("citdl")
    if citdl:
        improved, citdl = improve_citdl_expression(citdl)
        if improved:
            #print "Improved citdl %s %-10r (%r => %r)" % (
            #        elem.get("ilk") or elem.tag, elem.get("name"),
            #        elem.get("citdl"), citdl)
            elem.set("citdl", citdl)
    if elem.tag == "scope" and elem.get("ilk") == "function":
        # We got a function, examine the returns, see if we can make it
        citdl = elem.get("returns")
        if citdl:
            improved, citdl = improve_citdl_expression(citdl)
            if improved:
                #print "Improved citdl %s %-10r (%r => %r)" % (
                #        elem.get("ilk") or elem.tag, elem.get("name"),
                #        elem.get("returns"), citdl)
                elem.set("returns", citdl)
        else:
            signature = elem.get("signature")
            if signature:
                match = _gPyCitdlFromSignature.match(signature)
                if match:
                    leftover = match.group(4)
                    sp = leftover.split(None, 1)
                    citdl = _gPyNamesFromCitdl.get(sp[0].lower())
                    if citdl:
                        #print "Returns from signature for func %r => %r (%s)" % (
                        #        elem.get("name"), sp[0], leftover)
                        elem.set("returns", citdl)
                    #else:
                    #    print "unknown return type: %r (%r)" % (sp[0], leftover)
    for child in elem:
        perform_smart_analysis(child)

def getsdoc(obj):
    "like pydoc's getdoc, but shorter docs"
    doc = getdoc(obj)
    doclines = doc.split('\n')
    # Skip over python specific comments.
    index = 0
    while index < len(doclines):
        if not _gPyModelineOrHashBangPat.match(doclines[index]):
            break
        index += 1
    #doclines = parseDocSummary(doclines)
    doc = '\n'.join(doclines[index:index+3])
    return doc

def process_class_using_instance(rootElt, obj, name, callables):
    doc = getsdoc(obj) or None
    classElt = SubElement(rootElt, "scope", ilk="class", name=name)
    if doc: classElt.set('doc', doc)
    callables[name] = classElt
    classElt.set('attributes', '__hidden__')

    attrs = filter(lambda (name, value): visiblename(name),
               inspect.getmembers(obj, inspect.isbuiltin))
    for (key, value) in attrs:
        process_routine(classElt, value, key, callables)

    
def process_class(rootElt, obj, name, callables, __hidden__=False):
    doc = getsdoc(obj) or None
    classElt = SubElement(rootElt, "scope", ilk="class", name=name)
    if doc: classElt.set('doc', doc)
    callables[name] = classElt
    if __hidden__:
        classElt.set('attributes', '__hidden__')
    classrefs = [base.__name__ for base in obj.__bases__]
    if classrefs:
        classElt.set('classrefs', ' '.join(classrefs))
    # Functions are method descriptors in Python inspect module parlance.
    def attrfilter(attr):
        # Only add methods and attributes of the class to the CIX.
        # - "os._Environ" seems to be a particular problem case in that
        #   some methods defined on it are inspect.ismethod() but not
        #   inspect.ismethoddescriptor(). Not so for other examples in
        #   modules that stdcix.py processes, and adding .ismethod() to this
        #   filter adds unwanted methods on C-defined module exception
        #   classes.
        if not (inspect.isdatadescriptor(attr)
                or inspect.ismethoddescriptor(attr)
                or inspect.ismethod(attr) or
                inspect.isfunction(attr)):
            return False
        # Skip inherited attributes in the CIX.
        try:
            attrname = attr.__name__
            for base in obj.__bases__:
                if hasattr(base, attrname) and getattr(base, attrname) is \
                    getattr(obj, attrname):
                    return False
        except AttributeError:
            # staticmethod and classmethod objects don't have a __name__
            pass
            #print "Couldn't process: %r, assuming ok" % str(attr)
        return True

    #attrs = inspect.getmembers(object, attrfilter) # should I be using getmembers or class attr's?
    attrs = filter(lambda (name, value): attrfilter(value),
               [(name, getattr(obj, name)) for name in obj.__dict__])
    for (key, value) in attrs:
        if inspect.isfunction(value) or inspect.ismethod(value) or inspect.ismethoddescriptor(value):
            process_routine(classElt, value, key, callables)

def process_module(rootElt, obj, name, callables, modname, __hidden__=False):
    if (modname, name) in module_import_hacks:
        import_defn = module_import_hacks[(modname, name)]
        moduleElt = SubElement(rootElt, "import", **import_defn)
    else:
        moduleElt = SubElement(rootElt, "import", module=name)

def process_routine(rootElt, obj, name, callables):    
    if inspect.isfunction(obj):
        args, varargs, varkw, defaults = inspect.getargspec(obj)
        argspec = inspect.formatargspec(
            args, varargs, varkw, defaults)
        sig = name+argspec
    else:
        sig = ''
    doc = getdoc(obj) or None
    call_sig_lines, description_lines = parsePyFuncDoc(doc, [sig])
    if description_lines:
        doc = '\n'.join(parseDocSummary(description_lines))
    if call_sig_lines:
        signature = '\n'.join(call_sig_lines)
    else:
        signature = sig
    if name == '__init__':
        if doc == obj.__init__.__doc__:
            doc = None
        if signature == obj.__init__.__doc__:
            signature = None
    
    funcElt = SubElement(rootElt, "scope", ilk="function", name=name)
    if doc: funcElt.set('doc', doc)
    if signature: funcElt.set('signature', signature)

    callables[name] = funcElt

module_replacements = {
    "os.path": {"__doc__": "Common pathname manipulations."},
}
module_import_hacks = {
    # Hook up the "path" module in "os" to our special "os.path" static CIX
    # definition.
    ("os", "path"): {"module": "os.path", "line": "1", "alias": "path"}
}

module_skips = {
    '*': ["_", "__name__", "__doc__", "__debug__", "exit", "copyright",
          "license"],
}

def docmodule(modname, root, force=False, usefile=False):
    name = modname
    modulename = modname
    if modname == '*':
        modname = '__builtin__'
    try:
        obj, modulename = pydoc.resolve(modname)
    except Exception, e:
        print e
        return

    result = ''
    try:
        all = obj.__all__
    except AttributeError:
        all = None

    try:
        filename = inspect.getabsfile(obj)
    except TypeError:
        filename = '(built-in)'
    if usefile:
        cixfile = SubElement(root, "file",
                             lang="Python",
                             mtime=str(int(time.time())),
                             path=os.path.basename(filename))
    else:
        cixfile = root
    module = obj
    doc = getsdoc(obj) or None
    moduleElt = SubElement(cixfile, "scope", ilk="blob", name=name, lang="Python")
    if doc: moduleElt.set('doc', doc)
    skips = module_skips.get(name, [])
    callables = {}
    for key, value in sorted(inspect.getmembers(obj)):
        if key in skips:
            continue
        if inspect.ismodule(value):
            process_module(moduleElt, value, key, callables, modname)
            continue
        if not visiblename(key): # forget about __all__ 
            continue
        if (inspect.isfunction(value) or
            inspect.ismethod(value) or
            inspect.ismethoddescriptor(value) or
            inspect.isroutine(value) or
            inspect.isbuiltin(value)):
            process_routine(moduleElt, value, key, callables)
        elif inspect.isclass(value) or isinstance(value, types.TypeType):
            process_class(moduleElt, value, key, callables)
        elif isinstance(value, types.InstanceType):
            klass = value.__class__
            if klass.__module__ == name:
                t = klass.__name__
            else:
                t = "%s.%s" % (klass.__module__, klass.__name__)
            varElt = SubElement(moduleElt, "variable", name=key, citdl=t)
            # make sure we also process the type of instances
            process_class(moduleElt, klass, klass.__name__, callables)
        elif isdata(value):
            varElt = SubElement(moduleElt, "variable", name=key, citdl=type(value).__name__)
        else:
            log.warn("unexpected element in module '%s': '%s' is %r",
                     modulename, name, type(value))

    helpername = os.path.join("helpers", modname + '_helper.py')
    namespace = {}
    if os.path.exists(helpername):
        print >> sys.stderr, "Found helper module: %r" % helpername
        execfile(helpername, namespace, namespace)
        # look in helpername for analyze_retval_exprs, which is a list of (callable_string, *args)
        # and which corresponds to callables which when called w/ the specified args, will return
        # variables which should be used to specify the <return> subelement of the callable.
        analyze_retval_exprs = namespace.get('analyze_retval_exprs', [])
        signatures = namespace.get('signatures', {})
        for retval_expr in analyze_retval_exprs:
            name, args = retval_expr
            if name in callables:
                callableElt = callables[name]
                if name in signatures:
                    sig = signatures[name]
                    callableElt.set('signature', sig) # XXX???
                playarea = module.__dict__
                var = eval(name, playarea)(*args)
                # find out what type that is
                callableElt.set("returns", type(var).__name__)
            else:
                print "Don't know about: %r" % expr
        hidden_classes_exprs = namespace.get('hidden_classes_exprs', [])
        for expr in hidden_classes_exprs:
            playarea = module.__dict__
            var = eval(expr, playarea)
            name = type(var).__name__
            process_class_using_instance(moduleElt, var, name, callables)

def writeCixFileForElement(filename, root):
    stream = open(filename, 'w')
    stream.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    prettify(root)
    tree = ElementTree(root)
    tree.write(stream)
    stream.close()

if __name__ == "__main__":
    parser = optparse.OptionParser()
    parser.add_option('-f', '--force', dest='force', default=False)
    parser.add_option('-n', '--name', dest='name', help="The catalog name")
    parser.add_option('-d', '--description', dest='description',
                      help="The catalog description")
    parser.add_option('-o', '--onefile', dest='onefile',
                      help="Combine all scans into the one CIX file.")
    (options, args) = parser.parse_args()
    if len(args) < 1:
        parser.print_help()
        sys.exit(0)
    root = None
    for arg in args:
        print "Generating CIX for", arg
        if root is None or not options.onefile:
            root = Element("codeintel", name=arg, version="2.0", xmlns="urn:activestate:cix:2.0")
            if options.name:
                root.set("name", options.name)
            if options.description:
                root.set("description", options.description)

        docmodule(arg, root, options.force, usefile=True)

        if not options.onefile:
            perform_smart_analysis(root)
            writeCixFileForElement(arg + ".cix", root)

    if root is not None and options.onefile:
        perform_smart_analysis(root)
        writeCixFileForElement(options.onefile, root)
    print "done."
