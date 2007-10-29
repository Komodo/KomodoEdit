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

#******************************************************************
#XXX not done and not being used
#    Paul and Adam and Audrey are working on this problem (for the Komodo docs
#    at least). Perl and Python doc handling is still up in the air.
#******************************************************************

"""
    "Frame TOC and Index HTML" to "Komodo Help Resource" converter

    This converter takes one HTML table of contents file and one HTML
    index files created by FrameMaker and converts them to Komodo Help
    Resource .toc and .idx files.

    Usage:
        python frame2khr.py [options] \\
            <frame-TOC-infile> <frame-index-infile> \\
            <khr-TOC-outfile> <khr-index-outfile>

    Options:
        -h, --help          show this help
        -v, --verbose       verbose output
"""

import sys, os, getopt, re, cmd
import xml.sax, xml.sax.expatreader



#---- globals

verbosity = 0


#---- exceptions

class Frame2KhrError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg



#---- output control

class FormattedOutput:
    """A replacement for sys.stdout that provides some useful formatting.
    Features: word wrap, line prefixing
    Interface: write()
    Usage:
        out = FormattedOutput()
        out.write("blah")
    """
    def __init__(self, rightMargin=75, prefix=''):
        self.rightMargin = rightMargin
        self.prefix = prefix
        self.content = ''

    TT_WS, TT_NEWLINE, TT_WORD = range(3) # token types
    WHITESPACE = ' \t\r\f\v'  # excluding '\n' on purpose
    def parse(self, text):
        """return a list of tuples (TOKEN_TYPE, <token>)"""
        tokens = []
        i = 0
        while i < len(text):
            ch = text[i]
            if ch in ['\n']:
                tokens.append((self.TT_NEWLINE, ch))
                i = i + 1
            elif ch in self.WHITESPACE:
                spaces = ''
                while i < len(text) and text[i] in self.WHITESPACE:
                    spaces = spaces + text[i]
                    i = i + 1
                tokens.append((self.TT_WS, spaces))
            else:
                word = ''
                while i < len(text) and text[i] not in self.WHITESPACE+'\n':
                    word = word + text[i]
                    i = i + 1
                tokens.append((self.TT_WORD, word))
        return tokens
  
    def wipeContent(self):
        """clear the current line (content)"""
        self.content = ''

    def writeLine(self):
        # the other content has already been written in self.add()
        sys.__stdout__.write('\n')
        self.wipeContent()

    def spaceLeft(self):
        return self.rightMargin - len(self.prefix + self.content)

    def add(self, ttype, token):
        """add a token to the current line content"""
        if not token:
            pass
        else:
            spaceLeft = self.spaceLeft()
            toadd = ''
            if ttype == self.TT_WS and len(token) > spaceLeft:
                # drop any whitespace beyond the right margin
                # tabs are evil, they are not handled gracefully here
                toadd = token[:spaceLeft]
            else:
                toadd = token
            # now have to write out the token and store it to the
            # current line (token)
            if not self.content:
                sys.__stdout__.write(self.prefix)
            sys.__stdout__.write(toadd)
            self.content = self.content + toadd

    def write(self, text):
        #sys.stderr.write('XXX write text:%s\n' % repr(text))
        tokens = self.parse(text)
        for ttype, token in tokens:
            #print 'XXX token:', ttype, repr(token)
            if ttype == self.TT_NEWLINE:
                self.writeLine()
            elif ttype == self.TT_WS:
                self.add(ttype, token)
            elif ttype == self.TT_WORD:
                #print 'XXX word:%s content:%s spaceLeft:%d' % (repr(token), repr(self.content), self.spaceLeft())
                if len(token) > self.spaceLeft():
                    #print 'XXX causes overflow'
                    if len(token) > self.rightMargin - len(self.prefix):
                        #print 'XXX break up word'
                        while token:
                            spaceLeft = self.spaceLeft()
                            piece, token = token[:spaceLeft], token[spaceLeft:]
                            #print 'XXX pieces:', repr(piece), repr(token)
                            self.add(ttype, piece)
                            if token:
                                self.writeLine()
                    else:
                        self.writeLine()
                        self.add(ttype, token)
                else:
                    self.add(ttype, token)

class MarkedUpOutput(FormattedOutput):
    """A replacement for sys.stdout that provides some useful formatting.
    Features: word wrap, line prefixing, 
    Interface: write(), {start|end}{Group|Item|ErrorItem}()
    Usage:
        out = MarkedUpOutput()
        out.startGroup()
        out.startErrorItem()
        out.write("this is an error")
        out.endErrorItem()
        out.startItem()
        out.write("this is just some text")
        out.endItem()
        out.endGroup()
    """
    def __init__(self, *args, **kwargs):
        FormattedOutput.__init__(self, *args, **kwargs)
        self.groupDepth = 0
        self.itemDepth = 0
        self._bullet = ''

    # understood types of markup
    MT_START_GROUP, MT_END_GROUP,\
        MT_START_ITEM, MT_END_ITEM,\
        MT_START_ERROR_ITEM, MT_END_ERROR_ITEM = range(6)
    def startGroup(self): self.markup(self.MT_START_GROUP)
    def endGroup(self): self.markup(self.MT_END_GROUP)
    def startItem(self): self.markup(self.MT_START_ITEM)
    def endItem(self): self.markup(self.MT_END_ITEM)
    def startErrorItem(self): self.markup(self.MT_START_ERROR_ITEM)
    def endErrorItem(self): self.markup(self.MT_END_ERROR_ITEM)

    def markup(self, mark):
        if mark == self.MT_START_GROUP:
            if self.content:
                self.writeLine()
            self.groupDepth = self.groupDepth + 1
            self.write(self.groupStartSeparator())
            self.prefix = '  ' + self.prefix
        elif mark == self.MT_END_GROUP:
            if self.content:
                self.writeLine()
            self.write(self.groupEndSeparator())
            self.prefix = self.prefix[2:]
            self.groupDepth = self.groupDepth - 1
        elif mark == self.MT_START_ITEM:
            if self.content:
                self.writeLine()
            self.itemDepth = self.itemDepth + 1
            self.write(self.itemStartSeparator())
            self.prefix = self.prefix + self.bullet()
        elif mark == self.MT_END_ITEM:
            if self.content:
                self.writeLine()
            self.write(self.itemEndSeparator())
            self.prefix = self.prefix[:len(self.prefix)-len(self.bullet())]
            self.itemDepth = self.itemDepth - 1
        elif mark == self.MT_START_ERROR_ITEM:
            if self.content:
                self.writeLine()
            self.prefix = self.prefix + '*** '
        elif mark == self.MT_END_ERROR_ITEM:
            if self.content:
                self.writeLine()
            self.prefix = self.prefix[:len(self.prefix)-len('*** ')]

    def bullet(self):
        bullets = ['o ', '- ']
        depth = max(0, self.itemDepth-1)
        if depth >= len(bullets):
            return bullets[len(bullets)-1]
        else:
            return bullets[depth]

    def groupStartSeparator(self):
        seps = [
            '='*(self.rightMargin - len(self.prefix)) + '\n',
            '-'*(self.rightMargin - len(self.prefix)) + '\n',
        ]
        depth = max(0, self.groupDepth-1)
        if depth >= len(seps):
            return seps[len(seps)-1]
        else:
            return seps[depth]

    def groupEndSeparator(self):
        seps = ['\n\n', '\n']
        depth = max(0, self.groupDepth-1)
        if depth >= len(seps):
            return seps[len(seps)-1]
        else:
            return seps[depth]

    def itemStartSeparator(self):
        return ''
    
    def itemEndSeparator(self):
        seps = ['\n', '']
        depth = max(0, self.itemDepth-1)
        if depth >= len(seps):
            return seps[len(seps)-1]
        else:
            return seps[depth]
    
    def writeLine(self):
        FormattedOutput.writeLine(self)
        # ensures that the bullets are blanked out after the first line
        self.prefix = ' '*len(self.prefix)

out = MarkedUpOutput()



#---- an augmented command shell

class CmdError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg

class AugmentedListCmd(cmd.Cmd):
    """Better help reporting (Augmented) and pass args lists (List).
   
    "Augmented" part:
        Better std do_help() implementation that uses specially formatted
        method doc strings (see comments below for this formatting). "do_*"
        commands without doc strings do not show up.
   
    "List" part:
        Modify the std Cmd class to pass arg lists instead of command lines.
        This seems more appropriate for integration with sys.argv which handles
        the proper parsing of the command line arguments (particularly handling
        of quoting of args with spaces). It also allows Python function specs
        to be used to greater effect.

        Limitations:
            The cmdloop() stuff is not implemented because I don't use it so
            have not ported and tested it.
    """
    nohelp = "*** %s: No help for command %s."
    name = "AugmentedListCmd"
    
    def cmdloop(self, intro=None):
        raise "The cmdloop stuff is not yet implemented for AugmentedListCmd."

    def onecmd(self, args):
        if not args:
            return self.emptyline()
        elif args[0] == '?':
            args = ["help"] + args[1:]
        elif args[0][0] == '?':
            args = ["help"] + [args[0][1:]] + args[1:]
        elif args[0] == '!':
            if hasattr(self, 'do_shell'):
                args = ['shell'] + args[1:]
            else:
                return self.default(args)
        elif args[0][0] == '!':
            if hasattr(self, 'do_shell'):
                args = ['shell'] + [args[0][1:]] + args[1:]
            else:
                return self.default(args)
        self.lastcmd = args
        cmd, args = args[0], args[1:]
        try:
            func = getattr(self, 'do_' + cmd)
        except AttributeError:
            return self.default([cmd] + args)
        try:
            return func(*args)
        except (TypeError, CmdError), err:
            out.write("*** %s %s: %s\n" % (self.name, cmd, str(err)))
            out.write("(Try `%s help %s'.)\n" % (self.name, cmd))
            usage = self.doc_usage(func.__doc__)
            if usage:
                out.write("Usage:\n")
                for line in usage:
                    out.write("\t" + line + "\n")
            # re-raise the error if being verbose
            global verbosity
            if verbosity:
                out.write("\n")
                import traceback
                traceback.print_exception(*sys.exc_info())
                


    def default(self, args):
        out.write("%s: unknown syntax: %s (Try `%s help'.)\n" %\
            (self.name, " ".join(args), self.name))

    def _helponecmd(self, cmdName):
        """show help for the given command"""
        try:
            func = getattr(self, 'help_' + cmdName)
        except AttributeError:
            try:
                doc = getattr(self, 'do_' + cmdName).__doc__
                synopsis = self.doc_synopsis(doc)
                usageLines = self.doc_usage(doc)
                descLines = self.doc_description(doc)
                out.write("\n")
                out.write("    %s -- %s\n" % (cmdName, synopsis))
                if usageLines:
                    out.write("\n")
                    for line in usageLines:
                        out.write("    %s\n" % line)
                if descLines:
                    out.write("\n")
                    for line in descLines:
                        out.write("    %s\n" % line)
                return
            except:
                pass
            out.write(self.nohelp % (self.name, repr(cmdName)) + "\n")
            return
        func()

    def do_help(self, cmdNameStr=None):
        if cmdNameStr:
            for cmdName in cmdNameStr.split():
                self._helponecmd(cmdName)
        else:
            # show the Cmd class' docstring
            if self.__class__.__doc__ is not None:
                out.write(self.__class__.__doc__ + "\n")

    def printcmds(self):
        """print a single help line for each documented command"""
        # Inheritance says we have to look in class and
        # base classes; order is not important.
        cmds = []
        classes = [self.__class__]
        while classes:
            aclass = classes[0]
            if aclass.__bases__:
                classes = classes + list(aclass.__bases__)
            cmds = cmds + dir(aclass)
            del classes[0]
        cmds.sort()
        # There can be duplicates if routines overridden
        prevcmd = ''
        for cmd in cmds:
            if cmd[:3] == 'do_':
                if cmd == prevcmd:
                    continue
                prevcmd = cmd
                doc = getattr(self, cmd).__doc__
                # only show command if it has a doc string
                if doc:
                    synopsis = self.doc_synopsis(doc)
                    out.write("        %s %s%s%s\n" %\
                        (self.name, cmd[3:], ' '*(15-len(cmd[3:])), synopsis))

    def help_commands(self):
        out.write("\n")
        out.write("    %s commands:\n" % self.name)
        out.write("\n")
        self.printcmds()
        out.write("\n")

    def emptyline(self):
        pass

    def subcmd(self, shell, command):
        if command:
            shell.onecmd(command)
        else:
            shell.cmdloop()

    # AugmentedCmd "Standard" formatted doc string:
    #    """this is the synopsis, it can only be one line
    #
    #    this is the usage string, can be
    #    more than one line, this first should NOT be indented
    #
    #    this is the description string
    #    it can be
    #    as many lines as you want
    #           and have the desired indentation
    #    please terminate the docstring on a newline
    #    """
    def doc_synopsis(self, doc):
        """extract the synopsis from a standard formatted command docstring"""
        if not doc:
            return None
        else:
            return doc.split('\n')[0].strip()

    def doc_usage(self, doc):
        """Extract the usage from a standard formatted command docstring."""
        if not doc:
            return None
        docLines = doc.split('\n')
        if len(docLines) < 3:
            return None
        else:
            usageLines = []
            allWhitespaceRe = re.compile('^\s*$')
            for line in docLines[2:]:
                if allWhitespaceRe.search(line):
                    break
                usageLines.append(line.strip())
            return usageLines

    def doc_indentation(self, doc):
        """Returns the indentation for the docstring.
        The first usage line is used to determine this.
        """
        docLines = doc.split('\n')
        if len(docLines) < 3:
            return None
        else:
            allWhitespaceRe = re.compile('^\s*$')
            for line in docLines[2:]:
                if allWhitespaceRe.search(line):
                    return None
                else:
                    return len(line) - len(line.lstrip())

    def doc_description(self, doc):
        """extract the description from a std formatted command docstring"""
        docLines = doc.split('\n')
        if len(docLines) < 5:
            return None
        else:
            descLines = []
            indentation = self.doc_indentation(doc)
            for line in docLines[4:]:
                descLines.append(line[indentation:])
            return descLines


#---- other general helper stuff


class FrameTocParser(xml.sax.handler.ContentHandler):
    def __init__(self):
        pass

    def startElement(self, name, attrs):
        global verbosity
        if verbosity:
            out.write("startElement: %s %s" % (name, attrs))

    def endElement(self, name):
        global verbosity
        if verbosity:
            out.write("startElement: %s %s" % (name, attrs))



#---- script mainline

if __name__ == '__main__':
    # process options
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'vh',
            ['verbose', 'help'])
    except getopt.GetoptError, msg:
        out.startErrorItem()
        out.write("%s: error: invalid options: %s\n" % (sys.argv[0], msg))
        out.endErrorItem()
        out.write(sys.modules["__main__"].__doc__)
        sys.exit(1)
    for opt,optarg in optlist:
        if opt in ('-v', '--verbose'):
            verbosity = 1
        elif opt in ('-h', '--help'):
            out.write(sys.modules["__main__"].__doc__)
            sys.exit(0)

    # process arguments
    try:
        frameTocFileName, frameIndexFileName, khrTocFileName,\
            khrIndexFileName = args
    except ValueError:
        out.startErrorItem()
        out.write("%s: error: incorrect number of arguments: %s\n" % (sys.argv[0], args))
        out.endErrorItem()
        out.write(sys.modules["__main__"].__doc__)
        sys.exit(1)
    out.write("""
Will do the following conversion:
                      | FrameMaker -> Komodo Help Resource
  --------------------|--------------------------------------
  Table of Contents   | %s -> %s
  Index               | %s -> %s
""" % (frameTocFileName, khrTocFileName, frameIndexFileName, khrIndexFileName))

    # parse the FrameMaker table of contents
    dh = FrameTocParser()
    parser = xml.sax.expatreader.ExpatParser()
    parser.setContentHandler(dh)
    parser.parse(frameTocFileName)

