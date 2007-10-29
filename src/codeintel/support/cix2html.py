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
# Author:
#   Todd Whiteman (ToddW@ActiveState.com)

r"""cix2html -- Utilities to generate html content from cix files"""

__revision__ = "$Id$"
__version_info__ = (1, 0, 0)
__version__ = '.'.join(map(str, __version_info__))

import os
from os.path import isfile, isdir, exists, dirname, abspath, splitext, join
import sys
from optparse import OptionParser
import logging

sys.path.insert(0, join(dirname(dirname(abspath(__file__))), "lib"))
from ciElementTree import Element, SubElement, ElementTree
from codeintel2.manager import Manager
from codeintel2.tree import tree_from_cix
del sys.path[0]

import cmdln

#
# HTML API generating code
#

def _elemCompare(elem1, elem2):
    #return cmp(elem1.get("name"), elem2.get("name"))
    name1, name2 = elem1.get("name"), elem2.get("name")
    if name1:
        name1 = name1.lower()
    if name2:
        name2 = name2.lower()
    return cmp(name1, name2)

def _convertDocToHtml(html, elem, cls="doc"):
    doc = elem.get('doc')
    if doc:
        p = SubElement(html, "p", {"class":cls})
        p.text = doc

def _convertArgumentToHtml(html, elem):
    elem_name = elem.get("name")
    elem_type = elem.get('ilk') or elem.tag
    para = SubElement(html, "p")
    span = SubElement(para, "span", {"class": elem_type})
    span.text = elem_name
    citdl = elem.get("citdl")
    if citdl:
        citdl_span = SubElement(para, "span", {"class": "citdl"})
        citdl_span.text = " - %s" % (citdl, )
        _convertDocToHtml(html, elem, "doc_for_argument")

def _convertFunctionToHtml(html, elem):
    elem_name = elem.get("name")
    elem_type = elem.get('ilk') or elem.tag
    div = SubElement(html, "div", {"class": "function"})
    span = SubElement(div, "span", {"class": elem_type})
    codeElements = elem.get('attributes', "").split(" ")
    isCtor = False
    if "__ctor__" in codeElements:
        isCtor = True
        codeElements.remove("__ctor__")
    #else:
    #    codeElements.push("void")
    if not isCtor:
        #span.text = "%s %s %s" % (elem_type, " ".join(codeElements),
        #                          elem.get('signature') or elem_name + "()")
        span.text = "%s %s" % (" ".join(codeElements),
                               elem.get('signature') or elem_name + "()")
        _convertDocToHtml(div, elem)
    else:
        span.text = "%s" % (elem.get('signature') or elem_name + "()")

    function_arguments = [ x for x in elem if x.get("ilk") == "argument" and (x.get("citdl") or x.get("doc")) ]
    if function_arguments:
        arg_div = SubElement(div, "div", {"class": "function_arguments"})
        arg_div.text = "Arguments"
        for arg_elem in function_arguments:
            #sys.stderr.write("function arg: %r\n" % (arg_elem))
            _convertArgumentToHtml(arg_div, arg_elem)
    returns = elem.get('returns')
    if returns:
        ret_div = SubElement(div, "div", {"class": "function_returns"})
        ret_p = SubElement(ret_div, "p")
        ret_p.text = "Returns - "
        span = SubElement(ret_p, "span", {"class": "function_returns"})
        span.text = returns

def _convertVariableToHtml(html, elem):
    """Convert cix elements into html documentation elements

    Generally this will operate on blobs and variables with citdl="Object".
    """
    elem_name = elem.get("name")
    elem_type = elem.get('ilk') or elem.tag
    div = SubElement(html, "div", {"class": "variable"})
    para = SubElement(div, "p")
    span = SubElement(para, "span", {"class": elem_type})
    span.text = elem_name
    citdl = elem.get("citdl")
    if citdl:
        citdl_span = SubElement(para, "span", {"class": "variable_cidtl"})
        citdl_span.text = " - %s" % (citdl, )
    _convertDocToHtml(div, elem)

def _convertClassToHtml(html, elem):
    html = SubElement(html, "div", {"class": "class"})
    span = SubElement(html, "span", {"class": "class"})
    span.text = "class %s" % (elem.get("name"))
    _convertDocToHtml(html, elem)
    variables = sorted([ x for x in elem if x.tag == "variable" ], _elemCompare)
    functions = sorted([ x for x in elem if x.get("ilk") == "function" ], _elemCompare)
    constructors = [ x for x in functions if "__ctor__" in x.get("attributes", "").split(" ") ]
    if constructors:
        h3 = SubElement(html, "h3", {"class": "class"})
        h3.text = "Constructor"
        div = SubElement(html, "div", {"class": "class_variables"})
        for ctor_elem in constructors:
            functions.remove(ctor_elem)
            _convertFunctionToHtml(div, ctor_elem)
            SubElement(div, "hr", {"class": "constructor_separator"})
    if variables:
        h3 = SubElement(html, "h3", {"class": "class"})
        h3.text = "Class variables"
        div = SubElement(html, "div", {"class": "class_variables"})
        for var_elem in variables:
            _convertVariableToHtml(div, var_elem)
            SubElement(div, "hr", {"class": "variable_separator"})
    if functions:
        h3 = SubElement(html, "h3", {"class": "class"})
        h3.text = "Class functions"
        div = SubElement(html, "div", {"class": "class_functions"})
        for var_elem in functions:
            _convertFunctionToHtml(div, var_elem)
            SubElement(div, "hr", {"class": "function_separator"})

def _convertScopeToHtml(html, scope, namespace, namespace_elements):
    name = scope.get('name')
    if namespace:
        namespace += ".%s" % (name)
    else:
        namespace = name
    #sys.stderr.write("namespace: %s\n" % (namespace, ))
    a_href = SubElement(html, "a", name=namespace)
    # This is to fix a bug where firefox displays all elements with the same
    # css style as set in "a", like underline etc...
    a_href.text = " "

    div = SubElement(html, "div", {"name": namespace, "class": "namespace"})
    namespace_elements.append((namespace, div))
    h2 = SubElement(div, "h2", {"name": namespace, "class": "namespace"})
    h2.text = namespace
    _convertDocToHtml(div, scope, "doc_for_namespace")

    variables = set([ x for x in scope if x.tag == "variable" ])
    functions = set([ x for x in scope if x.get("ilk") == "function" ])
    classes = set([ x for x in scope if x.get("ilk") == "class" ])
    subscopes = set([ x for x in variables if x.get("citdl") == "Object" ])
    variables.difference_update(subscopes)

    if variables:
        h3 = SubElement(div, "h3")
        h3.text = "Variables"
        for elem in sorted(variables, _elemCompare):
            _convertVariableToHtml(div, elem)
            SubElement(div, "hr", {"class": "variable_separator"})
    if functions:
        h3 = SubElement(div, "h3")
        h3.text = "Functions"
        for elem in sorted(functions, _elemCompare):
            _convertFunctionToHtml(div, elem)
            SubElement(div, "hr", {"class": "function_separator"})
    if classes:
        h3 = SubElement(div, "h3")
        h3.text = "Classes"
        for elem in sorted(classes, _elemCompare):
            _convertClassToHtml(div, elem)
            SubElement(div, "hr", {"class": "class_separator"})
    for elem in sorted(subscopes, _elemCompare):
        _convertScopeToHtml(div, elem, namespace, namespace_elements)

def _html_ci_elem(opts, elem, lang=None):
    # Taken from codeintel2.tree, modified to ensure it keeps all
    # existing text and tail data. Since this is used on generated
    # xml content, there is no need to worry about existing newlines
    # and whitespace, as there will be none existing at this point.
    def pretty_tree_from_tree(tree, indent_width=2):
        """Add appropriate .tail and .text values to the given tree so that
        it will have a pretty serialization.
    
        Presumption: This is a CIX 2.0 tree.
        """
        INDENT = ' '*indent_width
    
        def _prettify(elem, indent_level=0):
            if elem: # i.e. elem has child elements
                elem.text = '\n' + INDENT*(indent_level+1) + (elem.text or "")
                for child in elem:
                    _prettify(child, indent_level+1)
                elem[-1].tail = (elem[-1].tail or "") + '\n' + INDENT*indent_level
                elem.tail = (elem.tail or "") + '\n' + INDENT*indent_level
            else:
                #elem.text = None
                elem.tail = (elem.tail or "") + '\n' + INDENT*indent_level

        _prettify(tree)
        return tree

    def remove_private_elements(elem):
        """Remove all the private cix elements."""
        parent_map = dict((c, p) for p in elem.getiterator() for c in p)
        for node in list(elem.getiterator()):
            attributes = node.get("attributes", "").split(" ")
            if "private" in attributes or "__hidden__" in attributes:
                # Remove it
                parentnode = parent_map.get(node)
                if parentnode is not None:
                    parentnode.remove(node)

    # Set the css reference file
    if not opts.css_reference_files:
        opts.css_reference_files = ["aspn.css", "api.css"]

    html = Element("html")
    head = SubElement(html, "head")
    for css_filename in opts.css_reference_files:
        SubElement(head, "link", rel="stylesheet", type="text/css",
                   href=css_filename)
    body = SubElement(html, "body")
    body_div = SubElement(body, "div", {"id": "body"})

    namespace_elements = []
    # Remove any private cix elements, as they are not externally visible.
    remove_private_elements(elem)
    if elem.tag == "file":
        for child in elem:
            for subchild in child:
                _convertScopeToHtml(body_div, subchild, "", namespace_elements)
    else:
        _convertScopeToHtml(body_div, elem, "", namespace_elements)

    # Now, we can print out the html in a few formats:
    #  Single file - the default and only implemented format at present
    #  File for each namespace and an index - Not done.

    # Try to build an index, placed in same html file
    #nav_div = SubElement(body, "div", {"id": "nav"})
    #ul = SubElement(nav_div, "ul")
    #for ns, elem in namespace_elements:
    #    li = SubElement(ul, "li")
    #    a_href = SubElement(li, "a", href="#%s" % (ns))
    #    a_href.text = ns

    footer_div = SubElement(body, "div", {"id": "footer"})

    pretty_tree_from_tree(html)
    tree = ElementTree(html)
    xhtml_header = '<?xml version="1.0"?>\n' \
                   '<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" ' \
                   '"http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n'

    stream = sys.stdout
    if opts.output:
        stream = file(opts.output, "wb")
    stream.write(xhtml_header)
    tree.write(stream)

    if opts.toc_file:
        file_href = opts.output or "komodo-js-api.html"
        toc_node = Element("node", name="Komodo JavaScript API Reference",
                           link=file_href)
        for ns, elem in namespace_elements:
            sub_node = SubElement(toc_node, "node", name=ns, link="%s#%s" % (
                          file_href, ns, ))

        pretty_tree_from_tree(toc_node)
        toc_file = open(opts.toc_file, "w")
        tree = ElementTree(toc_node)
        tree.write(toc_file)


def cix2html(opts, path):
    """Turn cix file into html API documentation.

    Example:
        cix2html path/to/foo.cix#AClass.amethod
        cix2html path/to/foo.cix -o file.html

    ${cmd_usage}
    ${cmd_option_list}
    """
    mgr = Manager()
    mgr.upgrade()
    mgr.initialize()
    try:
        def blobs_from_tree(tree):
            for file_elem in tree:
                for blob in file_elem:
                    yield blob

        if '#' in path:
            path, anchor = path.rsplit('#', 1)
        else:
            anchor = None

        if path.endswith(".cix"):
            tree = tree_from_cix(open(path, 'r').read())
            #buf = mgr.buf_from_content("", tree[0].get("lang"), path=path)
        else:
            buf = mgr.buf_from_path(path, lang=opts.lang)
            tree = buf.tree

        if anchor is not None:
            # Lookup the anchor in the codeintel CIX tree.
            lpath = re.split(r'\.|::', anchor)
            for elem in blobs_from_tree(tree):
                # Generally have 3 types of codeintel trees:
                # 1. single-lang file: one <file>, one <blob>
                # 2. multi-lang file: one <file>, one or two <blob>'s
                # 3. CIX stdlib/catalog file: possibly multiple
                #    <file>'s, likely multiple <blob>'s
                # Allow the first token to be the blob name or lang.
                # (This can sometimes be weird, but seems the most
                # convenient solution.)
                if lpath[0] in (elem.get("name"), elem.get("lang")):
                    remaining_lpath = lpath[1:]
                else:
                    remaining_lpath = lpath
                for name in remaining_lpath:
                    try:
                        elem = elem.names[name]
                    except KeyError:
                        elem = None
                        break # try next lang blob
                if elem is not None:
                    break # found one
            else:
                log.error("could not find `%s' definition (or blob) in `%s'",
                          anchor, path)
                return 1
        else:
            elem = tree

        try:
            if elem.tag  == "codeintel":
                _html_ci_elem(opts, elem.getchildren()[0])
            else:
                _html_ci_elem(opts, elem)
        except IOError, ex:
            if ex.errno == 0:
                # Ignore this error from aborting 'less' of 'ci2 outline'
                # output:
                #    IOError: (0, 'Error')
                pass
            else:
                raise
        except Exception, e:
            import traceback
            traceback.print_exc()
    finally:
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
    try:
        from xpcom import components
        _xpcom_ = True
    except ImportError:
        _xpcom_ = False
    else:
        koTestSvc = components.classes["@activestate.com/koTestService;1"] \
            .getService(components.interfaces.koITestService)
        koTestSvc.init()

def main(argv):
    usage = """usage: %prog [options] path_to_cix

    Example:
        cix2html path/to/foo.cix#AClass.amethod
        cix2html path/to/foo.cix -o htmldir
"""
    parser = OptionParser(usage=usage)
    parser.add_option("-c", "--css", dest="css_reference_files", action="append",
                      help="add css reference file for styling"
                           " (can be used more than once)")
    parser.add_option("-o", "--output", dest="output",
                      help="filename for generated html output, defaults to stdout")
    parser.add_option("-t", "--toc-file", dest="toc_file",
                      help="filename for generated toc xml file")
    parser.add_option("-l", "--language", dest="lang",
                      help="only include docs for the supplied language")
    (opts, args) = parser.parse_args()
    if len(args) != 1:
        parser.print_usage()
        return 1
    else:
        _prepare_xpcom()
        cix2html(opts, args[0])
    return 0


if __name__ == "__main__":
    logging.basicConfig()
    sys.exit(main(sys.argv))
