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
# Contributors:
#   Trent Mick (TrentM@ActiveState.com)

"""kc -- a command-line convenience script to issue Komodo commandments"""

import os
import sys
import getopt
import cmd
import re
import logging


#---- exceptions

class KCError(Exception):
    pass


#---- global data

_version_ = (0, 1, 0)
log = logging.getLogger("kc")
gKomodoVer = "3.0"



#---- internal routines and classes
#TODO: prefix internal routines and classes with an underscore (as per
#      section "Naming Conventions" in http://www.python.org/peps/pep-0008.html)

class _ListCmd(cmd.Cmd):
    """Pass arglists instead of command strings to commands.

    Modify the std Cmd class to pass arg lists instead of command lines.
    This seems more appropriate for integration with sys.argv which handles
    the proper parsing of the command line arguments (particularly handling
    of quoting of args with spaces).
    """
    name = "_ListCmd"
    
    def cmdloop(self, intro=None):
        raise NotImplementedError

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
        try:
            return func(argv)
        except TypeError, ex:
            log.error("%s: %s", cmdName, ex)
            log.error("try '%s help %s'", self.name, cmdName)
            if 1:   # for debugging
                print
                import traceback
                traceback.print_exception(*sys.exc_info())

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

def _ensureKocommandmentsOnPath():
    """Find and place kocommandments.py is on sys.path.

    Currently the hard work of issuing a commandment is done by the core
    Komodo file 'kocommandments.py'.  This function sets it up so that that
    module can be imported.
    """
    try:
        import kocommandments
    except ImportError:
        # Let's try to find it in the Komodo install tree. It is usually
        # installed to bkconfig.komodoPythonUtilsDir. Presuming this script
        # is in the Komodo-devel/util dir, then bkconfig.py is one directory
        # up.
        topDir = os.path.dirname(os.path.dirname(__file__))
        sys.path.insert(0, topDir)
        try:
            from bkconfig import komodoPythonUtilsDir
            if "bkconfig" in sys.modules:
                del sys.modules["bkconfig"]
        finally:
            del sys.path[0]
        # *Append* it because we don't want other Python modules and packages
        # there to interfere with normal operation of this script, if we
        # can help it.
        sys.path.append(komodoPythonUtilsDir)


#---- public module interface
#TODO: add an appropriate public module interface

class KCShell(_ListCmd):
    """
    kc - issue Komodo commandments

    Usage:
        kc [<options>...] <command> [<args>...]

    Options:
        -h, --help      Print this help and exit.
        -V, --version   Print the version info and exit.
        -v, --verbose   More verbose output.

        -k <version>    Specify Komodo <major>.<minor> version to which to
                        connect. Defaults to "3.0".

    Komodo supports a system by which one can connect to a running Komodo
    and issue commands. This is called the Komodo Commandment system and
    each such command is called a "commandment". This script allows one
    to issue these commandments from the command-line.

    Getting Started:
        kc help                 print this help
        kc help commandments    list all Komodo commandments
        kc help <commandment>   help on a specific commandment
    """
    name = 'kc'

    def emptyline(self):
        self.do_help(['help'])

    def help_commandments(self):
        sys.stdout.write("""\
    
    General 'kc' commands:

        open            open a file
        macro           run the given code as a macro in Komodo
        macro_file      run the given macro file in Komodo
        quit            quit Komodo
        
""")
        sys.stdout.flush()

    def do_open(self, argv):
        """
    open -- open a file in Komodo

    kc open [<options>...] <file>

        Options:
            -s, --selection <selection>
                        Specify a position/selection in the opened file.
                        The given selection numbers are 0-based character
                        indices into the file. (XXX Consider giving alternate
                        interface that 'komodo.exe' provides.)

        The given file is opened in Komodo.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "s:", ["selection="])
        except getopt.GetoptError, ex:
            log.error("open: %s", ex)
            log.error("open: try 'kc help open'")
            return 1
        cargs = []
        for opt, optarg in optlist:
            if opt in ("-s", "--selection"):
                cargs += ["--selection", optarg]

        # Process arguments.
        if len(args) != 1:
            log.error("open: incorrect number of arguments: %s", args)
            log.error("open: try 'kc help open'")
            return 1
        file = args[0]
        if not os.path.isabs(file):
            file = os.path.abspath(file)
        cargs.append(file)
        
        _ensureKocommandmentsOnPath()
        import kocommandments
        try:
            kocommandments.issue("open", cargs, gKomodoVer)
        except kocommandments.KoCommandmentsError, ex:
            raise KCError(ex)

    def do_macro(self, argv):
        """
    macro -- run a macro in Komodo

    kc macro [<options>...] <macro-code>

        Options:
            -l, --language <language>
                    Specify the language of the macro. Valid values
                    are "python" (the default) and "javascript".
            -j      Shortcut for "--language=javascript"
            -p      Shortcut for "--language=python"

        The given macro code is run in Komodo.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "l:jp", ["language="])
        except getopt.GetoptError, ex:
            log.error("macro: %s", ex)
            log.error("macro: try 'kc help macro'")
            return 1
        cargs = []
        for opt, optarg in optlist:
            if opt in ("-l", "--language"):
                cargs += ["--language", optarg]
            elif opt == "-j":
                cargs += ["--language", "javascript"]
            elif opt == "-p":
                cargs += ["--language", "python"]

        # Process arguments.
        if len(args) != 1:
            log.error("macro: incorrect number of arguments: %s", args)
            log.error("macro: try 'kc help macro'")
            return 1
        code = repr(args[0])
        cargs.append(code)
        
        _ensureKocommandmentsOnPath()
        import kocommandments
        try:
            kocommandments.issue("macro", cargs, gKomodoVer)
        except kocommandments.KoCommandmentsError, ex:
            raise KCError(ex)

    def do_macro_file(self, argv):
        """
    macro_file -- run a macro file in Komodo

    kc macro_file [<options>...] <macro-file>

        Options:
            -l, --language <language>
                    Specify the language of the macro_file. Valid values
                    are "python" (the default) and "javascript".
            -j      Shortcut for "--language=javascript"
            -p      Shortcut for "--language=python"

        The given file is run as a macro in Komodo.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "l:jp", ["language="])
        except getopt.GetoptError, ex:
            log.error("macro_file: %s", ex)
            log.error("macro_file: try 'kc help macro_file'")
            return 1
        cargs = []
        for opt, optarg in optlist:
            if opt in ("-l", "--language"):
                cargs += ["--language", optarg]
            elif opt == "-j":
                cargs += ["--language", "javascript"]
            elif opt == "-p":
                cargs += ["--language", "python"]

        # Process arguments.
        if len(args) != 1:
            log.error("macro_file: incorrect number of arguments: %s", args)
            log.error("macro_file: try 'kc help macro_file'")
            return 1
        file = args[0]
        if not os.path.isabs(file):
            file = os.path.abspath(file)
        cargs.append(file)
        
        _ensureKocommandmentsOnPath()
        import kocommandments
        try:
            kocommandments.issue("macro_file", cargs, gKomodoVer)
        except kocommandments.KoCommandmentsError, ex:
            raise KCError(ex)


    def do_quit(self, argv):
        """
    quit -- quit Komodo

    kc quit

        Shutdown Komodo.
        """
        # Process options.
        try:
            optlist, args = getopt.getopt(argv[1:], "")
        except getopt.GetoptError, ex:
            log.error("quit: %s", ex)
            log.error("quit: try 'kc help quit'")
            return 1
        cargs = []

        # Process arguments.
        if len(args) != 0:
            log.error("quit: incorrect number of arguments: %s", args)
            log.error("quit: try 'kc help quit'")
            return 1
        
        _ensureKocommandmentsOnPath()
        import kocommandments
        try:
            kocommandments.issue("quit", cargs, gKomodoVer)
        except kocommandments.KoCommandmentsError, ex:
            raise KCError(ex)



#---- mainline

def main(argv):
    logging.basicConfig()
    try:
        optlist, args = getopt.getopt(argv[1:], "hVvk:",
            ["help", "version", "verbose"])
    except getopt.GetoptError, ex:
        log.error(str(ex))
        log.error("Try 'kc --help'.")
        return 1
    for opt, optarg in optlist:
        if opt in ("-h", "--help"):
            sys.stdout.write(KCShell.__doc__)
            return 0
        elif opt in ("-V", "--version"):
            print "kc %s" % '.'.join([str(i) for i in _version_])
            return 0
        elif opt in ("-v", "--verbose"):
            log.setLevel(logging.DEBUG)
        elif opt == "-k":
            if not re.match("\d+\.\d+", optarg):
                log.error("invalid Komodo version value: '%s': it must be "
                          "of the form <major>.<minor>", optarg)
                return 1
            global gKomodoVer
            gKomodoVer = optarg

    shell = KCShell()
    try:
        return shell.onecmd(args)
    except KCError, ex:
        log.error(str(ex))
        if log.isEnabledFor(logging.DEBUG):
            import traceback
            traceback.print_exception(*sys.exc_info())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0])
    sys.exit( main(sys.argv) )




