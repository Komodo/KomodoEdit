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

# Augmented Cmd class -- see the class docs strings
#
# Example Usage:
# ----------------- p4x.py ------------------------------------
# import tmCmd
# class P4XShell(tmCmd.AugmentedListCmd):
#     """
#     Perforce Extended Shell -- an extended Perforce interface
# 
#         p4x help             this help
#         p4x help commands    list the available commands
#         p4x help <command>   help on a specific command
# 
#         p4x backout ...      help backout a specific change
#     """
#     def do_backout(self, argv):
#         """backout a specific change number in perforce
#         
#         p4x backout <changenum>
#         
#         Provide all the general steps for rolling back a perforce change.
#         Everything but the "p4 submit" (for now).
#         c.f. http://www.perforce.com/perforce/technotes/note014.html
#         """
#         pass
#
#
# #---- script mainline
#
# if __name__ == '__main__':
#     shell = P4XShell()
#     sys.exit(shell.onecmd(args))
# --------------------- end of p4x.py ----------------------------
#
# try the following commands:
#     python p4x.py
#     python p4x.py help
#     python p4x.py help commands
#     python p4x.py help backout
#     python p4x.py backout 123
#

import sys, os, re, cmd


#---- globals

verbosity = 1
out = sys.stdout  # can be overridden


#---- exceptions raised by this module

class CmdError(Exception):
    def __init__(self, msg):
        self.msg = msg
    def __str__(self):
        return self.msg



#---- an augmented command shell

class AugmentedListCmd(cmd.Cmd):
    """Better help reporting (Augmented) and pass args lists (List).
   
    "Augmented" part:
        Better std do_help() implementation that uses specially formatted
        method doc strings (see comments below for this formatting). "do_*"
        commands without doc strings do not show up.

        As well, there is a default implementation of do_commands() which
        will print help for each of the do_*() command with a doc string (if
        there is no doc string then that command is "hidden").
   
    "List" part:
        Modify the std Cmd class to pass arg lists instead of command lines.
        This seems more appropriate for integration with sys.argv which handles
        the proper parsing of the command line arguments (particularly handling
        of quoting of args with spaces).

        Limitations:
            The cmdloop() stuff is not implemented because I don't use it so
            have not ported and tested it.
    """
    nohelp = "*** %s: No help for command %s."
    name = "AugmentedListCmd"
    
    def cmdloop(self, intro=None):
        raise "The cmdloop stuff is not yet implemented for AugmentedListCmd."

    def onecmd(self, argv):
        if not argv:
            return self.emptyline()
        elif argv[0] == '?':
            argv = ["help"] + argv[1:]
        elif argv[0][0] == '?':
            argv = ["help"] + [argv[0][1:]] + argv[1:]
        elif argv[0] == '!':
            if hasattr(self, 'do_shell'):
                argv = ['shell'] + argv[1:]
            else:
                return self.default(argv)
        elif argv[0][0] == '!':
            if hasattr(self, 'do_shell'):
                argv = ['shell'] + [argv[0][1:]] + argv[1:]
            else:
                return self.default(argv)
        self.lastcmd = argv
        cmdName = argv[0]
        try:
            func = getattr(self, 'do_' + cmdName)
        except AttributeError:
            return self.default(argv)
        try:
            return func(argv)
        except (TypeError, CmdError), err:
            out.write("*** %s %s: %s\n" % (self.name, cmdName, str(err)))
            out.write("(Try `%s help %s'.)\n" % (self.name, cmdName))
            usage = self.doc_usage(func.__doc__)
            if usage:
                out.write("Usage:\n")
                for line in usage:
                    out.write("\t" + line + "\n")
            # re-raise the error if being verbose
            global verbosity
            if verbosity > 1:
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

    def do_help(self, argv):
        if len(argv[1:]) > 0:
            # i.e. if any commands were specified
            for cmdName in argv[1:]:
                self._helponecmd(cmdName)
        else:
            # show the Cmd class' docstring
            if self.__class__.__doc__ is not None:
                out.write(self.__class__.__doc__ + "\n")

    def getcmds(self):
        """return list of do_* commands defined for this object"""
        # Inheritance says we have to look in class and
        # base classes; order is not important.
        cmdDict = {} # use dictionary to eliminate duplicates
        classes = [self.__class__]
        while classes:
            aclass = classes[0]
            if aclass.__bases__:
                classes = classes + list(aclass.__bases__)
            for cmd in dir(aclass):
                cmdDict[cmd] = 1
            del classes[0]
        cmds = cmdDict.keys()
        # remove non-do_*() methods
        doCmds = []
        for cmd in cmds:
            if cmd.startswith("do_"):
                doCmds.append(cmd)
        # sort and return
        doCmds.sort()
        return doCmds
    
    def printcmds(self):
        """print a single help line for each documented command"""
        for cmd in self.getcmds():
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

    def help_ashtml(self):
        out.wordWrapping = 0
        # header
        out.write('<?xml version="1.0"?>\n')
        out.write('<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Strict//EN"\n')
        out.write('          http://www.w3.org/TR/xhtml1/DTD/xhtml1-strict.dtd">\n\n')
        out.write('<html xmlns="http://www.w3.org/TR/xhtml1">\n\n')
        # head
        out.write('<head>\n')
        out.write('<title>\n')
        out.write('%s\n' % self.name)
        out.write('</title>\n')
        out.write('</head>\n\n')
        # body
        out.write('<body>\n')

        # - summary
        classDoc = self.__class__.__doc__
        if classDoc:
            out.write('<pre>\n')
            out.write(classDoc)
            out.write('</pre>\n\n')

        # - commands
        for cmd in self.getcmds():
            doc = getattr(self, cmd).__doc__
            # only show command if it has a doc string
            if doc:
                synopsis = self.doc_synopsis(doc)
                out.write('\n\n<h3>%s %s%s%s</h3>\n\n' %\
                    (self.name, cmd[3:], ' '*(15-len(cmd[3:])), synopsis))
                usage = self.doc_usage(doc)
                out.write('<pre>%s</pre>\n' % "\n".join(usage))
                desc = self.doc_description(doc)
                out.write('<p>\n%s</p>\n' % "\n".join(desc))

        # finish up
        out.write('</body>\n')
        out.write('</html>\n')
        out.wordWrapping = 1

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
            # start at the first usage line and walk forward to first empty
            # to find the start of the description
            start = 2
            while docLines[start].strip() != "":
                start += 1
            start += 1  # skip the empty line
            descLines = []
            indentation = self.doc_indentation(doc)
            for line in docLines[start:]:
                descLines.append(line[indentation:])
            return descLines


