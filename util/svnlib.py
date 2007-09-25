#!/usr/bin/env python

"""
    An OO interface to 'svn' (the Subversion client command line app).  Based on
    Subversion version 1.0.6.

    Usage:
        import svnlib
        svn = svnlib.SVN(<svnoptions>)
        result = svn.<command>(<svnoptions>)

    For more information see the doc string on each command. For example:
        print svnlib.SVN.opened.__doc__
    
    Arguments to all functions match the arguments of the command as retrieved with:
    
        'svn help command'
        
    but they need to be converted as in the following example:
    
        --force-log becomes force_log
        --auto-props becomes auto_props
    
    If the argument takes no additional information, it is a boolean argument in the function.  Some
    functions (those that take multiple paths such as commit) will have additional parameters:
    
        SVN.commit([file1.txt, ...], username='test', password='test', force_log=1)
        
    Only the long argument names are supported.
    
    Available subcommands:
       add
       checkout (co)
       cleanup
       commit (ci)
       copy (cp)
       delete (del, remove, rm)
       diff (di)
       import (see importToRepository)
       info
       resolved
       revert
       status (stat, st)
       update (up)
       
    Not Implemented:
       blame (praise, annotate, ann)
       cat
       export
       help (?, h)
       list (ls)
       log
       merge
       mkdir
       move (mv, rename, ren)
       propdel (pdel, pd)
       propedit (pedit, pe)
       propget (pget, pg)
       proplist (plist, pl)
       propset (pset, ps)
       switch (sw)
"""

import os
import sys
import pprint
import cmd
import re
import types
import marshal
import getopt
import tempfile
import copy

import logging
log = logging.getLogger('svnlib')
#log.setLevel(logging.DEBUG)

#---- exceptions

class SVNLibError(Exception):
    pass


#---- global data

_version_ = (0, 1, 0)

#---- internal support stuff
actionNames = {' ':'', 'A': 'add', 'C': 'conflict', 'D': 'delete',
                'G': 'merged', 'I': 'ignored', 'M': 'edit',
                'R': 'replaced', 'X': 'unversioned',
                '?': '', '!': 'incomplete', '~': 'conflict'}

def _escapeArg(arg):
    """Escape the given command line argument for the shell."""
    #XXX There is a *lot* more that we should escape here.
    #XXX This is also not right on Linux, just try putting 'svn' is a dir
    #    with spaces.
    return arg.replace('"', r'\"')


def _joinArgv(argv):
    r"""Join an arglist to a string appropriate for running.
        >>> import os
        >>> _joinArgv(['foo', 'bar "baz'])
        'foo "bar \\"baz"'
    """
    cmdstr = ""
    # Quote args with '*' because don't want shell to expand the
    # argument. (XXX Perhaps that should only be done for Windows.)
    specialChars = [';', ' ', '=', '*']
    for arg in argv:
        for ch in specialChars:
            if ch in arg:
                cmdstr += '"%s"' % _escapeArg(arg)
                break
        else:
            cmdstr += _escapeArg(arg)
        cmdstr += ' '
    if cmdstr.endswith(' '): cmdstr = cmdstr[:-1]  # strip trailing space
    return cmdstr


def _run(argv, cwd=None, env=None, input=None):
    """Prepare and run the given arg vector, 'argv', and return the
    results.  Returns (<stdout lines>, <stderr lines>, <return value>).
    Note: 'argv' may also just be the command string.
    """
    if type(argv) in (types.ListType, types.TupleType):
        cmd = _joinArgv(argv)
    else:
        cmd = argv
    log.debug("Running '%s'..." % cmd)
    output = None
    # Run with process.py if it is available. It is more reliable.
    try:
        import process
    except ImportError:
        if input is not None:
            raise SVNLibError("Cannot handle process input with process.py. "\
                             "cmd=%r" % cmd)
        if sys.platform.startswith('win'):
            # XXX The following incantation will hang popen3 on Win9x:
            #    echo "hi there"
            #    echo "hi\ there"
            # but these will not hang popen3:
            #    echo hi there
            #    echo "hithere"
            # Something to do with quoting and spaces, and passing through
            # w9xpopen.exe, and launching via command.com. Weird quoting
            # rules for command.com? Should perhaps work on _joinArg and
            # _escapeArg to ensure safe command strings (if possible).
            i, o, e = os.popen3(cmd)
            output = o.readlines()
            error = e.readlines()
            i.close()
            e.close()
            retval = o.close()
        else:
            import popen2
            p = popen2.Popen3(cmd, 1)
            i, o, e = p.tochild, p.fromchild, p.childerr
            output = o.readlines()
            error = e.readlines()
            i.close()
            o.close()
            e.close()
            rv = p.wait()
            if os.WIFEXITED(rv):
                retval = os.WEXITSTATUS(rv)
            else:
                raise SVNLibError("Error running '%s', it did not exit "\
                                 "properly: rv=%d" % (cmd, rv))
    else:
        if env is None:
            env = {}
        
        # Komodo can only handle svn messages in english.
        # http://bugs.activestate.com/show_bug.cgi?id=45677
        env['LC_MESSAGES'] = 'en_US'
        # Set LANGUAGE too, otherwise it may still come back in another lang
        # http://bugs.activestate.com/show_bug.cgi?id=68615
        env['LANGUAGE'] = 'en_US'

        p = process.ProcessOpen(cmd=cmd, cwd=cwd, env=env)
        if input is not None:
            p.stdin.write(input)
        p.stdin.close()
        output = p.stdout.readlines()
        error = p.stderr.readlines()
        p.stdout.close()
        p.stderr.close()
        retval = p.wait()
        if not sys.platform.startswith("win"):
            if os.WIFEXITED(retval):
                retval = os.WEXITSTATUS(retval)
            else:
                raise SVNLibError("Error running '%s', it did not exit "\
                                 "properly: retval=%d" % (cmd, retval))
        p.close()

    # XXX TODO
    # svn will return valid results, and an error result in the same
    # call.  We need to use lasterrorsvc, or something similar to catch
    # the errors, but allow the valid results to be used.
    #if retval:
    #    raise SVNLibError("Error %s running '%s' in '%s': \n%s"\
    #                     % (retval,cmd, cwd,''.join(error), ))
    return output, error, retval

#---- public stuff
def getValidOpts(valid, **options):
    newopts = {}
    for key, val in options.items():
        if key in valid:
            newopts[key] = val
    return newopts

def makeOptv(**options):
    """Create a svn option vector from the given svn option dictionary.
    
    "options" is an option dictionary. Valid keys and values are defined by
        what class SVN's constructor accepts via SVN(**optd).
    
    Example:
        >>> makeOptv(client='swatter', dir='D:\\trentm')
        ['--client', 'swatter', '--dir', 'D:\\trentm']
        >>> makeOptv(client='swatter', dir=None)
        ['--client', 'swatter']
    """
    # SVN args are globally unique across all commands, so this is simple...
    optv = []
    for key, val in options.items():
        # convert the key from this_is_the_key to --this-is-the-key
        arg = '--' + key.replace('_','-')
        # first, handle those keys that do not have an argument
        if key in ['non_recursive', 'auto_props', 'no_auto_props', 'quiet',
                   'no_auth_cache', 'non_interactive', 'force_log', 'force',
                   'notice_ancestry', 'no_diff_deleted', 'dry_run',
                   'ignore_ancestry', 'incremental', 'no_ignore',
                   'notice_ancestry', 'recursive', 'revprop', 'show_updates',
                   'stop_on_copy', 'strict', 'verbose', 'xml'
                   ]:
            if int(val):
                optv.append(arg)
        else:
            optv.append(arg)
            if type(val) not in types.StringTypes:
                val = str(val)
            optv.append(val)
    return optv

def _parseHits(output, error=[], retval=[], _raw=0, _exp='^(?P<result>\w+)\s+(?P<path>.*)$'):
    hits = []
    hitRe = re.compile(_exp)
    for line in output:
        match = hitRe.match(line)
        if match:
            hit = match.groupdict()
            hits.append(hit)

    if _raw:
        return hits, {'stdout': ''.join(output),
                      'stderr': ''.join(error),
                      'retval': retval}
    else:
        return hits

def _parseKeyList(output, error=[], retval=[], _raw=0):
    hits = {}
    for line in output:
        try:
            match = line.split(':', 1)
            hits[match[0]]=match[1].strip()
        except IndexError:
            pass
    
    if _raw:
        return hits, {'stdout': ''.join(output),
                      'stderr': ''.join(error),
                      'retval': retval}
    else:
        return hits

class SVN:
    """A proxy to the Subversion client app 'svn'."""
    def __init__(self, svn='svn', **options):
        """Create a 'svn' proxy object.

        "svn" is the Subversion client to execute commands with. Defaults
            to 'svn'.
            
        You can set any SVN supported argument in the init, and they will
        be used in all SVN calls.  This can be very usefull for some arguments,
        and detrimental in others.
        
        For more information about supported arguments see:
        http://svnbook.red-bean.com/en/1.0/ch09.html#svn-ch-9-sect-1.1
        
        Optional keyword arguments:
            "cwd" is a special option to have the underlying process
                spawner use this as the cwd.
        """
        self.svn = svn
        self.optd = options
        self._optv = makeOptv(**self.optd)
        
    def _svnrun(self, argv, env=None, input=None, **svnoptions):
        """Run the given svn command.
        
        The current instance's svn and svn options (optionally overriden by
        **svnoptions) are used. The 3-tuple (<output>, <error>, <retval>) is
        returned.
        """
        cwd = None
        if svnoptions:
            import copy
            d = copy.copy(self.optd)
            d.update(svnoptions)
            if 'cwd' in d:
                cwd = d['cwd']
                del d['cwd']
            svnoptv = makeOptv(**d)
        else:
            svnoptv = self._optv
        if not env and 'env' in svnoptv:
            env = svnoptv['env']
            del svnoptv['env']
        argv = [self.svn] + svnoptv + argv
        return _run(argv, cwd, env, input)

    def _simpleCommand(self, command, urls, _raw=0, **svnoptions):
        if type(urls) in types.StringTypes:
            urls = [urls]
        argv = [command] + urls
        output, error, retval = self._svnrun(argv, **svnoptions)
        print "ARGV: %r" % argv
        print "OUTPUT: %r" % output
        print "ERROR: %r" % error
        print "SVNOPTIONS: %r" % svnoptions
        return _parseHits(output, error, retval, _raw)
        
    def add(self, files, _raw=0, **svnoptions):
        """
        add: Put files and directories under version control, scheduling
        them for addition to repository.  They will be added in next commit.
        
        usage: add PATH...
        
        Valid options:
          --targets arg            : pass contents of file ARG as additional args
          -N [--non-recursive]     : operate on single directory only
          -q [--quiet]             : print as little as possible
          --config-dir arg         : read user configuration files from directory ARG
          --auto-props             : enable automatic properties
          --no-auto-props          : disable automatic properties
        
        Returns a list of dicts representing commentary on each file *attempted* to be
        opened for add. Keys are: 'result', 'path'.
        
        If '_raw' is true then the a dictionary with the unprocessed results of calling
        svn is returned in addition to the processed results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        # Example output:
        #   A         asdf.txt
        #
        # Example recursive output
        #
        #    A         testdir
        #    A         testdir/a
        #    A         testdir/b
        #    A         testdir/c
        #    A         testdir/d
        #
        return self._simpleCommand('add', files, _raw, **svnoptions)

    def blame(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        blame (praise, annotate, ann): Output the content of specified files or
        URLs with revision and author information in-line.
        usage: blame TARGET...
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG
        """

        raise SVNLibError("Not Implemented")
    
    def cat(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        cat: Output the content of specified files or URLs.
        usage: cat TARGET...
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG
        """

        raise SVNLibError("Not Implemented")
    
    def checkout(self, urls, path=None, _raw=0, **svnoptions):
        """
        checkout (co): Check out a working copy from a repository.
        usage: checkout URL... [PATH]
        
          Note: If PATH is omitted, the basename of the URL will be used as
          the destination. If multiple URLs are given each will be checked
          out into a sub-directory of PATH, with the name of the sub-directory
          being the basename of the URL.
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -q [--quiet]             : print as little as possible
          -N [--non-recursive]     : operate on single directory only
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG
        
        Returns a list of dicts representing commentary on each file *attempted* to be
        opened for add. Keys are: 'result', 'path'.
        
        If '_raw' is true then the a dictionary with the unprocessed results of calling
        svn is returned in addition to the processed results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
    
        if type(urls) in types.StringTypes:
            urls = [urls]
        
        argv = ['checkout'] + urls
        if path:
            argv += [path]
        output, error, retval = self._svnrun(argv, **svnoptions)

        # Example output:
        #    A  mine/a
        #    A  mine/b
        #    Checked out revision 2.
        #
        return _parseHits(output, error, retval, _raw)
    

    def cleanup(self, path=None, _raw=0, **svnoptions):
        """
        cleanup: Recursively clean up the working copy, removing locks, resuming
        unfinished operations, etc.
        
        SVN.cleanup(path, _raw=0, **options)
        
        usage: cleanup [PATH...]
        
        Valid options:
          --diff3-cmd arg          : use ARG as merge command
          --config-dir arg         : read user configuration files from directory ARG
        
        cleanup produces no output for results.
        """
        argv = ['cleanup']
        if path:
            argv += [path]
        self._svnrun(argv, **svnoptions)


    def commit(self, urls, _raw=0, **svnoptions):
        """
        commit (ci): Send changes from your working copy to the repository.
        
        SVN.commit([file,...], _raw=0, **options)
        
        usage: commit [PATH...]
        
          A log message must be provided, but it can be empty.  If it is not
          given by a --message or --file option, an editor will be started.
        
        Valid options:
          -m [--message] arg       : specify commit message ARG
          -F [--file] arg          : read data from file ARG
          -q [--quiet]             : print as little as possible
          -N [--non-recursive]     : operate on single directory only
          --targets arg            : pass contents of file ARG as additional args
          --force-log              : force validity of log message source
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --editor-cmd arg         : use ARG as external editor
          --encoding arg           : treat value as being in charset encoding ARG
          --config-dir arg         : read user configuration files from directory ARG
        
        Returns a list of dicts representing commentary on each file *attempted* to be
        opened for add. Keys are: 'result', 'path'.
        
        If '_raw' is true then the a dictionary with the unprocessed results of calling
        svn is returned in addition to the processed results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        # Example output:
        #    Sending         file.txt
        #    Transmitting file data .
        #    Committed revision 7.
        #    Deleting        dumby.txt
        #    Committed revision 7.
        #
        return self._simpleCommand('commit', urls, _raw, **svnoptions)
    
    def copy(self, frompath, topath, _raw=0, **svnoptions):
        """
        copy (cp): Duplicate something in working copy or repos, remembering history.
        
        SVN.copy(src, dest, _raw=0, **options)
        
        usage: copy SRC DST
        
          SRC and DST can each be either a working copy (WC) path or URL:
            WC  -> WC:   copy and schedule for addition (with history)
            WC  -> URL:  immediately commit a copy of WC to URL
            URL -> WC:   check out URL into WC, schedule for addition
            URL -> URL:  complete server-side copy;  used to branch & tag
        
        Valid options:
          -m [--message] arg       : specify commit message ARG
          -F [--file] arg          : read data from file ARG
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -q [--quiet]             : print as little as possible
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --force-log              : force validity of log message source
          --editor-cmd arg         : use ARG as external editor
          --encoding arg           : treat value as being in charset encoding ARG
          --config-dir arg         : read user configuration files from directory ARG
        
        
        Returns a list of dicts representing commentary on each file *attempted* to be
        opened for add. Keys are: 'result', 'path'.
        
        If '_raw' is true then the a dictionary with the unprocessed results of calling
        svn is returned in addition to the processed results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
    
        argv = ['copy', frompath, topath]
        if path:
            argv += [path]
        output, error, retval = self._svnrun(argv, **svnoptions)

        # Example output:
        #    A  file.txt
        #
        return _parseHits(output, error, retval, _raw)

    def delete(self, urls, _raw=0, **svnoptions):
        """
        delete (del, remove, rm): Remove files and directories from version control.
        
        SVN.delete([file,...], _raw=0, **options)
        
        usage: 1. delete PATH...
               2. delete URL...
        
          1. Each item specified by a PATH is scheduled for deletion upon
            the next commit.  Files, and directories that have not been
            committed, are immediately removed from the working copy.
            PATHs that are, or contain, unversioned or modified items will
            not be removed unless the --force option is given.
        
          2. Each item specified by a URL is deleted from the repository
            via an immediate commit.
        
        Valid options:
          --force                  : force operation to run
          --force-log              : force validity of log message source
          -m [--message] arg       : specify commit message ARG
          -F [--file] arg          : read data from file ARG
          -q [--quiet]             : print as little as possible
          --targets arg            : pass contents of file ARG as additional args
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --editor-cmd arg         : use ARG as external editor
          --encoding arg           : treat value as being in charset encoding ARG
          --config-dir arg         : read user configuration files from directory ARG
        
        
        Returns a list of dicts representing commentary on each file *attempted* to be
        opened for add. Keys are: 'result', 'path'.
        
        If '_raw' is true then the a dictionary with the unprocessed results of calling
        svn is returned in addition to the processed results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        # Example output:
        #    D         myfile
        #
        return self._simpleCommand('delete', urls, _raw, **svnoptions)
    
    def diff(self, file1, file2=None, _raw=0, **svnoptions):
        """
        diff (di): Display the differences between two paths.
        
        SVN.diff(file1, file2=NULL, **options)
        
        usage: 1. diff [-r N[:M]] [--old OLD-TGT] [--new NEW-TGT] [PATH...]
               2. diff -r N:M URL
               3. diff [-r N[:M]] URL1[@N] URL2[@M]
        
          1. Display the differences between OLD-TGT and NEW-TGT.  PATHs, if
             given, are relative to OLD-TGT and NEW-TGT and restrict the output
             to differences for those paths.  OLD-TGT and NEW-TGT may be working
             copy paths or URL[@REV].
        
             OLD-TGT defaults to the path '.' and NEW-TGT defaults to OLD-TGT.
             N defaults to BASE or, if OLD-TGT is an URL, to HEAD.
             M defaults to the current working version or, if NEW-TGT is an URL,
             to HEAD.
        
             '-r N' sets the revision of OLD-TGT to N, '-r N:M' also sets the
             revision of NEW-TGT to M.
        
          2. Shorthand for 'svn diff -r N:M --old=URL --new=URL'.
        
          3. Shorthand for 'svn diff [-r N[:M]] --old=URL1 --new=URL2'
        
          Use just 'svn diff' to display local modifications in a working copy
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          --old arg                : use ARG as the older target
          --new arg                : use ARG as the newer target
          -x [--extensions] arg    : pass ARG as bundled options to GNU diff
          -N [--non-recursive]     : operate on single directory only
          --diff-cmd arg           : use ARG as diff command
          --no-diff-deleted        : do not print differences for deleted files
          --notice-ancestry        : notice ancestry when calculating differences
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG
        
        
        Returns the raw diff results
        """
        optv = getValidOpts(['env','cwd','revision','old','new','extensions',
                             'diff_cmd','no_diff_deleted','notice_ancestry',
                             'username','password','no_auth_cache', 'revision',
                             'non_interactive','config_dir'], **svnoptions)
    
        argv = ['diff', file1]
        if file2:
            argv += [file2]
        output, error, retval = self._svnrun(argv, **optv)
        diff = ''.join(output)
        if _raw:
            return diff, \
                         {'stdout': diff,
                          'stderr': ''.join(error),
                          'retval': retval}
        else:
            return diff
        

    def diff1(self, urls, _raw=0, **svnoptions):
        if type(urls) in types.StringTypes:
            urls = [urls]
        diffs = []
        for url in urls:
            diff = self.diff(url, _raw=_raw, **svnoptions)
            if _raw:
                diff, out = diff
            diffs.append(diff)
        return os.pathsep.join(diffs)

    def export(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        export: Create an unversioned copy of a tree.
        usage: 1. export [-r REV] URL [PATH]
               2. export [-r REV] PATH1 [PATH2]
        
          1. Exports a clean directory tree from the repository specified by
             URL, at revision REV if it is given, otherwise at HEAD, into
             PATH. If PATH is omitted, the last component of the URL is used
             for the local directory name.
        
          2. Exports a clean directory tree from the working copy specified by
             PATH1, at revision REV if it is given, otherwise at WORKING, into
             PATH2.  If PATH2 is omitted, the last component of the PATH1 is used
             for the local directory name. If REV is not specified, all local
             changes will be preserved, but files not under version control will
             not be copied.
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -q [--quiet]             : print as little as possible
          --force                  : force operation to run
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG
        """

        raise SVNLibError("Not Implemented")
    
    def importToRepository(self, urls, _raw=0, **svnoptions):
        """
        import: Commit an unversioned file or tree into the repository.
        
        SVN.importToRepository(path, url, _raw=0, **options)
        
        *NOTE: import is a python keyword, so we use a verbose function name.
        
        usage: import [PATH] URL
        
          Recursively commit a copy of PATH to URL.
          If PATH is omitted '.' is assumed.  Parent directories are created
          as necessary in the repository.
        
        Valid options:
          -m [--message] arg       : specify commit message ARG
          -F [--file] arg          : read data from file ARG
          -q [--quiet]             : print as little as possible
          -N [--non-recursive]     : operate on single directory only
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --force-log              : force validity of log message source
          --editor-cmd arg         : use ARG as external editor
          --encoding arg           : treat value as being in charset encoding ARG
          --config-dir arg         : read user configuration files from directory ARG
          --auto-props             : enable automatic properties
          --no-auto-props          : disable automatic properties
        
        
        Returns a list of dicts representing commentary on each file *attempted* to be
        opened for add. Keys are: 'action', 'path'.
        
        If '_raw' is true then the a dictionary with the unprocessed results of calling
        svn is returned in addition to the processed results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        if type(urls) in types.StringTypes:
            urls = [urls]
        
        argv = ['import'] + urls + [path]
        output, error, retval = self._svnrun(argv, **svnoptions)

        # Example output:
        #    Adding         myproj/sample.txt
        #    ...
        #    Transmitting file data .........
        #    Committed revision 19.
        #
        return _parseHits(output, error, retval, _raw, '^(?P<action>\w)\s+(?P<path>.*)$')
    
    def info(self, urls, _raw=0, **svnoptions):
        """
        info: Display information about a file or directory.
        
        SVN.info([file,...], _raw=0, **options)
        
        usage: info [PATH...]
        
          Print information about each PATH (default: '.').
        
        Valid options:
          --targets arg            : pass contents of file ARG as additional args
          -R [--recursive]         : descend recursively
          --config-dir arg         : read user configuration files from directory ARG
        
        
        Returns a dict of file URLS, whos values are dicts containing the key:value
        result of the info output.
        
        If '_raw' is true then the a dictionary with the unprocessed results of calling
        svn is returned in addition to the processed results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
    
        if type(urls) in types.StringTypes:
            urls = [urls]
        
        argv = ['info'] + urls
        output, error, retval = self._svnrun(argv, **svnoptions)
        if not output:
            if _raw:
                return None, None
            return None
        # Example output:
        #    $ svn info foo.c
        #    Path: foo.c
        #    Name: foo.c
        #    URL: http://svn.red-bean.com/repos/test/foo.c
        #    Revision: 4417
        #    Node Kind: file
        #    Schedule: normal
        #    Last Changed Author: sally
        #    Last Changed Rev: 20
        #    Last Changed Date: 2003-01-13 16:43:13 -0600 (Mon, 13 Jan 2003)
        #    Text Last Updated: 2003-01-16 21:18:16 -0600 (Thu, 16 Jan 2003)
        #    Properties Last Updated: 2003-01-13 21:50:19 -0600 (Mon, 13 Jan 2003)
        #    Checksum: /3L38YwzhT93BWvgpdF6Zw==
        #
        
        # multiple files are seperated by a blank line, we want to split on that
        out = ''.join(output)
        files = re.split(r'[\r\n|\n|\r]{2}', out)
        
        filehits = {}
        for fileinfo in files:
            hits = {}
            for line in fileinfo.splitlines():
                try:
                    match = line.split(':', 1)
                    hits[match[0]]=match[1].strip()
                except IndexError:
                    pass
            try:
                filehits[hits['Path']] = hits
            except KeyError:
                try:
                    filehits[hits['URL']] = hits
                except KeyError:
                    pass
                        
        if _raw:
            return filehits, {'stdout': ''.join(output),
                          'stderr': ''.join(error),
                          'retval': retval}
        else:
            return filehits

    def list(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        list (ls): List directory entries in the repository.
        usage: list [TARGET...]
        
          List each TARGET file and the contents of each TARGET directory as
          they exist in the repository.  If TARGET is a working copy path, the
          corresponding repository URL will be used.
        
          The default TARGET is '.', meaning the repository URL of the current
          working directory.
        
          With --verbose, the following fields show the status of the item:
        
            Revision number of the last commit
            Author of the last commit
            Size (in bytes)
            Date and time of the last commit
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -v [--verbose]           : print extra information
          -R [--recursive]         : descend recursively
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG


        """
        raise SVNLibError("Not Implemented")

    re_log_revisions = re.compile(
        r'''------------------------------------------------------------------------\s*[\r\n]*'''\
         '''r(?P<revision>\d+)\s\|\s(?P<author>.*)\s\|\s(?P<date>.*)\s\|\s(?P<num_lines>\d+) line.*[\r\n]*'''\
         '''[\r\n]*'''
    )

    def log(self, url, _raw=0, **svnoptions):
        """
        log: Show the log messages for a set of revision(s) and/or file(s).
        usage: 1. log [PATH]
               2. log URL [PATH...]
        
          1. Print the log messages for a local PATH (default: '.').
             The default revision range is BASE:1.
        
          2. Print the log messages for the PATHs (default: '.') under URL.
             The default revision range is HEAD:1.
        
          With -v, also print all affected paths with each log message.
          With -q, don't print the log message body itself (note that this is
          compatible with -v).
        
          Each log message is printed just once, even if more than one of the
          affected paths for that revision were explicitly requested.  Logs
          follow copy history by default.  Use --stop-on-copy to disable this
          behavior, which can be useful for determining branchpoints.
        
          Examples:
            svn log
            svn log foo.c
            svn log http://www.example.com/repo/project/foo.c
            svn log http://www.example.com/repo/project foo.c bar.c
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -q [--quiet]             : print as little as possible
          -v [--verbose]           : print extra information
          --targets arg            : pass contents of file ARG as additional args
          --stop-on-copy           : do not cross copies while traversing history
          --incremental            : give output suitable for concatenation
          --xml                    : output in XML
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG
        """

        argv = ['log', url]
        output, error, retval = self._svnrun(argv, **svnoptions)
        if not output:
            if _raw:
                return None, {'stdout': output,
                              'stderr': ''.join(error),
                              'retval': retval}
            return None

        # Example output below from: svn log file2.txt
        #
        #------------------------------------------------------------------------
        #r9 | toddw | 2006-06-13 18:10:41 -0700 (Tue, 13 Jun 2006) | 2 lines
        #
        #Updated with more lines.
        #
        #------------------------------------------------------------------------
        #r7 | toddw | 2006-06-13 18:09:35 -0700 (Tue, 13 Jun 2006) | 2 lines
        #
        #Added file2.txt.
        #Cool aye.
        #------------------------------------------------------------------------
        #
        
        history = []
        output = ''.join(output)

        matchIterator = self.re_log_revisions.finditer(output)
        try:
            match = matchIterator.next()
        except StopIteration:
            match = None
        while match:
            text_start = match.end()
            try:
                matchNext = matchIterator.next()
            except StopIteration:
                matchNext = None
            if matchNext:
                message = output[text_start:matchNext.start()]
            else:
                leftOverText = output[text_start:]
                endMarker = leftOverText.find("------------------------------------------------------------------------")
                if endMarker > 0:
                    leftOverText = leftOverText[:endMarker]
                message = leftOverText

            history.append( {
                'revision': match.group('revision'),
                'author': match.group('author'),
                'date': match.group('date'),
                'message': message
                } )
            match = matchNext

        if _raw:
            return history, {'stdout': output,
                             'stderr': ''.join(error),
                             'retval': retval}
        else:
            return history
    
    def merge(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        merge: Apply the differences between two sources to a working copy path.
        usage: 1. merge sourceURL1[@N] sourceURL2[@M] [WCPATH]
               2. merge sourceWCPATH1@N sourceWCPATH2@M [WCPATH]
               3. merge -r N:M SOURCE [WCPATH]
        
          1. In the first form, the source URLs are specified at revisions
             N and M.  These are the two sources to be compared.  The revisions
             default to HEAD if omitted.
        
          2. In the second form, the URLs corresponding to the source working
             copy paths define the sources to be compared.  The revisions must
             be specified.
        
          3. In the third form, SOURCE can be a URL, or working copy item
             in which case the corresponding URL is used.  This URL, at
             revisions N and M, defines the two sources to be compared.
        
          WCPATH is the working copy path that will receive the changes.
          If WCPATH is omitted, a default value of '.' is assumed, unless
          the sources have identical basenames that match a file within '.':
          in which case, the differences will be applied to that file.
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -N [--non-recursive]     : operate on single directory only
          -q [--quiet]             : print as little as possible
          --force                  : force operation to run
          --dry-run                : try operation but make no changes
          --diff3-cmd arg          : use ARG as merge command
          --ignore-ancestry        : ignore ancestry when calculating merges
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG


        """
        raise SVNLibError("Not Implemented")
    
    def mkdir(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        mkdir: Create a new directory under version control.
        usage: 1. mkdir PATH...
               2. mkdir URL...
        
          Create version controlled directories.
        
          1. Each directory specified by a working copy PATH is created locally
            and scheduled for addition upon the next commit.
        
          2. Each directory specified by a URL is created in the repository via
            an immediate commit.
        
          In both cases, all the intermediate directories must already exist.
        
        Valid options:
          -m [--message] arg       : specify commit message ARG
          -F [--file] arg          : read data from file ARG
          -q [--quiet]             : print as little as possible
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --editor-cmd arg         : use ARG as external editor
          --encoding arg           : treat value as being in charset encoding ARG
          --force-log              : force validity of log message source
          --config-dir arg         : read user configuration files from directory ARG


        """
        raise SVNLibError("Not Implemented")
    
    def move(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        move (mv, rename, ren): Move and/or rename something in working copy or repository.
        usage: move SRC DST
        
          Note:  this subcommand is equivalent to a 'copy' and 'delete'.
        
          SRC and DST can both be working copy (WC) paths or URLs:
            WC  -> WC:   move and schedule for addition (with history)
            URL -> URL:  complete server-side rename.
        
        Valid options:
          -m [--message] arg       : specify commit message ARG
          -F [--file] arg          : read data from file ARG
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -q [--quiet]             : print as little as possible
          --force                  : force operation to run
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --editor-cmd arg         : use ARG as external editor
          --encoding arg           : treat value as being in charset encoding ARG
          --force-log              : force validity of log message source
          --config-dir arg         : read user configuration files from directory ARG


        """
        raise SVNLibError("Not Implemented")
    
    def propdel(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        propdel (pdel, pd): Remove PROPNAME from files, dirs, or revisions.
        usage: 1. propdel PROPNAME [PATH...]
               2. propdel PROPNAME --revprop -r REV [URL]
        
          1. Removes versioned props in working copy.
          2. Removes unversioned remote prop on repos revision.
        
        Valid options:
          -q [--quiet]             : print as little as possible
          -R [--recursive]         : descend recursively
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          --revprop                : operate on a revision property (use with -r)
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG


        """
        raise SVNLibError("Not Implemented")
    
    def propredit(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        propedit (pedit, pe): Edit property PROPNAME with $EDITOR on targets.
        usage: 1. propedit PROPNAME PATH...
               2. propedit PROPNAME --revprop -r REV [URL]
        
          1. Edits versioned props in working copy.
          2. Edits unversioned remote prop on repos revision.
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          --revprop                : operate on a revision property (use with -r)
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --encoding arg           : treat value as being in charset encoding ARG
          --editor-cmd arg         : use ARG as external editor
          --force                  : force operation to run
          --config-dir arg         : read user configuration files from directory ARG


        """
        raise SVNLibError("Not Implemented")
    
    def propget(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        propget (pget, pg): Print value of PROPNAME on files, dirs, or revisions.
        usage: 1. propget PROPNAME [PATH...]
               2. propget PROPNAME --revprop -r REV [URL]
        
          1. Prints versioned prop in working copy.
          2. Prints unversioned remote prop on repos revision.
        
          By default, this subcommand will add an extra newline to the end
          of the property values so that the output looks pretty.  Also,
          whenever there are multiple paths involved, each property value
          is prefixed with the path with which it is associated.  Use
          the --strict option to disable these beautifications (useful,
          for example, when redirecting binary property values to a file).
        
        Valid options:
          -R [--recursive]         : descend recursively
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          --revprop                : operate on a revision property (use with -r)
          --strict                 : use strict semantics
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG


        """
        raise SVNLibError("Not Implemented")
    
    def proplist(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        proplist (plist, pl): List all properties on files, dirs, or revisions.
        usage: 1. proplist [PATH...]
               2. proplist --revprop -r REV [URL]
        
          1. Lists versioned props in working copy.
          2. Lists unversioned remote props on repos revision.
        
        Valid options:
          -v [--verbose]           : print extra information
          -R [--recursive]         : descend recursively
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -q [--quiet]             : print as little as possible
          --revprop                : operate on a revision property (use with -r)
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG
        """
        raise SVNLibError("Not Implemented")
    
    def propset(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        propset (pset, ps): Set PROPNAME to PROPVAL on files, dirs, or revisions.
        usage: 1. propset PROPNAME [PROPVAL | -F VALFILE] PATH...
               2. propset PROPNAME --revprop -r REV [PROPVAL | -F VALFILE] [URL]
        
          1. Creates a versioned, local propchange in working copy.
          2. Creates an unversioned, remote propchange on repos revision.
        
          Note: svn recognizes the following special versioned properties
          but will store any arbitrary properties set:
            svn:ignore     - A newline separated list of file patterns to ignore.
            svn:keywords   - Keywords to be expanded.  Valid keywords are:
              URL, HeadURL             - The URL for the head version of the object.
              Author, LastChangedBy    - The last person to modify the file.
              Date, LastChangedDate    - The date/time the object was last modified.
              Rev, LastChangedRevision - The last revision the object changed.
              Id                       - A compressed summary of the previous
                                           4 keywords.
            svn:executable - If present, make the file executable. This
              property cannot be set on a directory.  A non-recursive attempt
              will fail, and a recursive attempt will set the property only
              on the file children of the directory.
            svn:eol-style  - One of 'native', 'LF', 'CR', 'CRLF'.
            svn:mime-type  - The mimetype of the file.  Used to determine
              whether to merge the file, and how to serve it from Apache.
              A mimetype beginning with 'text/' (or an absent mimetype) is
              treated as text.  Anything else is treated as binary.
            svn:externals  - A newline separated list of module specifiers,
              each of which consists of a relative directory path, optional
              revision flags, and an URL.  For example
                foo             http://example.com/repos/zig
                foo/bar -r 1234 http://example.com/repos/zag
        
        Valid options:
          -F [--file] arg          : read data from file ARG
          -q [--quiet]             : print as little as possible
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          --targets arg            : pass contents of file ARG as additional args
          -R [--recursive]         : descend recursively
          --revprop                : operate on a revision property (use with -r)
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --encoding arg           : treat value as being in charset encoding ARG
          --force                  : force operation to run
          --config-dir arg         : read user configuration files from directory ARG
        

        """
        raise SVNLibError("Not Implemented")
    
    def resolved(self, urls, _raw=0, **svnoptions):
        """
        resolved: Remove 'conflicted' state on working copy files or directories.

        SVN.resolved([file,...], _raw=0, **options)

        usage: resolved PATH...
        
          Note:  this subcommand does not semantically resolve conflicts or
          remove conflict markers; it merely removes the conflict-related
          artifact files and allows PATH to be committed again.
        
        Valid options:
          --targets arg            : pass contents of file ARG as additional args
          -R [--recursive]         : descend recursively
          -q [--quiet]             : print as little as possible
          --config-dir arg         : read user configuration files from directory ARG
        """
        if type(urls) in types.StringTypes:
            urls = [urls]
        argv = ['resolved'] + urls
        self._svnrun(argv, **svnoptions)
        # XXX no output is documented
    
    def revert(self, urls, _raw=0, **svnoptions):
        """
        revert: Restore pristine working copy file (undo most local edits).

        SVN.revert([file,...], _raw=0, **options)

        usage: revert PATH...
        
          Note:  this subcommand does not require network access, and resolves
          any conflicted states.  However, it does not restore removed directories.
        
        Valid options:
          --targets arg            : pass contents of file ARG as additional args
          -R [--recursive]         : descend recursively
          -q [--quiet]             : print as little as possible
          --config-dir arg         : read user configuration files from directory ARG
        """
        return self._simpleCommand('revert', urls, _raw, **svnoptions)
    
    def status(self, urls, _raw=0, **svnoptions):
        """
        status (stat, st): Print the status of working copy files and directories.
        
        SVN.status([file,...], _raw=0, **options)
        
        usage: status [PATH...]
        
          With no args, print only locally modified items (no network access).
          With -u, add working revision and server out-of-date information.
          With -v, print full revision information on every item.
        
          The first five columns in the output are each one character wide:
            First column: Says if item was added, deleted, or otherwise changed
              ' ' no modifications
              'A' Added
              'C' Conflicted
              'D' Deleted
              'G' Merged
              'I' Ignored
              'M' Modified
              'R' Replaced
              'X' item is unversioned, but is used by an externals definition
              '?' item is not under version control
              '!' item is missing (removed by non-svn command) or incomplete
              '~' versioned item obstructed by some item of a different kind
            Second column: Modifications of a file's or directory's properties
              ' ' no modifications
              'C' Conflicted
              'M' Modified
            Third column: Whether the working copy directory is locked
              ' ' not locked
              'L' locked
            Fourth column: Scheduled commit will contain addition-with-history
              ' ' no history scheduled with commit
              '+' history scheduled with commit
            Fifth column: Whether the item is switched relative to its parent
              ' ' normal
              'S' switched
            Sixth column: Repository lock token
              (without -u)
              ' ' no lock token
              'K' lock token present
              (with -u)
              ' ' not locked in repository, no lock token
              'K' locked in repository, lock toKen present
              'O' locked in repository, lock token in some Other working copy
              'T' locked in repository, lock token present but sTolen
              'B' not locked in repository, lock token present but Broken
        
          The out-of-date information appears in the eighth column (with -u):
              '*' a newer revision exists on the server
              ' ' the working copy is up to date
        
          Remaining fields are variable width and delimited by spaces:
            The working revision (with -u or -v)
            The last committed revision and last committed author (with -v)
            The working copy path is always the final field, so it can
              include spaces.
        
          Example output:
            svn status wc
             M     wc/bar.c
            A  +   wc/qax.c
        
            svn status -u wc
             M           965    wc/bar.c
                   *     965    wc/foo.c
            A  +         965    wc/qax.c
            Head revision:   981
        
            svn status --show-updates --verbose wc
             M           965       938 kfogel       wc/bar.c
                   *     965       922 sussman      wc/foo.c
            A  +         965       687 joe          wc/qax.c
                         965       687 joe          wc/zig.c
            Head revision:   981
        
        Valid options:
          -u [--show-updates]      : display update information
          -v [--verbose]           : print extra information
          -N [--non-recursive]     : operate on single directory only
          -q [--quiet]             : print as little as possible
          --no-ignore              : disregard default and svn:ignore property ignores
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG
        """

        opts = svnoptions.keys()
        updates = 'show_updates' in opts
        verbose = 'verbose' in opts
        _exp = r'^(?P<Status>.)(?P<Modified>.)(?P<Locked>.)(?P<History>.)(?P<Switched>.)'
        if updates or verbose:
            _exp += r'(?P<reserved1>.)(?P<reserved2>.)(?P<Sync>.)\s+(?P<Revision>\d+)'
        if verbose:
            _exp += r'\s+(?P<Last_Changed_Rev>\d+|\?)\s+(?P<Last_Changed_Author>.+?)'
        _exp += r'\s+(?P<Path>.*)$'
        
        if type(urls) in types.StringTypes:
            urls = [urls]
        argv = ['status'] + urls
        output, error, retval = self._svnrun(argv, **svnoptions)

        return _parseHits(output, error, retval, _raw, _exp)
    
    def switch(self, **svnoptions):
        """
        NOT IMPLEMENTED
        
        switch (sw): Update the working copy to a different URL.
        usage: 1. switch URL [PATH]
               2. switch --relocate FROM TO [PATH...]
        
          1. Update the working copy to mirror a new URL within the repository.
             This behaviour is similar to 'svn update', and is the way to
             move a working copy to a branch or tag within the same repository.
        
          2. Rewrite working copy URL metadata to reflect a syntactic change only.
             This is used when repository's root URL changes (such as a schema
             or hostname change) but your working copy still reflects the same
             directory within the same repository.
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -N [--non-recursive]     : operate on single directory only
          -q [--quiet]             : print as little as possible
          --diff3-cmd arg          : use ARG as merge command
          --relocate               : relocate via URL-rewriting
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG


        """
        raise SVNLibError("Not Implemented")
    
    def update(self, urls, _raw=0, **svnoptions):
        """
        update (up): Bring changes from the repository into the working copy.
        
        SVN.update([file,...], _raw=0, **options)
        
        usage: update [PATH...]
        
          If no revision given, bring working copy up-to-date with HEAD rev.
          Else synchronize working copy to revision given by -r.
        
          For each updated item a line will start with a character reporting the
          action taken.  These characters have the following meaning:
        
            A  Added
            D  Deleted
            U  Updated
            C  Conflict
            G  Merged
        
          A character in the first column signifies an update to the actual file,
          while updates to the file's properties are shown in the second column.
        
        Valid options:
          -r [--revision] arg      : ARG (some commands also take ARG1:ARG2 range)
                                     A revision argument can be one of:
                                        NUMBER       revision number
                                        "{" DATE "}" revision at start of the date
                                        "HEAD"       latest in repository
                                        "BASE"       base rev of item's working copy
                                        "COMMITTED"  last commit at or before BASE
                                        "PREV"       revision just before COMMITTED
          -N [--non-recursive]     : operate on single directory only
          -q [--quiet]             : print as little as possible
          --diff3-cmd arg          : use ARG as merge command
          --username arg           : specify a username ARG
          --password arg           : specify a password ARG
          --no-auth-cache          : do not cache authentication tokens
          --non-interactive        : do no interactive prompting
          --config-dir arg         : read user configuration files from directory ARG

        Returns a list of dicts representing commentary on each file *attempted* to be
        opened for add. Keys are: 'result', 'path'.
        
        If '_raw' is true then the a dictionary with the unprocessed results of calling
        svn is returned in addition to the processed results:
            {'stdout': <stdout>, 'stderr': <stderr>, 'retval': <retval>}
        """
        # Example output:
        #    A  newdir/toggle.c
        #    A  newdir/disclose.c
        #    A  newdir/launch.c
        #    D  newdir/README
        #    Updated to revision 32.
        #
        return self._simpleCommand('update', urls, _raw, **svnoptions)

    def statusEx(self, urls, _raw=0, **svnoptions):
        
        optv = getValidOpts(['env','cwd','targets','recursive','config_dir'], **svnoptions)
        info = self.info(urls, _raw, **optv)

        # status will fail for all url's if a single url is not under scc
        # control, so we must know that it is actually in the repository before
        # doing a status call on it
        stat = stat_urls = []
        if info and info[0]:
            for basename in info[0].keys():
                stat_urls.append(basename)
        if stat_urls:
            optv = getValidOpts(['env','cwd','show_updates','verbose','non_recursive','quiet',
                                 'no_ignore','username','password','no_auth_cache',
                                 'non_interactive','config_dir'], **svnoptions)
            stat = self.status(stat_urls, _raw, **optv)
        
        if _raw:
            info, info_out = info
            if stat:
                stat, stat_out = stat
            else:
                stat_out = {}

        for s in stat:
            # fix dict keys that have underscore (re limitation)
            if 'Last_Changed_Rev' in s:
                s['Last Changed Rev'] = s['Last_Changed_Rev']
                del s['Last_Changed_Rev']
            if 'Last_Changed_Author' in s:
                s['Last Changed Author'] = s['Last_Changed_Author']
                del s['Last_Changed_Author']

            if s['Path'] in info:
                info[s['Path']].update(s)
            else:
                info[s['Path']] = s
                
        if _raw:
            return info, (info_out, stat_out)
        return info



