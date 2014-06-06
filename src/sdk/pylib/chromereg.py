#!/usr/bin/env python
# Copyright (c) 2011 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Gecko 2.0 pyxpcom chrome registration helper

Given a python component and a chrome.manifest file, parse the component for
XPCOM registration information and modify the manifest to declare them.
Also suppports registering XPTypeLib files.
"""

import re
import sys
import urllib
from os.path import exists, basename, splitext
try:
    import ast
except ImportError:
    # Support Python 2.5
    from compiler import ast

def _dump_ast(node, indent="", stream=sys.stdout):
    """Pretty-print the AST in a somewhat readable manner.
    
    @param node The AST node to dump
    @param indent the leading indent, used for recursive calls
    @param stream the stream to dump to
    """
    if isinstance(node, list):
        for item in node:
            dump_ast(item, indent)
        return
    stream.write("%s%s\n" % (indent, type(node).__name__))
    for name, value in ast.iter_fields(node):
        if isinstance(value, ast.AST):
            stream.write("%s  %s:\n" % (indent, name))
            dump_ast(value, "  " + indent)
        elif isinstance(value, list):
            stream.write("%s  %s:\n" % (indent, name))
            dump_ast(value, indent + "    ")
        else:
            stream.write("%s  %s: %s\n" % (indent, name, value))

class ChromeReg(object):
    """Helper class to group related methods to register a component"""
    def __init__(self, source_file, manifest, relpath=""):
        """ChromeReg constrcutor
        
        @param source_file a Python or XPTypeLib file to register
        @param manifest the manifest to write to
        @param relpath the relative path from the manifest to the registered
            component
        """
        self.vars = {} # variables seen
        self.existing_lines = None # existing chrome registration lines
        self.new_lines = set() # added chrome registration lines

        self.source_file = source_file
        self.manifest_name = manifest
        if len(relpath) == 0 or relpath.endswith("/") or relpath.endswith("\\"):
            self.relpath = relpath
        else:
            self.relpath = relpath + "/"

    def read_manifest(self):
        """Read the chrome manifest for existing registrations"""
        assert self.existing_lines is None, \
            "reading existing manifest twice"
        self.existing_lines = set()
        if not exists(self.manifest_name):
            # nothing to read
            return
        inputfile = file(self.manifest_name, "rU")
        for line in inputfile.readlines():
            # normalize whitespace - strip leading/trailing, collapse inner
            line = " ".join(line.split())
            if line.startswith("#"):
                # skip all comments (repeating them can make sense)
                continue
            self.existing_lines.add(line)

    def write_manifest(self):
        """Write new registrations to the chrome manifest"""
        assert isinstance(self.existing_lines, set), \
            "writing manifest without reading it first"
        # skip the lines we already have
        for line in self.existing_lines:
            self.new_lines.discard(line)
        if len(self.new_lines) < 1:
            # nothing to write
            return
        outputfile = file(self.manifest_name, "a")
        for line in self.new_lines:
            outputfile.write("%s\n" % line)

    def set(self, scope, name, value):
        """Set the value of an expression
        
        @param scope the scope to set the value in, limited to a single level.
            May be an empty string to indicate global scope.
        @param name the name of the variable to set
        @param value the new value of the variable
        """
        if not scope in self.vars:
            self.vars[scope] = {}
        self.vars[scope][name] = value

    # Note: default=sys is used to determine if the "default" arg was set
    def get(self, expr, scope=None, default=sys):
        """ Get the value of an expression
        
        @param expr - string or (AST) expression to evaluate
        @param scope - name the scope in which to look for variables; the
            global scope will also be used.
        @param default - the value when expr doesn't exist
        @return the evaluated expression (as a string)
        """
    
        def lookup(key):
            """Look up the given variable name
            @param key the variable name
            """
            try:
                # special python keyword literals
                value = {"None":  None,
                         "True":  True,
                         "False": False,
                        }.get(key, "")
                if value != "":
                    return value
        
                if scope in self.vars and key in self.vars[scope]:
                    return self.vars[scope][key]
                if key in self.vars[""]:
                    return self.vars[""][key]
                assert (scope in self.vars and key in self.vars[scope]) or (key in self.vars[""]), \
                    "Failed to find {key} for {scope} in {file} line {line}".format(
                        {"key": key, "scope": scope, "file": self.source_file, "line": expr.lineno})
            except KeyError:
                if default is sys:
                    raise
                return default

        # the scope name "" (empty string) is reserved for globals since it's
        # not a valid python identifier
        assert scope != "", "Invalid scope name"
    
        if isinstance(expr, str):
            # Direct string lookup.
            return lookup(expr)

        if isinstance(expr, ast.Name):
            # variable or keyword
            return lookup(expr.id)
    
        if isinstance(expr, ast.Num):
            # number literal
            return expr.n

        if isinstance(expr, ast.Str):
            # string literal
            return expr.s
    
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Mod) and isinstance(expr.left, ast.Str):
            # expression is a formatted string: "foo %s" % bar
            if isinstance(expr.right, ast.Str) or isinstance(expr.right, ast.Name):
                # a single value; wrap it in a list
                values = [self.get(expr.right, scope)]
            elif isinstance(expr.right, ast.Tuple) or isinstance(expr.right, ast.List):
                # multiple values; read them in turn
                values = []
                for v in expr.right.elts:
                    assert isinstance(v, ast.Name), \
                        "don't know how to handle %s (%s) when parsing %s line %s" % (
                            type(v).__name__, ast.dump(v), self.source_file, stmt.lineno)
                    values.append(lookup(v.id))
            else:
                assert False, \
                    "don't know how to handle %s (%s) when parsing %s line %s" % (
                        type(expr.right).__name__, ast.dump(expr.right),
                        self.source_file, stmt.lineno)
            # value lookup done, do the formatting
            return expr.left.s % tuple(values)

        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add):
            # x + y: hopefully these things are strings...
            return self.get(expr.left, scope) + self.get(expr.right, scope)
    
        raise NotImplementedError(
            "%s line %i col %i in class %s: don't know how to deal with expression %s" % (
            self.source_file, expr.lineno, expr.col_offset, scope, ast.dump(expr)))

    def _parse_class(self, clazz):
        """Parse the AST of a single class definition
        
        @param clazz the AST node for the class
        """
        componentData = {"name": clazz.name,
                         "file": self.relpath + basename(self.source_file),
                         "desc": "%s PyXPCOM component" % (clazz.name)}
        for stmt in clazz.body:
            if not isinstance(stmt, ast.Assign):
                # we only care about assignments (to the magic props)
                continue
    
            if isinstance(stmt.value, ast.Num):
                # assignment from a string; we might need this later.
                for target in stmt.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    self.set(clazz.name, target.id, self.get(stmt.value))

            if isinstance(stmt.value, ast.Str):
                # assignment from a string; we might need this later.
                for target in stmt.targets:
                    if not isinstance(target, ast.Name):
                        continue
                    self.set(clazz.name, target.id, self.get(stmt.value))
    
            if filter(lambda n: hasattr(n, "id") and n.id == "_reg_contractid_", stmt.targets):
                # this is an assignment to _reg_contractid_
                value = self.get(stmt.value, clazz.name)
                if value is not None:
                    componentData["contractid"] = value.replace(" ", "%20")
    
            if filter(lambda n: hasattr(n, "id") and n.id == "_reg_clsid_", stmt.targets):
                # this is an assignment to _reg_clsid_
                value = self.get(stmt.value, clazz.name)
                if value is not None:
                    # check for CIDs with missing braces
                    if re.match(r"^[0-9a-fA-F-]{36}$", value):
                        value = "{%s}" % value
                    componentData["clsid"] = value
    
            if filter(lambda n: hasattr(n, "id") and n.id == "_reg_desc_", stmt.targets):
                # this is an assignment to _reg_desc_
                value = self.get(stmt.value, clazz.name)
                if value is not None:
                    componentData["desc"] = urllib.quote(value)

            if filter(lambda n: hasattr(n, "id") and n.id == "_reg_categories_", stmt.targets):
                # this is a category registration
                assert isinstance(stmt.value, ast.Tuple) or isinstance(stmt.value, ast.List), \
                    "%s line %i: category assignment must be a list, got %s" % (
                    self.source_file, stmt.value.lineno, ast.dump(stmt.value))
                for entry in stmt.value.elts:
                    assert isinstance(entry, ast.Tuple) or isinstance(entry, ast.List), \
                        "%s line %i: category entry must be a list, got %s" % (
                        self.source_file, entry.lineno, ast.dump(entry))
                    assert len(entry.elts) == 2 or len(entry.elts) == 3, \
                        "%s line %i: category entry must have 2 or 3 values, got %s" % (
                        self.source_file, entry.lineno, ast.dump(entry))
                    if not "category" in componentData:
                        componentData["category"] = []
                    entryData = list(map(lambda k: self.get(k, clazz.name), entry.elts))
                    assert len(entryData) == 2 or len(entryData) == 3, \
                        "%s line %i: category entry %s for class %s has " \
                        "incorrect number of args: %d (expected 2 or 3)" % (
                            self.source_file, entry.lineno, entryData[0],
                            clazz.name, entryData)
                    componentData["category"].append(entryData)

            # koILanguage shebangPatterns attribute - which is a list of regular expressions.
            if filter(lambda n: hasattr(n, "id") and n.id == "shebangPatterns", stmt.targets):
                # shebangPatterns = [ re.compile(ur'\A#!.*ruby.*$', re.IGNORECASE | re.MULTILINE | re.S),]
                assert isinstance(stmt.value, ast.Tuple) or isinstance(stmt.value, ast.List), \
                    "%s line %i: shebangPatterns assignment must be a list, got %s" % (
                    self.source_file, stmt.value.lineno, ast.dump(stmt.value))
                shebangPatterns = []
                for entry in stmt.value.elts:
                    # Should be a regular expression call.
                    re_expr = self.get(entry.args[0], clazz.name)
                    re_flags_expr = ast.dump(entry.args[1])
                    attr_names = (
                        ('I', 'IGNORECASE', re.IGNORECASE),
                        ('L', 'LOCALE', re.LOCALE),
                        ('M', 'MULTILINE', re.MULTILINE),
                        ('S', 'DOTALL', re.DOTALL),
                        ('U', 'UNICODE', re.UNICODE),
                        ('X', 'VERBOSE', re.VERBOSE),
                    )
                    re_flags = 0
                    for short_name, long_name, value in attr_names:
                        for name in (short_name, long_name):
                            if "attr='%s'" % (name, ) in re_flags_expr:
                                re_flags |= value
                                break
                    shebangPatterns.append((re_expr, re_flags))
                self.set(clazz.name, "shebangPatterns", shebangPatterns)

            # koILanguage class attributes that are of type 'list'.
            for lang_attr in ("extraFileAssociations", "modeNames", "namespaces", "publicIdList", "systemIdList"):
                if filter(lambda n: hasattr(n, "id") and n.id == lang_attr, stmt.targets):
                    assert isinstance(stmt.value, ast.Tuple) or isinstance(stmt.value, ast.List), \
                        "%s line %i: %s assignment must be a list, got %s" % (
                        self.source_file, stmt.value.lineno, lang_attr, ast.dump(stmt.value))
                    assert all(isinstance(x, ast.Str) for x in stmt.value.elts), \
                        "%s line %i: %s assignment must be a list of strings, got %s" % (
                        self.source_file, stmt.value.lineno, lang_attr, ast.dump(stmt.value))
                    self.set(clazz.name, lang_attr, [x.s for x in stmt.value.elts])

        if "contractid" in componentData and "clsid" in componentData:
            self.new_lines.add("component {clsid} {file}".format(**componentData))
            self.new_lines.add("contract {contractid} {clsid}".format(**componentData))
            if "category" in componentData:
                for entry in componentData["category"]:
                    category = entry[0]
                    entryname = urllib.quote(entry[1])
                    if len(entry) == 3:
                        entryvalue = entry[2]
                    else:
                        # Default to using the contract id.
                        entryvalue = componentData["contractid"]
                    self.new_lines.add("category {category} {entryname} {entryvalue}".format(**locals()))

            # Check if it's a Komodo language.
            contractid = componentData.get("contractid")
            if "koLanguage?language=" in contractid:
                # Convert koILanguage attributes into one (json-encoded) XPCOM category.
                language_name = self.get("name", scope=clazz.name)
                entrydict = {}
                for lang_attr in ("name", "primary", "internal", "accessKey", "defaultExtension",
                                  "extraFileAssociations", "shebangPatterns", "modeNames",
                                  "namespaces", "publicIdList", "systemIdList"):
                    # category  language_attribute  (LANG)_(ATTR)  (VALUE)  1
                    entryvalue = self.get(lang_attr, scope=clazz.name, default=None)
                    if entryvalue is None:
                        continue
                    entrydict[lang_attr] = entryvalue
                    continue
                import json
                entryname = urllib.quote(language_name)
                entryvalue = urllib.quote(json.dumps(entrydict))
                self.new_lines.add("category komodo-language-info {entryname} {entryvalue}".format(**locals()))

    def register(self):
        """Main entry point to register the component in the chrome registry"""
        self.read_manifest()
        extension = splitext(self.source_file)[1]
        relname = self.relpath + basename(self.source_file)
        if extension in (".py",):
            self._register_python()
        elif extension in (".xpt",):
            self.new_lines.add("interfaces %s" % relname)
        elif extension in (".dll", ".so", ".dylib"):
            self.new_lines.add("binary-component %s" % relname)
        elif extension in (".manifest",):
            self.new_lines.add("manifest %s" % relname)
        else:
            assert False, "Don't know how to register %s" % self.source_file
        self.write_manifest()
    
    def _register_python(self):
        """Regsiter the component, knowing that it is a python file"""
        inputfile = file(self.source_file, "r")
        tree = ast.parse(inputfile.read(), self.source_file)
        assert isinstance(tree, ast.Module), \
            "failed to parse %s" % self.source_file
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, ast.Assign):
                # simple assignment of globals, hopefully into a string
                if not isinstance(node.value, ast.Str):
                    continue
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        self.set("", target.id, node.value.s)
            elif isinstance(node, ast.ClassDef):
                # we have a class; try to register it
                self._parse_class(node)

    def add_line(self, line):
        """Add a raw line into the manifest file."""
        self.read_manifest()
        self.new_lines.add(line)
        self.write_manifest()

def register_category(manifest, entry):
    """Add the category entry
    
    @param manifest the manifest file to write to; it will be modified in-place
    @param entry the category entry (line) to add
    """
    registry = ChromeReg(None, manifest)
    registry.add_line("category " + entry)
    return registry

def register_file(source_file, manifest, relpath=""):
    """Register all components in a given source file in the manifest
    
    @param source_file a Python source file to read from; it must be
        syntactically valid python.  Alternatively, a valid XPTypeLib file.
    @param manifest the manifest file to write to; it will be modified in-place
    @param repath The relative path from the manifest to the component when
        installed
    """
    registry = ChromeReg(source_file, manifest, relpath=relpath)
    registry.register()
    return registry

if __name__ == "__main__":
    # using this as a command line script (possibly in the build system)
    usage_message = "Usage: %s komodo.manifest component.py [relpath]" % sys.argv[0]
    assert len(sys.argv) == 3 or len(sys.argv) == 4, usage_message
    manifest = sys.argv[1]
    source_file = sys.argv[2]
    assert exists(source_file), usage_message + ": can't find file %s" % (source_file,)
    if len(sys.argv) == 4:
        relpath = sys.argv[3]
    else:
        relpath = ""
    register_file(source_file, manifest, relpath)
