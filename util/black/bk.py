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

# A build system assistance utility.
# 
# It can be used as a front end for development commands for a project and/or
# to provide project configuration services (i.e. discover system and user
# chosen information and generate "config" files that can be subsequently
# used by the build system at build time, a la autoconf).
#

import sys, os, getopt, stat, re, string, shutil, urllib, tempfile, cmd
import functools

# put the Black Python lib directory on sys.path
installDir = os.path.abspath(os.path.normpath(os.path.dirname(sys.argv[0])))
pythonLibDir = os.path.join(installDir, "lib", "python")
sys.path.insert(0, pythonLibDir)
del pythonLibDir
del installDir

import tmOutput, tmCmd, tmUtils, tmShUtil
import black.configure, black.configure.std, black.configure.mozilla


#---- globals

verbosity = 0           # <0==quiet, 0==normal, >0==versbose
blackFileName = None    # the configuration filename
blackFile = None        # a black file object [Currently this is just
                        # the imported Blackfile.py module object.]


#---- output control

out = tmOutput.MarkedUpOutput()
black.configure.out =\
    black.configure.std.out =\
    black.configure.mozilla.out = out
# tell the "tm" modules to use the same output controller/stream
tmCmd.out = tmUtils.out = tmShUtil.out = out



#---- other helper stuff

def FindBlackFile():
    """Look for an appropriate Blackfile.
    Algorithm: Walk up the directory tree from the current directory,
    looking for a "Blackfile.py".
    """
    base = "Blackfile.py"
    currDir = os.getcwd()
    retval = None
    while currDir:
        fileName = os.path.join(currDir, base)
        if os.path.isfile(fileName):
            retval = fileName
            break
        else:
            parent = os.path.dirname(currDir)
            if parent == currDir:
                break
            else:
                currDir = parent
    return retval 


def ParseBlackFile(blackFileName):
    """Return an object with the black file configuration items as attrs.
    Currently this just presumes that the Blackfile is Python module.
    """
    import imp
    dirName, baseName = os.path.split(blackFileName)
    baseName, ext = os.path.splitext(baseName) 
    file, pathname, description = imp.find_module(baseName, [dirName])
    try:
        blackfile = imp.load_module(baseName, file, pathname, description)
    except ImportError, e:
        out.startErrorItem()
        out.write("black: There was a problem importing your project "\
            "configuration file: '%s'\n" % blackFileName)
        out.write("\n")
        out.endErrorItem()
        raise
    return blackfile


def HasOverride(blackFile, commandName):
    """Return true iff the given project configuration overrides the given
    command name.
    """
    return hasattr(blackFile, "commandOverrides") and\
           blackFile.commandOverrides.has_key(commandName)


def RunOverride(blackFile, projectConfig, commandName, argv):
    """Execute the given command override."""
    commmandOverride = blackFile.commandOverrides[commandName]
    executeDir = os.path.dirname(blackFileName)
    if callable(commmandOverride):
        if verbosity > 0:
            out.write("Changing dir to '%s'.\n" % executeDir)
            out.write("Executing command override: '%s'\n" %\
                      commmandOverride)
        os.chdir(executeDir)
        return commmandOverride(projectConfig, argv)

    elif type(commmandOverride) == type.StringType:
        if verbosity > 0:
            out.write("Changing dir to '%s'.\n" % executeDir)
            out.write("Executing command override: '%s'\n" %\
                      commmandOverride)
        os.chdir(executeDir)
        #XXX should quote command line args that have spaces
        #XXX will this log properly or shoudl tmShUtil.RunCommands be
        #    used?
        #XXX need a test case for a string command override
        return os.system(commmandOverride + " ".join(argv[1:]))

    else:
        out.startErrorItem()
        out.write("error: A command override must be a callable object "\
                  "or a string. The override in %s is neither.\n" %\
                  blackFileName)
        out.endErrorItem()
        return 1



#---- Black Dev Shell
class Shell(tmCmd.AugmentedListCmd):
    """
    Black -- an interface to some build system

        Black provides a defined interface to a build system for
        an arbitrary project. Such a project must have a
        Blackfile.py it its root directory.
        
    Usage:
        bk help             this help
        bk help commands    list the available commands
        bk help <command>   help on a specific command

    Options:
        -f <blackfile>      specify a Black configuration file [default
                            is "Blackfile.py" in the current or ancestral
                            directory]
        -q, --quiet         quiet output
        -v, --verbose       verbose output
        --version           print Black's version and exit
        
    """
    def __init__(self, cmd_overrides):
        tmCmd.AugmentedListCmd.__init__(self)
        self.name = "bk"
        for cmd, handler in cmd_overrides.items():
            func_name = "do_" + cmd
            if not hasattr(self, func_name):
                self._make_do_wrapper(cmd, handler)


    def helpdefault(self):
        # tailor default help to the Blackfile, if one is found
        global blackFile, blackFileName
        if blackFile:
            template_head = """
    %(title)s

        bk help             this help
        bk help commands    list the available commands
        bk help <command>   help on a specific command
"""
            template = """
        bk configure        configure to build %(name)s
        bk build            build %(name)s
        bk clean            clean %(name)s
        bk run              run the %(name)s app
        bk start <command>  execute a command in the configured environment
        bk test             run %(name)ss self-test suite

        bk package          package up %(name)s bits
        bk upload           upload %(name)s bits to staging area
"""
            template_tail = """
    Options:
        -f <blackfile>      specify a Black configuration file [default
                            is "Blackfile.py" in the current or ancestral
                            directory]
        -q, --quiet         quiet output
        -v, --verbose       verbose output
        --version           print Black's version and exit

"""
            # if the project is configured then use that information
            try:
                projectConfig = black.configure.ImportProjectConfig(
                    blackFileName, blackFile)
            except ImportError:
                projectConfig = None
            if projectConfig and hasattr(projectConfig, "name"):
                name = "project '%s'" % projectConfig.name
                title = "Development shell for %s" % name
            else:
                name = ""
                title = "Development shell for project in '%s'" % \
                        os.path.dirname(blackFileName)
            template = getattr(blackFile, "helpTemplate", template)
            template = template_head + template + template_tail
            out.wordWrapping = 0
            out.write(template % {"title":title, "name":name})
            out.wordWrapping = 1
        else:
            tmCmd.AugmentedListCmd.helpdefault(self)
    

    def do_build(self, argv):
        """build what is currently configured to be built
        
        bk build [configuration args] [build args]

            "configuration args" are all of the form --conf-<configurearg>.
            All configuration args must come before any build args.
            If any configuration args are present then the equivalent of
            the follow steps are taken:
                bk configure <previous conf args> <new conf args>
                bk build
                bk configure <previous conf args>
            This is basically a shortcut for doing a single build with
            a specific configuration, e.g.:
                bk build --conf-with-somefeature
            "--" can be used to terminate the list of configuration args,
            e.g.
                bk build --conf-a-conf-arg -- --conf-not-a-conf-arg

            "build args" are all passed to the underlieing build process.
        """
        global blackFile, blackFileName
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'build' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'build' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # look for configuration args
        # XXX this will fail for configuration options that take arguments
        #     and where the argument is seperated from the option with
        #     whitespace
        newConfArgs = []
        newArgv = []
        STATE_COMMAND_NAME, STATE_CONF_ARGS, STATE_BUILD_ARGS = range(3)
        state = STATE_COMMAND_NAME
        for arg in argv:
            if state == STATE_COMMAND_NAME:
                newArgv.append( arg )
                state = STATE_CONF_ARGS
            elif state == STATE_CONF_ARGS:
                if arg == "--":
                    state = STATE_BUILD_ARGS
                elif arg.startswith("--conf-"):
                    arg = arg[len("--conf-"):]
                    if len(arg) == 1:
                        arg = "-" + arg
                    else:
                        arg = "--" + arg
                    newConfArgs.append( arg )
                else:
                    newArgv.append( arg )
                    state = STATE_BUILD_ARGS
            elif state == STATE_BUILD_ARGS:
                newArgv.append( arg )
        argv = newArgv
        if newConfArgs:
            origConfArgs = projectConfig.blackConfigureOptions

        # Currently Black has no ability to build a project. However,
        # it can invoke a custom build procedure as expressed in
        # the commandOverrides['build'] variable in the project Blackfile.py.
        if HasOverride(blackFile, "build"):
            if newConfArgs:
                self.do_reconfigure(["reconfigure"] + newConfArgs)
            retval = RunOverride(blackFile, projectConfig, "build", argv)
            if newConfArgs:
                self.do_configure(["configure"] + origConfArgs)
            return retval
        else:
            out.startErrorItem()
            out.write("warning: Black currently does not know how to "\
                      "build anything unless you override the build command "\
                      "in your Blackfile. '%s' does not do this." %\
                      blackFileName)
            out.endErrorItem()
                

    def do_clean(self, argv):
        """clean what is currently configured to be built
        
        bk clean [optional args depending on configuration]
        """
        global blackFile, blackFileName
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'clean' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'clean' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # Currently Black has no knowledge of how to clean a project. However,
        # it can invoke a custom clean procedure as expressed in
        # the commandOverrides['clean'] variable in the project Blackfile.py.
        if HasOverride(blackFile, "clean"):
            return RunOverride(blackFile, projectConfig, "clean", argv)
        else:
            out.startErrorItem()
            out.write("warning: Black currently does not know how to "\
                      "clean anything unless you override the clean command "\
                      "in your Blackfile. '%s' does not do this." %\
                      blackFileName)
            out.endErrorItem()
                

    def do_distclean(self, argv):
        """completely clean everything
        
        bk distclean [optional args depending on configuration]
        """
        global blackFile, blackFileName
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'distclean' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'distclean' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # Currently Black has no knowledge of how to clean a project. However,
        # it can invoke a custom clean procedure as expressed in
        # the commandOverrides['clean'] variable in the project Blackfile.py.
        if HasOverride(blackFile, "distclean"):
            return RunOverride(blackFile, projectConfig, "distclean", argv)
        else:
            out.startErrorItem()
            out.write("warning: Black currently does not know how to "\
                      "distclean anything unless you override the distclean"\
                      "command in your Blackfile. '%s' does not do this." %\
                      blackFileName)
            out.endErrorItem()


    def do_run(self, argv):
        """run the application for the current project
        
        bk run [arguments to application]
        """
        global blackFile, blackFileName
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'run' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'run' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # There can be no default "run" command. A project must override
        # this.
        if HasOverride(blackFile, "run"):
            return RunOverride(blackFile, projectConfig, "run", argv)
        else:
            out.startErrorItem()
            if hasattr(projectConfig, "name"):
                name = "project '%s'" % projectConfig.name
            else:
                name = ""
            out.write("warning: Don't know how to 'run' %s. The "\
                      "project Blackfile (%s) must describe how to do "\
                      "this.\n" % (name, blackFileName))
            out.endErrorItem()
                

    def do_start(self, argv):
        """run a command in the configured environment"""
        global blackFile
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'start' with no project "\
                "configuration: no Blackfile.py was found")

        # import the project configure module
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'start' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1
        
        quotedArgs = []
        args = argv[1:]
        if args[0] == "-v":
            verbose = True
            del args[0]
        else:
            verbose = False
        for arg in args:
            if " " in arg:
                quotedArgs.append('"%s"' % arg)
            else:
                quotedArgs.append(arg)
        argString = " ".join(quotedArgs)
        curDir = os.getcwd()
        os.chdir(gCallDir)
        if verbose:
            os.environ["KOMODO_VERBOSE"] = "1"
        try:
            retval = tmShUtil.RunInContext(projectConfig.envScriptName,
                                           [argString])
        finally:
            os.chdir(curDir)
        return retval

    def do_package(self, argv):
        """package up bits
        
        bk package [<args...>]
        """
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'package' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'package' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # There can be no default "package" command. A project must override
        # this.
        if HasOverride(blackFile, "package"):
            return RunOverride(blackFile, projectConfig, "package", argv)
        else:
            out.startErrorItem()
            if hasattr(projectConfig, "name"):
                name = "project '%s'" % projectConfig.name
            else:
                name = ""
            out.write("warning: Don't know how to 'package' %s. The "\
                      "project Blackfile (%s) must describe how to do "\
                      "this.\n" % (name, blackFileName))
            out.endErrorItem()

    def do_image(self, argv):
        """create the install image

            bk image [<args...>]

        This is a total HACK just for Komodo -- the only user of Black,
        so that is okay.
        """
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'image' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'image' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # There can be no default "image" command. A project must override
        # this.
        if HasOverride(blackFile, "image"):
            return RunOverride(blackFile, projectConfig, "image", argv)
        else:
            out.startErrorItem()
            if hasattr(projectConfig, "name"):
                name = "project '%s'" % projectConfig.name
            else:
                name = ""
            out.write("warning: Don't know how to 'image' %s. The "\
                      "project Blackfile (%s) must describe how to do "\
                      "this.\n" % (name, blackFileName))
            out.endErrorItem()

    def do_grok(self, argv):
        """search our OpenGrok database

            bk grok <search-term>
        """
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'grok' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'grok' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # There can be no default "grok" command. A project must override
        # this.
        if HasOverride(blackFile, "grok"):
            return RunOverride(blackFile, projectConfig, "grok", argv)
        else:
            out.startErrorItem()
            if hasattr(projectConfig, "name"):
                name = "project '%s'" % projectConfig.name
            else:
                name = ""
            out.write("warning: Don't know how to 'grok' %s. The "\
                      "project Blackfile (%s) must describe how to do "\
                      "this.\n" % (name, blackFileName))
            out.endErrorItem()

    def do_upload(self, argv):
        """upload built packages to staging area

        bk upload <base-upload-dir>

        This is a total HACK just for Komodo -- the only user of Black,
        so that is okay.
        """
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'upload' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'upload' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # There can be no default "upload" command. A project must override
        # this.
        if HasOverride(blackFile, "upload"):
            return RunOverride(blackFile, projectConfig, "upload", argv)
        else:
            out.startErrorItem()
            if hasattr(projectConfig, "name"):
                name = "project '%s'" % projectConfig.name
            else:
                name = ""
            out.write("warning: Don't know how to 'upload' %s. The "\
                      "project Blackfile (%s) must describe how to do "\
                      "this.\n" % (name, blackFileName))
            out.endErrorItem()

    def do_cleanprefs(self, argv):
        """clean Komodo/Mozilla prefs

            bk cleanprefs [<args...>]

        This is a total HACK just for Komodo -- the only user of Black,
        so that is okay.
        """
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'cleanprefs' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'cleanprefs' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # There can be no default "cleanprefs" command. A project must override
        # this.
        if HasOverride(blackFile, "cleanprefs"):
            return RunOverride(blackFile, projectConfig, "cleanprefs", argv)
        else:
            out.startErrorItem()
            if hasattr(projectConfig, "name"):
                name = "project '%s'" % projectConfig.name
            else:
                name = ""
            out.write("warning: Don't know how to 'cleanprefs' %s. The "\
                      "project Blackfile (%s) must describe how to do "\
                      "this.\n" % (name, blackFileName))
            out.endErrorItem()

    def do_configure(self, argv):
        global blackFile, blackFileName
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'configure' with no project "\
                "configuration: no Blackfile.py was found")

        # configure away
        from black.configure import Configure
        return Configure(argv[1:], blackFileName, blackFile)

    def _make_do_wrapper(self, cmd, handler):
        """Generate a wrapper for an unknown command, and adds a handler for it.
        @param cmd {str} The command to execute, e.g. "build"
        @throws ValueError if cmd already has a handler
        """
        func_name = "do_" + cmd
        if hasattr(self, func_name):
            raise ValueError("Can't make new wrapper for command '%s', handler "
                             "for it already exists" % (cmd,))
        @functools.wraps(handler)
        def handle(argv):
            # die if there is no project configuration
            if not blackFile:
                raise black.BlackError("attempted 'cleanprefs' with no project "\
                    "configuration: no Blackfile.py was found")
            try:
                projectConfig = black.configure.ImportProjectConfig(
                    blackFileName, blackFile)
            except ImportError:
                out.startErrorItem()
                out.write("error: Attempted '%s' command without having "
                          "configured. You must first configure your project.\n"
                          % (cmd,))
                out.endErrorItem()
                return 1
            if HasOverride(blackFile, cmd):
                return RunOverride(blackFile, projectConfig, cmd, argv)
            raise black.BlackError("attempted to run command '%s', but the "
                                   "handler disappeared.\n" % (cmd,))
        setattr(self, func_name, handle)

    def help_configure(self):
        # print the available configuration options
        template = """
    configure the (%(name)s)

    bk configure [options...]

        This will configure the Black build system for the current
        project (%(name)s). Subsequent "bk" commands will
        use this configuration for doing their work.

    Options:
"""
        # if the project is configured then use that information
        if not blackFile:
            out.write(template % {"name":"current project (<none found>)"})
            out.write("        <none, because no project was specified>\n")
        else:
            try:
                projectConfig = black.configure.ImportProjectConfig(
                    blackFileName, blackFile)
            except ImportError:
                projectConfig = None
            if projectConfig and hasattr(projectConfig, "name"):
                name = "project '%s'" % projectConfig.name
            else:
                name = ""
            out.write(template % {"name":name})

            items = black.configure.Items(blackFile.configuration)
            for name, item in items.items():
                if hasattr(item, "optionHelp") and item.optionHelp:
                    out.write(item.optionHelp)
            out.write("\n\n")


    def do_reconfigure(self, argv):
        """reconfigure with the addition options

        bk reconfigure [options]

            This is really only currently useful for reconfiguring between
            changes in the "configure" infrastructure. 
            
            "options" can be specified to have the "configure" be run with
            the options with which the project was last configured PLUS
            the new given options, e.g.
                bk configure --foo
                ...
                bk reconfigure --bar
            has the same effect as:
                bk configure --foo --bar
            
            Note that this is a stupid appending of the options as opposed to
            an intelligent merging or related options, e.g.
                bk reconfigure --debug
            could result in:
                bk configure --release ... --debug
            Behaviour depends on the specific configuration items for that
            project.
        """
        global blackFile
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'reconfigure' with no project "\
                "configuration: no Blackfile.py was found")

        # import the project configure module
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'reconfigure' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # just call configure with the previously used options (found in the
        # black standard configuration item: "blackConfigureOptions")
        return self.do_configure(["configure"] +\
                                 projectConfig.blackConfigureOptions +\
                                 argv[1:])


    def do_test(self, argv):
        """run self-test
        
        bk test [options]
        """
        global blackFile, blackFileName
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'test' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'test' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # Currently Black has no knowledge of how to 'test' a project. However,
        # it can invoke a custom 'test' procedure as expressed in
        # the commandOverrides['test'] variable in the project Blackfile.py.
        if HasOverride(blackFile, "test"):
            return RunOverride(blackFile, projectConfig, "test", argv)
        else:
            out.startErrorItem()
            out.write("warning: Black currently does not know how to "\
                      "test anything unless you override the 'test' command "\
                      "in your Blackfile. '%s' does not do this." %\
                      blackFileName)
            out.endErrorItem()

    def do_perf(self, argv):
        """run self-perf
        
        bk perf [options]
        """
        global blackFile, blackFileName
        # die if there is no project configuration
        if not blackFile:
            raise black.BlackError("attempted 'perf' with no project "\
                "configuration: no Blackfile.py was found")
        try:
            projectConfig = black.configure.ImportProjectConfig(
                blackFileName, blackFile)
        except ImportError:
            out.startErrorItem()
            out.write("error: Attempted 'perf' command without having "\
                      "configured. You must first configure your project.\n")
            out.endErrorItem()
            return 1

        # Currently Black has no knowledge of how to clean a project. However,
        # it can invoke a custom clean procedure as expressed in
        # the commandOverrides['clean'] variable in the project Blackfile.py.
        if HasOverride(blackFile, "perf"):
            return RunOverride(blackFile, projectConfig, "perf", argv)
        else:
            out.startErrorItem()
            out.write("warning: Black currently does not know how to "\
                      "perf anything unless you override the clean command "\
                      "in your Blackfile. '%s' does not do this." %\
                      blackFileName)
            out.endErrorItem()



#---- script mainline

if __name__ == '__main__':
    # process options
    #   various      set the verbose/interaction detail level
    try:
        optlist, args = getopt.getopt(sys.argv[1:], 'vqf:',\
            ['quiet', 'verbose', 'version'])
    except getopt.GetoptError, msg:
        out.startErrorItem()
        out.write("%s: error in options: %s\n" % (sys.argv[0], msg))
        out.write("Try 'bk help'.")
        out.endErrorItem()
        sys.exit(1)
    for opt,optarg in optlist:
        if opt == "--version":
            import black
            out.write("Black %s\n" % black.GetPrettyVersion())
            sys.exit(0)
        if opt in ('-q', '--quiet'):
            tmCmd.verbosity =\
                tmUtils.verbosity =\
                tmShUtil.verbosity =\
                black.configure.verbosity =\
                black.configure.std.verbosity =\
                black.configure.mozilla.verbosity =\
                verbosity = -1
        elif opt in ('-v', '--verbose'):
            tmCmd.verbosity =\
                tmUtils.verbosity =\
                tmShUtil.verbosity =\
                black.configure.verbosity =\
                black.configure.std.verbosity =\
                black.configure.mozilla.verbosity =\
                verbosity = 1
        elif opt == '-f':
            blackFileName = os.path.abspath(os.path.normpath(optarg))
            if not os.path.isfile(blackFileName):
                out.startErrorItem()
                out.write("%s: error in options: the given blackfile (%s) "\
                    "does not exist\n" % (sys.argv[0], optarg))
                out.endErrorItem()
                blackFileName = None
                sys.exit(1)


    # determine the black configuration
    # The Blackfile location (and hence the project root) is determined as
    # follows:
    #   1. If "-f <blackfile>" is specified, that is used.
    #   2. Else if a Blackfile.py is found in an ancestral directory, then that
    #      is used.
    #   3. Else if the BLACKFILE_FALLBACK environment variable is defined,
    #      then that is used.
    if not blackFileName:
        blackFileName = FindBlackFile()
    if not blackFileName and os.environ.has_key("BLACKFILE_FALLBACK"):
        blackFileName = os.environ["BLACKFILE_FALLBACK"]
        if verbosity > 0:
            out.write("black: using BLACKFILE_FALLBACK (%s) to find "\
                      "Blackfile\n" % blackFileName)
        if not os.path.isfile(blackFileName):
            if verbosity > 0:
                out.write("black: '%s' (BLACKFILE_FALLBACK) is not a file. "\
                          "Silently skipping it.\n" % blackFileName)
            blackFileName = None
    global gCallDir
    gCallDir = os.getcwd()
    if blackFileName:
        os.chdir(os.path.dirname(blackFileName))
        try:
            blackFile = ParseBlackFile(blackFileName)
        except black.BlackError, e:
            out.write("\n")
            out.startErrorItem()
            out.write("black: error parsing blackfile '%s': %s" %\
                      (blackFileName, e))
            out.endErrorItem()
            if verbosity > 0:
                out.write("\n")
                raise
            else:
                sys.exit(1)

    # run the given command
    try:
        shell = Shell(getattr(blackFile, "commandOverrides", {}))
        retval = tmCmd.OneCmd(shell, args)
        sys.exit(retval)
    except black.BlackError, msg:
        out.write("\n")
        out.startErrorItem()
        out.write("black: error running '%s': %s" % (" ".join(args), msg))
        out.endErrorItem()
        if verbosity > 0:
            out.write("\n")
            raise
        else:
            sys.exit(1)
        
