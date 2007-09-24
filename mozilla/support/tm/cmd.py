#!python
# Copyright 2002-2003 Trent Mick

"""Useful extensions to Python's standard 'cmd' module.

    class ArgvCmd(cmd.Cmd)
        This is a subclass of Python's standard Cmd class with a couple
        improvements:
        - arguments are passed down to sub-commands as argument lists
          rather than as one command string; and
        - default help functionality is much improved.
"""
#TODO:
#   - implement the cmdloop() stuff, ... and any other methods that I
#     have not been looking at
#   - pass args through __init__ if not doing so already.
#   - sell this better in documentation
#   - describe it more fully in documentation
#   - consider a separate class for the do_help improvements

import sys
import cmd



#---- globals

_version_ = (0, 1, 0)



#---- internal support routines



#---- module public interface

class ArgvCmd(cmd.Cmd):
    """Pass arglists instead of command strings to commands.

    Modify the std Cmd class to pass arg lists instead of command lines.
    This seems more appropriate for integration with sys.argv which handles
    the proper parsing of the command line arguments (particularly handling
    of quoting of args with spaces).
    """
    name = "ArgvCmd"
    
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
            sys.stderr.write("error: %s: %s\n" % (cmdName, ex))
            sys.stderr.write("error: try '%s help %s'\n" % (self.name, cmdName))
            if 0:   # for debugging
                print
                import traceback
                traceback.print_exception(*sys.exc_info())

    def default(self, args):
        sys.stderr.error("error: unknown syntax: '%s'", " ".join(args))
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
                sys.stderr.write("error: no help for '%s'" % arg)
        else:
            return func()

    # Technically this improved do_help() does not fit into ArgvCmd, and
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




