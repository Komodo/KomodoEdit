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

"""toc -- module and command-line interface for ActiveState TOC XML files

See: http://specs.activestate.com/ASPN_Doc_Import/

Module interface:
    toc2html(...)       convert the given 'toc.xml' to an HTML file
    html2toc(...)       convert the given HTML to a 'toc.xml' file
    toc2ec(...)         convert the given 'toc.xml' to a JavaScript snippet
                        for the Expand/Collapse system used by the new
                        ActiveHelp system.
    linkcheck(...)      check a 'toc.xml' for link errors
"""
# TODO:
#   - Allow or warn about the usage of commas to separate flags on
#     <node> elements.
#   - Add a "toc lint ..." or "toc validate ..." to validate the given
#     toc.xml document.
#   - XXX Look at other <param> info in .hhc files (e.g. PyWin32.chm),
#     check out the python.org Python.chm
#        <param name="ImageNumber" value="1">
#        <param name="ImageNumber" value="11">
#     and at the top of the <body>:
#        <OBJECT type="text/site properties">
#            <param name="ImageType" value="Folder">
#        </OBJECT>


import os
import sys
import re
import getopt
import pprint
import cmd
import webbrowser
import string
import xml.sax
from xml.sax import saxutils
import xml.sax.handler
import tempfile
from HTMLParser import HTMLParser
import htmlentitydefs



#---- exceptions

class TOCError(Exception):
    pass


#---- internal logging facility

class Logger:
    DEBUG, INFO, WARN, ERROR, FATAL = range(5)
    def __init__(self, name, level=None, streamOrFileName=sys.stderr):
        import types
        self.name = name
        if level is None:
            self.level = self.WARN
        else:
            self.level = level
        if type(streamOrFileName) == types.StringType:
            self.stream = open(streamOrFileName, 'w')
            self._opennedStream = 1
        else:
            self.stream = streamOrFileName
            self._opennedStream = 0
    def __del__(self):
        if self._opennedStream:
            self.stream.close()
    def _getLevelName(self, level):
        levelNameMap = {
            self.DEBUG: "DEBUG",
            self.INFO: "INFO",
            self.WARN: "WARN",
            self.ERROR: "ERROR",
            self.FATAL: "FATAL",
        }
        return levelNameMap[level]
    def setLevel(self, level):
        self.level = level
    def isEnabled(self, level):
        return level >= self.level
    def isDebugEnabled(self): return self.isEnabled(self.DEBUG)
    def isInfoEnabled(self): return self.isEnabled(self.INFO)
    def isWarnEnabled(self): return self.isEnabled(self.WARN)
    def isErrorEnabled(self): return self.isEnabled(self.ERROR)
    def isFatalEnabled(self): return self.isEnabled(self.FATAL)
    def log(self, level, msg, *args):
        if level < self.level:
            return
        message = "%s: %s: " % (self.name, self._getLevelName(level).lower())
        message = message + (msg % args) + "\n"
        self.stream.write(message)
        self.stream.flush()
    def debug(self, msg, *args):
        self.log(self.DEBUG, msg, *args)
    def info(self, msg, *args):
        self.log(self.INFO, msg, *args)
    def warn(self, msg, *args):
        self.log(self.WARN, msg, *args)
    def error(self, msg, *args):
        self.log(self.ERROR, msg, *args)
    def fatal(self, msg, *args):
        self.log(self.FATAL, msg, *args)


#---- globals

_version_ = (0, 7, 0)
log = Logger("toc", Logger.WARN)


#---- internal support stuff

class _ListCmd(cmd.Cmd):
    """Pass arglists instead of command strings to commands.

    Modify the std Cmd class to pass arg lists instead of command lines.
    This seems more appropriate for integration with sys.argv which handles
    the proper parsing of the command line arguments (particularly handling
    of quoting of args with spaces).
    """
    name = "_ListCmd"
    
    def cmdloop(self, intro=None):
        raise NotImplementedError()

    def onecmd(self, argv):
        # Differences from Cmd
        #   - use an argv, rather than a command string
        #   - don't specially handle the '?' redirect to 'help'
        #   - don't allow the '!' shell out
        if not argv:
            return self.emptyline()
        self.lastcmd = argv
        cmdName = argv[0]
        try:
            func = getattr(self, 'do_' + cmdName)
        except AttributeError:
            return self.default(argv)
        #try:
        return func(argv)
        #except TypeError, ex:
        #    log.error("%s: %s", cmdName, ex)
        #    log.error("try '%s help %s'", self.name, cmdName)
        #    if 0:   # for debugging
        #        print
        #        import traceback
        #        traceback.print_exception(*sys.exc_info())

    def default(self, args):
        log.error("unknown syntax: '%s'", " ".join(args))
        return 1

    def _do_one_help(self, arg):
        try:
            # If help_<arg1>() exists, then call it.
            func = getattr(self, 'help_' + arg)
        except AttributeError:
            try:
                doc = getattr(self, 'do_' + arg).__doc__
            except AttributeError:
                doc = None
            if doc: # *do* have help, print that
                sys.stdout.write(doc + '\n')
                sys.stdout.flush()
            else:
                log.error("no help for '%s'", arg)
        else:
            return func()

    # Technically this improved do_help() does not fit into _ListCmd, and
    # something like this would be more appropriate:
    #    def do_help(self, argv):
    #        cmd.Cmd.do_help(self, ' '.join(argv[1:]))
    # but I don't want to make another class for it.
    def do_help(self, argv):
        if argv[1:]:
            for arg in argv[1:]:
                retval = self._do_one_help(arg)
                if retval:
                    return retval
        else:
            doc = self.__class__.__doc__  # try class docstring
            if doc:
                sys.stdout.write(doc + '\n')
                sys.stdout.flush()
            elif __doc__:  # else try module docstring
                sys.stdout.write(__doc__)
                sys.stdout.flush()

    def emptyline(self):
        # Differences from Cmd
        #   - Don't repeat the last command for an emptyline.
        pass


class _TOC2HTMLHandler_li(xml.sax.handler.ContentHandler):
    def __init__(self, dressing, flags=[]):
        self.dressing = dressing
        self.flags = flags
        self.html = ""
        self.indent = "  "
        self.level = None
        self.onDeckAt = {} # <ul> content that is on-deck at a given level
        self.nodeAt = {} # <level> : <boolean>
        # Stack of nodes to skip. The stack is started when a <node> has
        # a "flags" attribute that doesn't match given self.flags. All child
        # <node>s of a skipped <node> are also skipped.
        self.skipStack = []
    def startDocument(self):
        if self.dressing:
            self.add("""\
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN" "http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">
<html xmlns="http://www.w3.org/1999/xhtml" xml:lang="en" lang="en">
""")
        self.level = 0

    def endDocument(self):
        if self.dressing:
            self.add("\n</html>")
    def startElement(self, name, attrs):
        if name == "toc":
            if self.dressing:
                self.add("""
<head>
  <title>%(name)s %(version)s - Table of Contents</title>
</head>
<body>
""" % attrs)
            self.add("<ul>")
            self.level += 1
        elif name == "node":
            # Determine if this node should be skipped.
            if self.skipStack:
                self.skipStack.append(attrs["name"])
            elif self.flags and attrs.has_key("flags"):
                #XXX Warn or error out or allow it if it looks like
                #    commas (and perhaps other common separators) are
                #    being used here.
                nodeFlags = attrs["flags"].split()
                for nf in nodeFlags:
                    if nf in self.flags:
                        break
                else:
                    self.skipStack.append(attrs["name"])
            if not self.skipStack:
                # No skipping this node -- process it.
                if self.onDeckAt.get(self.level):
                    self.add(self.onDeckAt[self.level])
                    self.level += 1
                self.nodeAt[self.level] = 1
                if attrs.has_key("class"):
                    self.add('\n%s<li class=%s>'
                             % (self.indent*self.level,
                                saxutils.quoteattr(attrs["class"])))
                else:
                    self.add('\n%s<li>' % (self.indent*self.level))
                self.level += 1
                if attrs.has_key("link"):
                    self.add('<a href=%s>%s</a>'\
                             % (saxutils.quoteattr(attrs["link"]),
                                saxutils.escape(attrs["name"])))
                else:
                    self.add(saxutils.escape(attrs["name"]))
                self.onDeckAt[self.level] = '\n%s<ul>' % (self.indent*self.level)
    def endElement(self, name):
        if name == "node":
            if self.skipStack:
                self.skipStack.pop()
            elif self.nodeAt.get(self.level): # we need to close the <ul>
                self.level -= 1
                self.add('\n%s</ul>' % (self.indent*self.level))
                self.level -= 1
                self.add('\n%s</li>' % (self.indent*self.level))
            else:
                self.level -= 1
                self.add('</li>')
        elif name == "toc":
            self.add("\n</ul>")
            if self.dressing:
                self.add("\n\n</body>")
    def add(self, content):
        """Add some HTML content."""
        if 0: #XXX for debugging
            sys.stdout.write(content)
        else:
            self.html += content


class _TOC2HTMLHandler_hhc(xml.sax.handler.ContentHandler):
    def __init__(self, dressing, flags=[]):
        self.dressing = dressing
        self.flags = flags
        self.html = ""
        self.level = None
        self.onDeckAt = {} # <ul> content that is on-deck at a given level
        self.nodeAt = {} # <level> : <boolean>
        self.projectName = None
        # Stack of nodes to skip. The stack is started when a <node> has
        # a "flags" attribute that doesn't match given self.flags. All child
        # <node>s of a skipped <node> are also skipped.
        self.skipStack = []

    def startDocument(self):
        if self.dressing:
            self.add("""\
<!DOCTYPE HTML PUBLIC "-//IETF//DTD HTML//EN">
<HTML>
""")
        self.level = 0

    def endDocument(self):
        if self.dressing:
            self.add("\n</HTML>")

    def startElement(self, name, attrs):
        if name == "toc":
            self.projectName = attrs["name"]
            if self.dressing:
                self.add("""\
<HEAD>
<meta name="GENERATOR" content="toc.py">
<!-- Sitemap 1.0 -->
</HEAD><BODY>
<OBJECT type="text/site properties">
        <param name="Window Styles" value="0x801227">
        <param name="ImageType" value="Folder">
</OBJECT>
""")
            self.add("<UL>")
            self.level += 1
        elif name == "node":
            # Determine if this node should be skipped.
            if self.skipStack:
                self.skipStack.append(attrs["name"])
            elif self.flags and attrs.has_key("flags"):
                #XXX Warn or error out or allow it if it looks like
                #    commas (and perhaps other common separators) are
                #    being used here.
                nodeFlags = attrs["flags"].split()
                for nf in nodeFlags:
                    if nf in self.flags:
                        break
                else:
                    self.skipStack.append(attrs["name"])
            if not self.skipStack:
                # No skipping this node -- process it.
                if self.onDeckAt.get(self.level):
                    self.add(self.onDeckAt[self.level])
                    self.level += 1
                self.nodeAt[self.level] = 1
                self.add('\n<LI> <OBJECT type="text/sitemap">')
                self.level += 1
                self.add('\n    <param name="Local" value="%s">'
                         % attrs["link"])
                #XXX Might want to just s/"/'/g to not push it. HTMLHelp
                #    is brittle.
                self.add('\n    <param name="Name" value=%s>'
                         % saxutils.quoteattr(attrs["name"]))
                #self.add('\n</OBJECT> </LI>')
                self.add('\n</OBJECT>')
                self.onDeckAt[self.level] = '\n<UL>'

    def endElement(self, name):
        if name == "node":
            if self.skipStack:
                self.skipStack.pop()
            else:
                if self.nodeAt.get(self.level): # we need to close the <ul>
                    self.level -= 1
                    self.add('\n</UL>')
                self.level -= 1
        elif name == "toc":
            self.add("\n</UL>")
            if self.dressing:
                self.add("\n\n</BODY>")

    def add(self, content):
        """Add some HTML content."""
        if 0: #XXX for debugging
            sys.stdout.write(content)
        else:
            self.html += content


class _HTML2TOCParser_li(HTMLParser):
    """Parse an "li-sytle" HTML Table of Contents page and build TOC content.
    
    "li-style" basically means that the Table of Contents structure is
    represented something like this:
        <ul>
            <li><a href="LINK">NAME</a></li>
            <li><a href="LINK">NAME</a></li>
            <li><a href="LINK">NAME</a>
            </li>
        </ul>

    XXX: Should also be able to handle nodes that have text content but
    no link.

    TOC content is stored in "self.toc".
    """
    def __init__(self, htmlFileName, projectName, projectVersion, dressing=1,
                 prefix=None):
        HTMLParser.__init__(self)
        self.htmlFileName = htmlFileName
        self.projectName = projectName
        self.projectVersion = projectVersion
        self.dressing = dressing
        self.prefix = prefix
        if self.prefix is not None and self.prefix.endswith('/'):
            self.prefix = self.prefix[:-1] # drop trailing slash
        self.toc = ""
        self.stack = [None] # stack of tags that we care about: ul, li, a (ol?)
        # The current node. If not None, then it is currently being
        # parsed.
        self.node = None
        self.nodeOnDeck = None
        self.level = None
        self.indent = "  "
        self.baseHref = None

    def add(self, content):
        """Add some TOC content."""
        if 0: #XXX for debugging
            sys.stdout.write(content)
        else:
            self.toc += content

    def feed(self, data):
        self.level = 0
        if self.dressing:
            self.add("""\
<?xml version="1.0" encoding="UTF-8"?>
<toc name="%s" version="%s">
""" % (self.projectName, self.projectVersion))
        HTMLParser.feed(self, data)
        if self.dressing:
            self.add("\n\n</toc>\n")

    def handle_starttag(self, tag, attrs):
        if tag == "head":
            self.stack.append("head")
        elif tag == "body" and self.stack[-1] == "head":
            self.handle_endtag("head") # implicitly end head tag
        elif tag == "base" and self.stack[-1] == "head":
            for attrname, attrvalue in attrs:
                if attrname == "href":
                    self.baseHref = attrvalue
        elif tag == "ul":
            self.stack.append("ul")
        elif tag == "li":
            if self.stack[-1] == "li":
                # implicitly close the previous <li> tag
                self.handle_endtag("li")
            elif self.stack[-1] != "ul":
                raise TOCError("unexpected 'li' tag when 'ul' not at top of stack")
            if self.nodeOnDeck:
                name = self.nodeOnDeck["name"]
                name = ' '.join(name.split()) # normalize whitespace (no newlines)
                self.add('\n%s<node name=%s link=%s>'
                         % (self.indent*self.level,
                            saxutils.quoteattr(name),
                            saxutils.quoteattr(self.nodeOnDeck["link"])))
                self.level += 1
                self.nodeOnDeck = None
            self.stack.append("li")
        elif tag == "a" and self.stack[-1] == "li":
            self.stack.append("a")
            self.node = {}
            absLinkRe = re.compile("^(http|ftp|mailto|https):", re.I)
            for attrname, attrvalue in attrs:
                if attrname == "href":
                    link = attrvalue
                    if absLinkRe.search(link) or link.startswith('/'):
                        pass # leave this full/absolute link alone
                    elif self.baseHref is not None:
                        link = self.baseHref + '/' + link
                        log.debug("prefix BASE href to link: '%s'", link)
                    if absLinkRe.search(link) or link.startswith('/'):
                        pass # leave this full/absolute link alone
                    elif self.prefix is not None and not link.startswith(".."):
                        link = self.prefix + '/' + link
                        log.debug("prefix given 'prefix' to link: '%s'", link)
                    self.node["link"] = link
                    self.node["name"] = ""

    def handle_data(self, data):
        if self.node is not None:
            self.node["name"] += data

    def handle_entityref(self, entity):
        if self.node is not None:
            text = htmlentitydefs.entitydefs.get(entity)
            if text:
                self.node["name"] += text
            else:
                log.warn("do not know replacement text for '%s' HTML entity",
                         entity)

    def handle_endtag(self, tag):
        if tag == "head" and self.stack[-1] == "head":
            self.stack.pop()
        if tag == "a" and self.stack[-1] == "a":
            # Finish off parsing the current node.
            self.stack.pop()
            self.nodeOnDeck = self.node
            self.node = None
        elif tag == "li":
            if self.stack[-1] != "li":
                raise TOCError("unexpected </li> when 'li' not at top of "
                               "stack: stack=%s   node-on-deck=%r"
                               % (self.stack, self.nodeOnDeck))
            if self.nodeOnDeck:
                name = self.nodeOnDeck["name"]
                name = ' '.join(name.split()) # normalize whitespace (no newlines)
                self.add('\n%s<node name=%s link=%s/>'
                         % (self.indent*self.level,
                            saxutils.quoteattr(name),
                            saxutils.quoteattr(self.nodeOnDeck["link"])))
                self.nodeOnDeck = None
            else:
                self.level -= 1
                self.add("\n%s</node>" % (self.indent*self.level))
            self.stack.pop()
        elif tag == "ul":
            if self.stack[-1] == "li":
                # implicitly close the previous <li> tag
                self.handle_endtag("li")
            if self.stack[-1] != "ul":
                raise TOCError("unexpected </ul> when 'ul' not at top of "
                               "stack: stack=%s   node-on-deck=%r"
                               % (self.stack, self.nodeOnDeck))
            self.stack.pop()


#XXX This is still under development. There is no immediate need for this
#    format conversion because PureMessage's TOC (the only product currently
#    using this style) is not large and JenniferZ may just convert all
#    product TOCs to use the same style.
#class _HTML2TOCParser_h2_li(HTMLParser):
#    """Build TOC content from an "h2_li-sytle" HTML Table of Contents page.
#    
#    "h2_li-style" basically means that the Table of Contents structure is
#    represented something like this:
#        <h2>PureMessage User Guide</h2>
#        <ul>
#            <li><a href="main.html">Welcome to PureMessage</a></li>
#            <li><a href="pmx-setup.html">Installation Guide</a></li>
#            ...
#        </ul>
#
#    TOC content is stored in "self.toc".
#    """
#    def __init__(self, htmlFileName, projectName, projectVersion, dressing=1):
#        HTMLParser.__init__(self)
#        self.htmlFileName = htmlFileName
#        self.projectName = projectName
#        self.projectVersion = projectVersion
#        self.dressing = dressing
#        self.toc = ""
#        self.stack = [None] # stack of tags that we care about: ul, li, a (ol?)
#        # The current node. If not None, then it is currently being
#        # parsed.
#        self.node = None
#        self.nodeOnDeck = None
#        self.level = None
#        self.indent = "  "
#        self.baseHref = None
#    def add(self, content):
#        """Add some TOC content."""
#        if 1: #XXX for debugging
#            sys.stdout.write(content)
#        else:
#            self.toc += content
#    def feed(self, data):
#        self.level = 0
#        if self.dressing:
#            self.add("""\
#<?xml version="1.0" encoding="UTF-8"?>
#<toc name="%s" version="%s">
#""" % (self.projectName, self.projectVersion))
#        HTMLParser.feed(self, data)
#        if self.dressing:
#            self.add("\n\n</toc>\n")
#    def handle_starttag(self, tag, attrs):
#        if tag == "head":
#            self.stack.append("head")
#        elif tag == "body" and self.stack[-1] == "head":
#            self.handle_endtag("head") # implicitly end head tag
#        elif tag == "base" and self.stack[-1] == "head":
#            for attrname, attrvalue in attrs:
#                if attrname == "href":
#                    self.baseHref = attrvalue
#        elif tag == "h2":
#            self.stack.append("h2")
#            self.node = {"name": ""}
#        elif tag == "ul":
#            self.stack.append("ul")
#        elif tag == "li":
#            if self.stack[-1] == "li":
#                # implicitly close the previous <li> tag
#                self.handle_endtag("li")
#            elif self.stack[-1] != "ul":
#                raise TOCError("unexpected 'li' tag when 'ul' not at top of stack")
#            if self.nodeOnDeck:
#                if "link" in self.nodeOnDeck:
#                    self.add('\n%s<node name=%s link=%s>'
#                             % (self.indent*self.level,
#                                saxutils.quoteattr(self.nodeOnDeck["name"]),
#                                saxutils.quoteattr(self.nodeOnDeck["link"])))
#                else:
#                    self.add('\n%s<node name=%s>'
#                             % (self.indent*self.level,
#                                saxutils.quoteattr(self.nodeOnDeck["name"])))
#                self.level += 1
#                self.nodeOnDeck = None
#            self.stack.append("li")
#        elif tag == "a" and self.stack[-1] == "li":
#            self.stack.append("a")
#            if self.node is None:
#                self.node = {"name": ""}
#            for attrname, attrvalue in attrs:
#                if attrname == "href":
#                    link = attrvalue
#                    if (self.baseHref is not None
#                        and not link.startswith("http://")
#                        and not link.startswith("ftp://")
#                        and not link.startswith("/")):
#                        link = self.baseHref + '/' + link
#                    self.node["link"] = link
#    def handle_data(self, data):
#        if self.node is not None:
#            self.node["name"] += data
#    def handle_entityref(self, entity):
#        if self.node is not None:
#            text = htmlentitydefs.entitydefs.get(entity)
#            if text:
#                self.node["name"] += text
#            else:
#                log.warn("do not know replacement text for '%s' HTML entity",
#                         entity)
#    def handle_endtag(self, tag):
#        if tag == "head" and self.stack[-1] == "head":
#            self.stack.pop()
#        elif tag == "h2" and self.stack[-1] == "h2":
#            # Finish off parsing the current node.
#            self.stack.pop()
#            self.nodeOnDeck = self.node
#            self.node = None
#        elif tag == "a" and self.stack[-1] == "a":
#            # Finish off parsing the current node.
#            self.stack.pop()
#            self.nodeOnDeck = self.node
#            self.node = None
#        elif tag == "li":
#            if self.stack[-1] != "li":
#                raise TOCError("unexpected </li> when 'li' not at top of "
#                               "stack: stack=%s" % self.stack)
#            if self.nodeOnDeck:
#                if "link" in self.nodeOnDeck:
#                    self.add('\n%s<node name=%s link=%s/>'
#                             % (self.indent*self.level,
#                                saxutils.quoteattr(self.nodeOnDeck["name"]),
#                                saxutils.quoteattr(self.nodeOnDeck["link"])))
#                else:
#                    self.add('\n%s<node name=%s/>'
#                             % (self.indent*self.level,
#                                saxutils.quoteattr(self.nodeOnDeck["name"])))
#                self.nodeOnDeck = None
#            else:
#                self.level -= 1
#                self.add("\n%s</node>" % (self.indent*self.level))
#            self.stack.pop()
#        elif tag == "ul":
#            if self.stack[-1] != "ul":
#                raise TOCError("unexpected </ul> when 'ul' not at top of "
#                               "stack: stack=%s" % self.stack)
#            self.stack.pop()


class _HTML2TOCParser_hhc(HTMLParser):
    """Parse a .hhc file (used for .chm builds) and build TOC content.
    
    See "toc help styles" for more info on the .hhc "style".
    
    TOC content is stored in "self.toc".
    """
    def __init__(self, htmlFileName, projectName, projectVersion, dressing=1,
                 prefix=None):
        #XXX Could make projectName and projectVersion optional and
        #    try to parse them out of the hhc file.
        HTMLParser.__init__(self)
        self.htmlFileName = htmlFileName
        self.projectName = projectName
        self.projectVersion = projectVersion
        self.dressing = dressing
        self.prefix = prefix
        if self.prefix is not None and self.prefix.endswith('/'):
            self.prefix = self.prefix[:-1] # drop trailing slash
        self.toc = ""
        self.stack = [None]
        # The current node. If not None, then it is currently being parsed.
        self.node = None
        self.nodeOnDeck = None
        self.level = None
        self.indent = "  "

    def add(self, content):
        """Add some TOC content."""
        if 0: #XXX for debugging
            sys.stdout.write(content)
        else:
            self.toc += content

    def feed(self, data):
        self.level = -1
        if self.dressing:
            self.add("""\
<?xml version="1.0" encoding="UTF-8"?>
<toc name=%s version=%s>
""" % (saxutils.quoteattr(self.projectName),
       saxutils.quoteattr(self.projectVersion)))
        HTMLParser.feed(self, data)
        if self.dressing:
            self.add("\n\n</toc>\n")

    def handle_starttag(self, tag, attrs):
        if tag == "ul":
            self.stack.append("ul")
            if self.nodeOnDeck:
                self.add('\n%s<node name=%s link=%s>'
                         % (self.indent*self.level,
                            saxutils.quoteattr(self.nodeOnDeck["name"]),
                            saxutils.quoteattr(self.nodeOnDeck["link"])))
                self.nodeOnDeck = None
            self.level += 1
        elif tag == "li":
            if self.stack[-1] == "li":
                # implicitly close the previous <li> tag
                self.handle_endtag("li")
            if self.stack[-1] != "ul":
                raise TOCError("unexpected 'li' tag when 'ul' not at top of stack")
            if self.nodeOnDeck:
                self.add('\n%s<node name=%s link=%s/>'
                         % (self.indent*self.level,
                            saxutils.quoteattr(self.nodeOnDeck["name"]),
                            saxutils.quoteattr(self.nodeOnDeck["link"])))
                self.nodeOnDeck = None
            self.stack.append("li")
        elif tag == "object":
            if self.stack[-1] == "li":
                self.stack.append("object")
                self.node = {}
            else:
                # This might be a "merge" <object/>.
                self.stack.append("object")
        elif tag == "param" and self.stack[-1] == "object":
            # This:
            #   <param name="Local" value="mk:@MSITStore:ActivePython.chm::/UserGuide/install.html">
            # should yield this:
            #   self.node["link"] = "UserGuide/install.html"
            # while this:
            #   <param name="Name" value="Installation Guide for ActivePython">
            # should yield this:
            #   self.node["name"] = "Installation Guide for ActivePython"
            name, value = None, None
            for attrname, attrvalue in attrs:
                if   attrname == "name":  name  = attrvalue
                elif attrname == "value": value = attrvalue
            if name == "Local" and self.node is not None:
                self.node["link"] = value.split("::/", 1)[1]
                if self.prefix is not None:
                    self.node["link"] = self.prefix + '/' + self.node["link"]
            elif name == "Name" and self.node is not None:
                self.node["name"] = value
            elif name == "Merge":
                log.info("merging in '%s'" % value)
                self.add("\n\n%s<!-- Merged TOC from '%s' -->"\
                         % (self.indent*self.level, value))
                hhcBaseName = os.path.splitext(os.path.basename(value))[0]
                hhcFileName = os.path.join(os.path.dirname(self.htmlFileName),
                                           hhcBaseName, value)
                toc = html2toc(hhcFileName, style="hhc",
                               projectName=self.projectName,
                               projectVersion=self.projectVersion,
                               dressing=0,
                               prefix=hhcBaseName)
                self.add(toc)
            else:
                line, col = self.getpos()
                log.debug("%s: %s,%s: ignoring object '%s' param: ",
                          self.htmlFileName, line, col, name)

    def handle_endtag(self, tag):
        # Ignore <object> tags outside of <li>'s for now (c.f. start of
        # ActivePython-2_3::PyWin32.chm).
        if tag == "object" and self.stack[-1] == "object":
            # Finish off parsing the current node.
            self.stack.pop()
            self.nodeOnDeck = self.node
            self.node = None
        elif tag == "li":
            if self.stack[-1] != "li":
                raise TOCError("unexpected </li> when 'li' not at top of "
                               "stack: stack=%s" % self.stack)
            self.stack.pop()
        elif tag == "ul":
            if self.stack[-1] == "li":
                # implicitly close the previous <li> tag
                self.handle_endtag("li")
            if self.stack[-1] != "ul":
                raise TOCError("unexpected </ul> when 'ul' not at top of "
                               "stack: stack=%s" % self.stack)
            if self.nodeOnDeck:
                self.add('\n%s<node name=%s link=%s/>'
                         % (self.indent*self.level,
                            saxutils.quoteattr(self.nodeOnDeck["name"]),
                            saxutils.quoteattr(self.nodeOnDeck["link"])))
                self.nodeOnDeck = None
            self.level -= 1
            if self.level >= 0:
                self.add("\n%s</node>" % (self.indent*self.level))
            self.stack.pop()


class _TOC2ECHandler(xml.sax.handler.ContentHandler):
    """Convert a 'toc.xml' document to JS code of the form, e.g.:
    
        var tocTab = new Array();
        tocTab[0] = new Array("0", "<document title>", "<first link>");
        ...
        tocTab[21] = new Array("2.1", "Customizing the Appearance", "<link>");
        tocTab[22] = new Array("2.2", "Customizing the Debugger", "<link>");
        tocTab[23] = new Array("2.3", "Customizing the Editor", "<link>");
        tocTab[24] = new Array("2.3.1", "Customizing Editor Features", "<link>");
        tocTab[25] = new Array("2.3.1.1", "General Preferences", "<link>");
        ...
        var nCols = 4;

    where:
        <document title> is derived from the <toc>-element's "name" and
            "version" attributes. This can be overriden by passing in a
            specific title to the constructor.
        <first link> is the first non-empty <node> "link" attribute (because
            currently the toc.xml schema does not allow a "link" attribute
            on the leading <toc> element.

    Notes:
    - The E/C system will choke on the use of double-quotes in a node name.
      They are converted to single quotes here.

    This is part of the system that (I think) begins with this paper:
        http://www.d.umn.edu/ece/publications/handbook/Generate/OrigDoc.htm
        A Cross Browser Expanding and Collapsing Table of Contents Menu
    
    Some notes from the docs:
    - These are called: (<ordering string>, <heading text>, <anchor>)
      but we'll call them:  (<order>, <heading>, <anchor>)
    - The "ordering string" does not _have_ to be a dotted number.
    - The <heading text> is not supposed to have double quote marks in it.
      (I wonder if this is just a restriction of the generation code or
      if the user of the generated JS is so limited as well.
    - "nCols" defines the maximum number of hierarchical levels of the ToC.
    """
    def __init__(self, title=None, flags=[]):
        xml.sax.handler.ContentHandler.__init__(self)
        self.title = title
        self.flags = flags

    def startDocument(self):
        self.order = [0]  # '.'.join'ed to make <ordering string>'s
        self.toc = []  # list of (<order>, <heading>, <link>) 3-tuples
        self.onDeckAt = {} # <ul> content that is on-deck at a given level
        self.level = 0
        self.maxlevel = 0
        # When find first link in TOC, assign it to the top tocTab element
        # because the EC system uses this element as the default content
        # page to display.
        self._firstLink = None
        # Stack of nodes to skip. The stack is started when a <node> has
        # a "flags" attribute that doesn't match given self.flags. All child
        # <node>s of a skipped <node> are also skipped.
        self.skipStack = []

    def endDocument(self):
        # Generate self.js from the gathered data.
        js = "var tocTab = new Array();\n"
        for i in range(len(self.toc)):
            order, heading, anchor = self.toc[i]
            heading = heading.replace('"', "'") # see notes in class docstring
            js += 'tocTab[%d] = new Array("%s", "%s", "%s");\n'\
                  % (i, order, heading, anchor)
        js += "var nCols = %d;" % self.maxlevel
        self.js = js

    def startElement(self, name, attrs):
        #log.debug('toc2ec: start <%s name="%s">', name, attrs["name"])
        if name == "toc":
            if self.title is None:
                title = "%(name)s %(version)s" % attrs
            else:
                title = self.title
            order = '.'.join([str(i) for i in self.order])
            self.toc.append( (order, title, "") )
            self._firstLink = None
        elif name == "node":
            # Determine if this node should be skipped. (If skipStack is
            # non-empty at the end of this then this node is to be skipped.)
            if self.skipStack:
                self.skipStack.append(attrs["name"])
            elif self.flags and attrs.has_key("flags"):
                #XXX Warn or error out or allow it if it looks like
                #    commas (and perhaps other common separators) are
                #    being used here.
                nodeFlags = attrs["flags"].split()
                for nf in nodeFlags:
                    if nf in self.flags:
                        break
                else:
                    self.skipStack.append(attrs["name"])

            if not self.skipStack:
                self.order[-1] += 1
                self.maxlevel = max(self.maxlevel, len(self.order))
                order = '.'.join([str(i) for i in self.order])
                heading = attrs["name"]
                if attrs.has_key("link"):
                    anchor = attrs["link"]
                    if anchor and self._firstLink is None:
                        self._firstLink = anchor
                        firstOrder, firstHeading, firstLink = self.toc[0]
                        self.toc[0] = (firstOrder, firstHeading, self._firstLink)
                else:
                    anchor = "" #XXX Should I use the empty string or None/null?
                self.toc.append( (order, heading, anchor) )
                self.order.append(0)

    def endElement(self, name):
        if name == "node":
            if self.skipStack:
                self.skipStack.pop()
            else:
                del self.order[-1]
        elif name == "toc":
            pass


class _LinkChecker(xml.sax.handler.ContentHandler):
    """Check for link errors in a 'toc.xml' document.
    
    After processing the .errors attribute holds a list of any errors.

    Limitations:
        - HTML _anchors_ are not checked
        - http:// and ftp:// URLs are not checked
    """
    def __init__(self, baseDir):
        xml.sax.handler.ContentHandler.__init__(self)
        self.baseDir = baseDir

    def startDocument(self):
        self.errors = []

    def startElement(self, name, attrs):
        if name != "node":
            return
        link = attrs.get("link")
        if not link:
            return
        error = _checkOneLink(link, self.baseDir)
        if error:
            self.errors.append(error)

def _checkOneLink(link, baseDir):
    """Return an error string if the link is invalid, else return None."""
    if link.startswith("http://") or link.startswith("ftp://"):
        return None
    if os.path.isabs(link):
        path = link
    else:
        path = os.path.join(baseDir, link)
    path = os.path.normpath(path)
    if "#" in path:
        idx = path.rindex("#")
        path, anchor = path[:idx], path[idx+1:]
    else:
        anchor = None
    if not os.path.exists(path):
        return "'%s' does not exist" % path
    return None



#---- public interface

def toc2html(toc, style="li", dressing=1, flags=[]):
    """Convert the given 'toc.xml' file to an HTML file.
    
        "toc" is the toc file name
        "style" (optional) is an HTML style to generate (see
            'toc help styles'). The default style is "li".
        "dressing" (optional) is a boolean indicating if the surrounding
            document dressing (i.e. the <?xml...?> and <toc> tags) should
            be included or if only the code <node> content should be
            included. Defaults to true.
        "flags" (optional, default []) is a list of flags on which to
            filter processed <node>'s.

    Returns the HTML content.
    """
    style2handler = {
        "li": _TOC2HTMLHandler_li,
        #"h2_li": _TOC2HTMLHandler_h2_li,
        #"strong_br": _TOC2HTMLHandler_strong_br,
        "hhc": _TOC2HTMLHandler_hhc,
    }
    try:
        handlerClass = style2handler[style]
    except KeyError:
        raise TOCError("toc2html: unsupported HTML style: '%s'" % style)
    handler = handlerClass(dressing, flags)
    xml.sax.parse(toc, handler)
    return handler.html
    

def html2toc(htmlFileName, style="li", projectName=None, projectVersion=None,
             dressing=1, prefix=None):
    """Convert the given HTML Table of Contents file to a TOC content.
    
        "htmlFileName" is the HTML file name
        "style" (optional) is an HTML style to expect (see 'toc help styles').
            If not specified the "li" style is presumed.
        "projectName" is the name to use for the <toc/> element's "name"
            attribute
        "projectVersion" is the name to use for the <toc/> element's
            "version" attribute
        "dressing" (optional) is a boolean indicating if the surrounding
            document dressing (i.e. the <?xml...?> and <toc> tags) should
            be included or if only the code <node> content should be
            included. Defaults to true.
        "prefix" (optional) is a path with which to prefix relative links in
            the generated toc <node>'s. By default there is no prefix.

    The TOC XML Schema is defined here:
        http://specs.activestate.com/ASPN_Doc_Import/doc_import.html#toc-schema
    Returns the TOC content.
    """
    log.debug("html2toc(htmlFileName='%s', style='%s', projectName='%s', "
              "projectVersion='%s', dressing=%s, prefix=%s)", htmlFileName,
              style, projectName, projectVersion, dressing, prefix)
    fin = open(htmlFileName, 'r')
    try:
        html = fin.read()
    finally:
        fin.close()
    
    style2parser = {
        "li": _HTML2TOCParser_li,
        "hhc": _HTML2TOCParser_hhc,
        #"h2_li": _HTML2TOCParser_h2_li,
        #"strong_br": _HTML2TOCParser_strong_br,
    }
    try:
        parserClass = style2parser[style]
    except KeyError:
        raise TOCError("html2toc: unsupported HTML style: '%s'" % style)

    parser = parserClass(htmlFileName, projectName, projectVersion, dressing,
                         prefix)
    parser.feed(html)
    toc = parser.toc
    return toc


def toc2ec(toc, title=None, flags=[]):
    """Convert the given 'toc.xml' file to a JavaScript Expand/Collapse TOC
    used by the new ActiveHelp system.
    
        "toc" is the toc file name
        "title" (optional) is a heading to use for the top EC TOC entry. By
            default this is derived from the <toc>-element's "name" and
            "version" attributes.
        "flags" (optional, default []) is a list of flags on which to
            filter processed <node>'s.

    Convert the given 'toc.xml' to a JavaScript snippet for the
    Expand/Collapse system that JennZ (of ActiveState docs) is using for the
    new ActiveHelp system.
    """
    handler = _TOC2ECHandler(title=title, flags=flags)
    xml.sax.parse(toc, handler)
    return handler.js


def linkcheck(toc, baseDir=None):
    """Check the given toc.xml file for link errors.
    
        "toc" is a path to the toc.xml file.
        "baseDir" (optional) is a base directory from which to interpret
            relative links. By default the directory of the toc file is used.
    
    Returns a list of invalid links.
    """
    if baseDir is None:
        baseDir = os.path.dirname(toc) or os.curdir
    handler = _LinkChecker(baseDir)
    xml.sax.parse(toc, handler)
    return handler.errors


class TOCShell(_ListCmd):
    """
    toc -- work with ActiveState/ASPN/ActiveHelp Tables of Contents (TOC) 

    Usage:
        toc [<options>...] <command> [<args...>]

    Options:
        -h, --help          Print this help and exit.
        -v, --verbose       More verbose output
        -V, --version       Print this script's version and exit.
        
    See: http://specs.activestate.com/ASPN_Doc_Import/
    Importing ActiveState product documentation in ASPN is currently a pain.
    This script is part of a proposed ASPN Doc Import system to simplify
    this. 'toc' provides some useful functionality for working with toc.xml
    files.

    Help:
        toc help                Print this help and exit.
        toc help <command>      Print help on the given command.
        toc help styles         Specific help on supported HTML "styles"

    Commands:
        toc2html ...        convert the given 'toc.xml' to an HTML file
        html2toc ...        convert the given HTML Table of Contents file
                            to a 'toc.xml'
        toc2hhc ...         shortcut for 'toc toc2html --style=hhc ...'
        hhc2toc ...         shortcut for 'toc html2toc --style=hhc ...'
        toc2ec ...          convert the given 'toc.xml' to Expand/Collapse
                            JavaScript code used by ActiveHelp system.
        linkcheck ...       check the given 'toc.xml' for link errors
    """
    name = "toc"

    def emptyline(self):
        self.do_help(["help"])

    def help_usage(self):
        print __doc__
        sys.stdout.flush()

    def help_styles(self):
        """
    HTML Styles supported by 'toc':
    
    'toc' understands a few different styles of representing
    Table of Contents structure in HTML. The conversion commands
    (e.g. toc2html, html2toc) generally have a --style option to
    specify the HTML style to work with. The follow are the supported
    styles:
    
        Style       Description
        -----       -----------
        li          Nested <ul> elements with one <li> item per TOC node.
                    (This is the preferred style.)
        hhc         the "HTML" format used for .hhc files when making
                    .chm (Window compiled help) files
        h2_li*      <h2> elements denote header nodes and <li> elements
                    denote sub-nodes.
        strong_br*  <strong> elements denote section header nodes and
                    <br> elements delineate new nodes.

        (*) not yet implemented

    Example of the "li" style:
        ...
        <ul>
            <li><a href="fruit.html">Fruit I like</a>
              <ul>
                <li><a href="apples.html">Apples</a></li>
                <li><a href="pears.html">Pears</a></li>
              </ul>
            </li>
        </ul>
        ...

    Example of "hhc" style. Note the specific (lack of) indentation. This
    is done because the Windows HTML Help compiler (hhc.exe) is very
    sensitive to indentation of the .hhc file (XXX actually not too sure
    of this):
        ...
        <UL>
        <LI> <OBJECT type="text/sitemap">
            <param name="Local" value="fruit.html">
            <param name="Name" value="Fruit I like">
        </OBJECT>
        <UL>
        <LI> <OBJECT type="text/sitemap">
            <param name="Local" value="apples.html">
            <param name="Name" value="Apples">
        </OBJECT>
        <LI> <OBJECT type="text/sitemap">
            <param name="Local" value="pears.html">
            <param name="Name" value="Pears">
        </OBJECT>
        </UL>
        ...

    Example of "h2_li" style:
        ...
        <h2><a href="fruit.html">Fruit I like</a></h2>
        <ul>
            <li><a href="apples.html">Apples</a></li>
            <li><a href="pears.html">Pears</a></li>
        </ul>
        ...

    Example of "strong_br" style:
        ...
        <strong><a href="fruit.html">Fruit I like</a></strong><br>
        <a href="apples.html">Apples</a><br>
        <a href="pears.html">Pears</a><br>
        ...

    XXX:TODO: Support nodes not having a link.
        """
        print self.help_styles.__doc__

    def do_toc2html(self, argv):
        """
    toc2html -- convert the given 'toc.xml' to HTML

    toc toc2html [<options>...] <toc_file>
    
        Options:
            -o <filename>   specify a file to which to write the HTML, by
                            default the HTML is written to stdout
            -b, --browse    open the HTML file in your browser
            -s <style>, --style=<style>
                            specify a specific HTML style to generate
                            (see "toc help styles"); default style is "li"
            --without-dressing
                            Do not include header and footer HTML dressing
                            (i.e. <html>...<body> and </body>... stuff) in
                            the generated HTML content. This is useful for
                            building up an HTML file _partially_ from
                            the table of contents information.
            -f|--flags <flags>
                            Filter the input toc.xml file with the given
                            flags. Multiple flags can be specified by
                            separating with a comma, or this option can be
                            specified more than once.
    
        <toc_file> is a path to a 'toc.xml' file.

        [Note for the 'li' style only:] The "class" attributes on
        individual <node> elements are carried over as "class"
        attributes on the corresponding HTML <li> element. This
        mechanism can be used to apply specific style to parts of the
        Table of Contents.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "ho:bs:f:",
                ["help", "browse", "style=", "without-dressing", "flags="])
        except getopt.GetoptError, msg:
            log.error("%s. Your invocation was: %s", msg, argv)
            log.error("Try 'toc help toc2html'.")
            return 1
        outFileName = None
        browse = 0
        style = "li"
        dressing = 1
        flags = []
        for opt, optarg in optlist:
            if opt in ("-h", "--help"):
                print self.do_toc2html.__doc__
                return 0
            elif opt in ("-o",):
                outFileName = optarg
            elif opt in ("-b", "--browse"):
                browse = 1
            elif opt in ("-s", "--style"):
                style = optarg
            elif opt == "--without-dressing":
                dressing = 0
            elif opt in ("-f", "--flags"):
                flags += [f.strip() for f in optarg.split(",")]

        # Process arguments.
        if len(args) != 1:
            log.error("toc2html: incorrect number of arguments: %s", args)
            log.error("toc2html: try 'toc help toc2html'")
            return 1
        tocFileName = args[0]

        html = toc2html(tocFileName, style=style, dressing=dressing,
                        flags=flags)
        
        if browse and outFileName is None:
            outFileName = tempfile.mktemp()+".html"

        if outFileName:
            fout = open(outFileName, 'w')
            try:
                fout.write(html)
            finally:
                fout.close()
        else:
            print html

        if browse:
            webbrowser.open_new(outFileName)

    def do_html2toc(self, argv):
        """
    html2toc -- convert the given HTML Table of Contents file to a 'toc.xml'

    toc html2toc [<options>...] <html_file> <product_name> <product_version>
    
        Options:
            -o <filename>   specify an output filename, by
                            default output is written to stdout
            -s <style>, --style=<style>
                            specify a specific HTML style to expect
                            (see "toc help styles"); default style is "li"
            --without-dressing
                            Do not include header and footer TOC dressing
                            (i.e. <?xml...?> and <toc> tags) in the generated
                            TOC content.
            --prefix <prefix>
                            prefix links with the given path
    
        <html_file> is a path to an HTML Table of Content file.
        <project_name> is the value to use for the <toc/> element's
            "name" attribute
        <project_version> is the value to use for the <toc/> element's
            "version" attribute
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "ho:s:",
                ["help", "style=", "without-dressing", "prefix="])
        except getopt.GetoptError, msg:
            log.error("%s. Your invocation was: %s", msg, argv)
            log.error("Try 'toc help html2toc'.")
            return 1
        outFileName = None
        style = "li"
        prefix = None
        dressing = 1
        for opt, optarg in optlist:
            if opt in ("-h", "--help"):
                print self.do_html2toc.__doc__
                return 0
            elif opt in ("-o",):
                outFileName = optarg
            elif opt in ("-s", "--style"):
                style = optarg
            elif opt in ("--without-dressing",):
                dressing = 0
            elif opt in ("--prefix",):
                prefix = optarg

        # Process arguments.
        if len(args) != 3:
            log.error("html2toc: incorrect number of arguments: %s", args)
            log.error("html2toc: try 'toc help html2toc'")
            return 1
        htmlFileName, projectName, projectVersion = args

        toc = html2toc(htmlFileName, style=style, projectName=projectName,
                       projectVersion=projectVersion, dressing=dressing,
                       prefix=prefix)
        
        if outFileName:
            fout = open(outFileName, 'w')
            try:
                fout.write(toc)
            finally:
                fout.close()
        else:
            print toc

    def do_toc2hhc(self, argv):
        """
    toc2hhc -- convert the given 'toc.xml' to HTML for viewing

    toc toc2hhc [<options>...] <toc_file>
    
        Options:
            -o <filename>   specify a .hhc to which to write, by
                            default the HHC content is written to stdout
            -b, --browse    open the HTML file in your browser
            -f|--flags <flags>
                            Filter the input toc.xml file with the given
                            flags. Multiple flags can be specified by
                            separating with a comma, or this option can be
                            specified more than once.
    
        <toc_file> is a path to a 'toc.xml' file.

        This is mainly useful for debugging/playing with a 'toc.html' file.
        This command is a shortcut for 'toc toc2html --style=hhc ...'.
        """
        newArgv = ['toc2html', '--style=hhc'] + argv[1:]
        return self.onecmd(newArgv)

    def do_hhc2toc(self, argv):
        """
    hhc2toc -- convert the given .hhc file to a 'toc.xml'

    toc html2toc [<options>...] <hhc_file> <product_name> <product_version>
    
        Options:
            -o <filename>   specify an output filename, by
                            default output is written to stdout
            --without-dressing
                            Do not include header and footer TOC dressing
                            (i.e. <?xml...?> and <toc> tags) in the generated
                            TOC content.
            --prefix <prefix>
                            prefix links with the given path
    
        <hhc_file> is a path to the .hhc file to process.
        <project_name> is the value to use for the <toc/> element's
            "name" attribute
        <project_version> is the value to use for the <toc/> element's
            "version" attribute
        
        This command is a shortcut for 'toc html2toc --style=hhc ...'.
        """
        newArgv = ['html2toc', '--style=hhc'] + argv[1:]
        return self.onecmd(newArgv)

    def do_toc2ec(self, argv):
        """
    toc2ec -- convert the given 'toc.xml' to Expand/Collapse JavaScript TOC
              used by the ActiveHelp system

    toc toc2ec [<options>...] <toc_file>
    
        Options:
            -o <filename>   specify a file to which to write the JS; by
                            default the JS is written to stdout
            -n|--no-title   Do not include a title derived from the <toc>
                            name and version.
            -f|--flags <flags>
                            Filter the input toc.xml file with the given
                            flags. Multiple flags can be specified by
                            separating with a comma, or this option can be
                            specified more than once.
    
        <toc_file> is a path to a 'toc.xml' file.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "ho:nf:",
                                          ["help", "no-title", "flags="])
        except getopt.GetoptError, msg:
            log.error("%s. Your invocation was: %s", msg, argv)
            log.error("Try 'toc help toc2ec'.")
            return 1
        outFileName = None
        title = None
        flags = []
        for opt, optarg in optlist:
            if opt in ("-h", "--help"):
                print self.do_toc2ec.__doc__
                return 0
            elif opt in ("-o",):
                outFileName = optarg
            elif opt in ("-n", "--no-title"):
                title = ""
            elif opt in ("-f", "--flags"):
                flags += [f.strip() for f in optarg.split(",")]

        # Process arguments.
        if len(args) != 1:
            log.error("toc2ec: incorrect number of arguments: %s", args)
            log.error("toc2ec: try 'toc help toc2ec'")
            return 1
        tocFileName = args[0]

        js = toc2ec(tocFileName, title=title, flags=flags)
        
        if outFileName:
            fout = open(outFileName, 'w')
            try:
                fout.write(js)
            finally:
                fout.close()
        else:
            print js

    def do_linkcheck(self, argv):
        """
    linkcheck -- check the links in the given 'toc.xml'

    toc linkcheck [<options>...] <toc_file>
    
        Options:
            -d <basedir>    Specify a base directory from which to interpret
                            relative links. By default the dir of <toc_file>
                            is used.
    
        <toc_file> is a path to a 'toc.xml' file.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "hd:", ["help"])
        except getopt.GetoptError, msg:
            log.error("%s. Your invocation was: %s", msg, argv)
            log.error("Try 'toc help linkcheck'.")
            return 1
        baseDir = None
        for opt, optarg in optlist:
            if opt in ("-h", "--help"):
                print self.do_linkcheck.__doc__
                return 0
            elif opt in ("-d",):
                baseDir = optarg

        # Process arguments.
        if len(args) != 1:
            log.error("linkcheck: incorrect number of arguments: %s", args)
            log.error("linkcheck: try 'toc help linkcheck'")
            return 1
        tocFileName = args[0]

        errors = linkcheck(tocFileName, baseDir=baseDir)
        if errors:
            log.error("link errors in '%s':\n  %s", tocFileName,
                      "\n  ".join(errors))

        return len(errors)

    def do_generate_schemas(self, argv):
        """
    generate_schemas -- Re-generate the DTD and XML Schema schema from the
                        master 'toc.rng' Relax NG schema

    toc generate_schemas

        This command is a convenience command for TrentM. It makes assumptions
        about the local system (java installed, trang installed in a
        specific location).
        """
        javaLib = os.path.join(os.environ["HOME"], "lib-java")
        trangJar = os.path.join(javaLib, "trang.jar")
        cmds = [
            "p4 edit toc.dtd toc.xsd toc.rnc",
            "java -jar %s toc.rng toc.dtd" % trangJar,
            "java -jar %s toc.rng toc.xsd" % trangJar,
            "java -jar %s toc.rng toc.rnc" % trangJar,
            "p4 revert -a toc.dtd toc.xsd toc.rnc",
        ]
        for cmd in cmds:
            log.info("running '%s'", cmd)
            retval = os.system(cmd)
            if retval:
                raise TOCError("error running '%s'" % cmd)


#---- mainline

def main(argv):
    try:
        optlist, args = getopt.getopt(argv[1:], "hVv",
            ["help", "version", "verbose"])
    except getopt.GetoptError, msg:
        log.error("%s. Your invocation was: %s", msg, argv)
        log.error("Try 'toc --help'.")
        return 1
    for opt, optarg in optlist:
        if opt in ("-h", "--help"):
            print TOCShell.__doc__
            return 0
        elif opt in ("-V", "--version"):
            print "toc %s" % '.'.join([str(i) for i in _version_])
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(Logger.DEBUG)

    shell = TOCShell()

    try:
        return shell.onecmd(args)
    except Exception, ex:
        msg = str(ex)
        if not log.isDebugEnabled():
            msg += " (run in verbose mode, -v|--verbose, for more info)"
        log.error(msg)
        if log.isDebugEnabled():
            import traceback
            traceback.print_exception(*sys.exc_info())
        return 1


if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0])
    sys.exit( main(sys.argv) )


