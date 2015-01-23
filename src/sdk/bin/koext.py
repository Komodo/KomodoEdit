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

"""koext -- a tool for building Komodo extensions"""

__version_info__ = (0, 3, 0)
__version__ = '.'.join(map(str, __version_info__))


import os
from os.path import (join, exists, isdir, isfile, abspath, normcase,
                     splitext, dirname, expanduser, normpath, isabs,
                     basename)
import sys
import getopt
import time
import re
from pprint import pprint
from glob import glob
import traceback
import logging
from optparse import OptionParser

sys.path.insert(0, join(dirname(dirname(abspath(__file__))), "pylib"))
import cmdln
from cmdln import option
import koextlib
from koextlib import KoExtError



#---- global data

log = logging.getLogger("koext")



#---- main public stuff

class KoExtShell(cmdln.Cmdln):
    """${name} -- a tool for building Komodo extensions

    Usage:
        ${name} SUBCOMMAND [ARGS...]
        ${name} help SUBCOMMAND       # help on a specific command

    ${option_list}
    This tool provides some commands for working with and building
    Komodo extensions.

    ${command_list}
    ${help_list}
    """
    name = 'koext'
    version = __version__
    helpindent = '  '

    def get_optparser(self):
        parser = cmdln.Cmdln.get_optparser(self)
        parser.add_option("-v", "--verbose", dest="log_level",
                          action="store_const", const=logging.DEBUG,
                          help="more verbose output")
        parser.add_option("-q", "--quiet", dest="log_level",
                          action="store_const", const=logging.WARNING,
                          help="quieter output")
        parser.set_defaults(log_level=logging.INFO)
        return parser

    def postoptparse(self):
        global log
        log.setLevel(self.options.log_level)

    
    @option("-d", "--source-dir",
            help="The directory with the source for the extension "
                 "(defaults to the current dir)")
    @option("-i", "--include", action="append", dest="additional_includes",
            help="Include this file/directory in the resulting xpi")
    @option("-o", "--output-file", action="store", dest="xpi_path",
            help="The resulting xpi output file.")
    @option("--unjarred", action="store_true", dest="unjarred",
            help="Do not jar the chrome directory.")
    @option("--dev", action="store_const", dest="mode", const="dev",
            default="release", help="Build in development mode. See below.")
    @option("--disable-preprocessing", action="store_true",
            help="Disable preprocessing of '*.p.*' files in the source tree. "
                 "This is just paranioa in case the new preprocessing "
                 "facility here causes problems in building extensions.")
    @option("--define", action="append", dest="defines",
            help="Define a preprocessor variable, format 'name=value'.")
    def do_build(self, subcmd, opts):
        """${cmd_name}: build a Komodo extension

        ${cmd_usage}
        ${cmd_option_list}
        Using the "--dev" option has the following effects:
        1. The "MODE" preprocessor define is "dev", instead of the default
           "release", for preprocessing of "*.p.*" files in the source tree.
        2. The "support_devinstall" build option is enabled to support the
           use of `koext devinstall` (built bits are copied from the "build"
           dir to the source area for in-place usage).
        """
        if opts.source_dir is None:
            opts.source_dir = os.curdir
        ppdefines = {
            "MODE": opts.mode,
        }
        if opts.defines:
            for pp_definition in opts.defines:
                def_split = pp_definition.split("=", 1)
                if len(def_split) == 2:
                    name, value = def_split
                    ppdefines[name] = value
        if opts.disable_preprocessing:
            ppdefines = None
        koextlib.build_ext(opts.source_dir,
            support_devinstall=(opts.mode=="dev"),
            unjarred=opts.unjarred,
            ppdefines=ppdefines,
            additional_includes=opts.additional_includes,
            log=log,
            xpi_path=opts.xpi_path)

    @option("-d", "--source-dir",
            help="The directory with the source for the extension "
                 "(defaults to the current dir)")
    @option("--dev", action="store_const", dest="mode", const="dev",
            default="release",
            help="Build in development mode. See `koext help build`.")
    @option("--disable-preprocessing", action="store_true",
            help="Disable preprocessing of '*.p.*' files in the source tree. "
                 "See `koext help build`.")
    @option("--define", action="append", dest="defines",
            help="Define a preprocessor variable, format 'name=value'.")
    @option("-i", "--include", action="append", dest="additional_includes",
            help="Include this file/directory in the resulting xpi")
    @option("-o", "--output-file", action="store", dest="xpi_path",
            help="The resulting xpi output file.")
    @option("-p", "--packed", action="store_true", dest="packed",
            help="Installs as a zipped xpi file (default is to unpack it).")
    @option("--unjarred", action="store_true", dest="unjarred",
            help="Do not jar the chrome directory.")
    def _do_koinstall(self, subcmd, opts):
        """${cmd_name}: build and install this extension into a Komodo build

        ${cmd_usage}
        ${cmd_option_list}
        This command is for building *core* Komodo extensions into a Komodo
        build. This is *not* a command for installing an extension into a
        Komodo installation (either install the .xpi for use `koext devinstall`
        for that).
        """
        if opts.source_dir is None:
            opts.source_dir = os.curdir
        ppdefines = {
            "MODE": opts.mode,
        }
        if opts.defines:
            for pp_definition in opts.defines:
                def_split = pp_definition.split("=", 1)
                if len(def_split) == 2:
                    name, value = def_split
                    ppdefines[name] = value
        if opts.disable_preprocessing:
            ppdefines = None
        koextlib.komodo_build_install(opts.source_dir,
            ppdefines=ppdefines, log=log,
            unjarred=opts.unjarred,
            xpi_path=opts.xpi_path,
            distinstall=(subcmd == "distinstall"),
            additional_includes=opts.additional_includes,
            packed=opts.packed)

    @option("-d", "--source-dir",
            help="The directory with the source for the extension "
                 "(defaults to the current dir)")
    @option("--dev", action="store_const", dest="mode", const="dev",
            default="release",
            help="Build in development mode. See `koext help build`.")
    @option("--disable-preprocessing", action="store_true",
            help="Disable preprocessing of '*.p.*' files in the source tree. "
                 "See `koext help build`.")
    @option("--define", action="append", dest="defines",
            help="Define a preprocessor variable, format 'name=value'.")
    @option("-i", "--include", action="append", dest="additional_includes",
            help="Include this file/directory in the resulting xpi")
    @option("-o", "--output-file", action="store", dest="xpi_path",
            help="The resulting xpi output file.")
    @option("-p", "--packed", action="store_true", dest="packed",
            help="Installs as a zipped xpi file (default is to unpack it).")
    @option("--unjarred", action="store_true", dest="unjarred",
            help="Do not jar the chrome directory.")
    def _do_kodistinstall(self, subcmd, opts):
        """${cmd_name}: build and install this extension into a Komodo build

        ${cmd_usage}
        ${cmd_option_list}
        This command is for building *core* Komodo extensions into a Komodo
        build. This is *not* a command for installing an extension into a
        Komodo installation (either install the .xpi for use `koext devinstall`
        for that).
        """
        self._do_koinstall("distinstall", opts)

    @option("-d", "--dest-dir",
            help="The directory in which to extract into"
                 "(defaults to extensions dir)")
    def _do_kounpack(self, subcmd, opts, xpi_path):
        """${cmd_name}: unpack a .xpi file and install it into a Komodo build

        ${cmd_usage}
        ${cmd_option_list}
        This command is for installing *core* Komodo extensions into a Komodo
        build. This is *not* a command for installing an extension into a
        Komodo installation (either install the .xpi for use `koext devinstall`
        for that)."""
        koextlib.komodo_unpack_xpi(xpi_path, log=log, destdir=opts.dest_dir)

    def _do_kodistunpack(self, subcmd, opts, xpi_path):
        """${cmd_name}: unpack a .xpi file and install it into a Komodo build

        ${cmd_usage}
        ${cmd_option_list}
        This command is for installing *core* Komodo extensions into a Komodo
        build. This is *not* a command for installing an extension into a
        Komodo installation (either install the .xpi for use `koext devinstall`
        for that)."""
        koextlib.komodo_distunpack_xpi(xpi_path, log=log)

    @option("-d", "--source-dir",
            help="The directory with the source for the extension "
                 "(defaults to the current dir)")
    @option("-f", "--force", action="store_true", default=False,
            help="Force overwrite of extension link file, if necessary")
    def do_devinstall(self, subcmd, opts):
        """${cmd_name}: install link for development with current Komodo

        ${cmd_usage}
        ${cmd_option_list}
        Limitations:
        - Currently this only works in Komodo dev builds (i.e. won't work when using
          a Komodo SDK installed with a Komodo installer build).
        - Currently any *built* parts of the extension (e.g. binary components, jarring of
          chrome if not using 'chrome.p.manifest', built UDL lexers) will not
          get hooked up because a "build" directory is being used. Quickest
          solution is probably to update the "build" command to create built
          bits in-place.
        """
        if opts.source_dir is None:
            opts.source_dir = os.curdir
        koextlib.dev_install(opts.source_dir, force=opts.force, log=log)

    @option("--id",
            help="ID string, no spaces, typically of the form "
                 "'foo@example.com' (e.g. 'fuzzy_wuzzy@mydomain.com')")
    @option("--name",
            help="a short name for this extension (e.g. 'Fuzzy Wuzzy')")
    @option("--version", default="1.0.0", metavar="VER",
            help="starting version of the extension (default: 1.0.0)")
    @option("--desc", help="one sentence description of this extension",
            default="")
    @option("--creator", metavar="NAME",
            help="extension creator (typically your name, "
                 "e.g. 'Hugh Jackman')")
    @option("--homepage", metavar="URL", default="",
            help="URL at which to get information on this extension")
    def do_startext(self, subcmd, opts, dir):
        r"""${cmd_name}: create a Komodo extension source directory

        ${cmd_usage}
        ${cmd_option_list}
        Example:
            ${name} ${cmd_name} fuzzy --creator "Alan Jackson" \
                --desc "Support for the Fuzzy Wuzzy language." \
                --version 1.0.0 --name "Fuzzy Wuzzy"

        Create a new skeleton Komodo extension source directory.
        """
        koextlib.create_ext_skel(dir, name=opts.name, id=opts.id,
                                 version=opts.version, desc=opts.desc,
                                 creator=opts.creator,
                                 homepage=opts.homepage,
                                 log=log)

    @option("--is-html-based", action="store_true",
            help="indicate if this file type includes HTML")
    @option("--is-xml-based", action="store_true",
            help="indicate if this file type includes XML")
    @option("--ext",
            help="file extension for files of this language (e.g. '.pl')")
    @option("-d", "--source-dir",
            help="The directory with the source for the extension "
                 "(defaults to the current dir)")
    @option("-n", "--dry-run", action="store_true",
            help="do a dry-run")
    def do_startlang(self, subcmd, opts, lang):
        """${cmd_name}: generate stub files for a new UDL-based language

        ${cmd_usage}
        ${cmd_option_list}
        Example:
            ${name} ${cmd_name} RHTML --ext .rhtml --is-html-based

        Use this to get starter files for adding a *completely new
        language* to Komodo. This involves the following pieces:

        - An XPCOM component (written in Python) that gives basic data
          about the new language
        - A UDL-based lexer for syntax coloring of the new language.
          UDL stands for "User-Defined Language". It is a language (and
          compiler) for describing the syntax of a language.
          See `${name} help udl' and Komodo's UDL documentation for
          details on UDL.
        - Some "New File..." templates.
        """
        if opts.source_dir is None:
            opts.source_dir = os.curdir
        koextlib.create_udl_lang_skel(normpath(opts.source_dir),
                                      lang, ext=opts.ext,
                                      is_html_based=opts.is_html_based,
                                      is_xml_based=opts.is_xml_based,
                                      dry_run=opts.dry_run, log=log)


    @option("-d", "--source-dir",
            help="The directory with the source for the extension "
                 "(defaults to the current dir)")
    @option("-n", "--dry-run", action="store_true", default=False,
            help="do a dry-run")
    @option("-f", "--force", action="store_true", default=False,
            help="allow overwrite of existing stub files")
    def do_startcodeintel(self, subcmd, opts, lang):
        """${cmd_name}: generate stub files for codeintel support for a new language

        ${cmd_usage}
        ${cmd_option_list}

        Use this to get starter files for adding Code Intelligence
        support for a language for which Komodo does not already have
        support. "Code Intelligence" support any of:
        
        - autocomplete and calltips to aid with editing files of that
          language
        - scanning a file of this language to produce outline info for
          the Code Browser (Komodo IDE only)
        
        The files generated are "pylib/lang_$(LANG).py" and
        "pylib/cile_$(LANG).py". See the "Anatomy of a Komodo
        Extension" tutorial (TODO) for more information on how to
        author these stub files.
        """
        if opts.source_dir is None:
            opts.source_dir = os.curdir
        koextlib.create_codeintel_lang_skel(
            normpath(opts.source_dir), lang, dry_run=opts.dry_run,
            force=opts.force, log=log)

    def help_hooks(self):
        """overview of Komodo's extension hooks"""
        return """
            Many parts of Komodo's functionality can be extended with a
            Komodo extension. We call those "hooks" here. The following is
            a list of all extension hooks that Komodo currently supports.

            The "source tree files" sections below are conventions for
            placement of sources files. If you use these conventions, then
            `koext build' will automatically be able to build your extension
            properly.
            
            chrome
                Chrome is the collective term for XUL (content), JavaScript
                (content), CSS (skin), images (skin) and localized files
                (locale, typically DTDs) that can be used to extend the
                Komodo UI. This works in Komodo extensions in exactly the
                same way as any other Mozilla-base application (such as
                Firefox). See `koext help chrome' for some tips.
                
                source tree files:
                    chrome.manifest
                    content/            # XUL overlays, dialogs and JavaScript
                    skin/               # CSS
                    locale/             # localized files (typically DTDs)

            XPCOM components
                XPCOM components are placed here. These can be written in
                Python or JavaScript. (C++-based components are possible
                as well, but currently the Komodo SDK does not support
                building them.)
                
                source files:
                    components/
                        *.idl           # interface definitions
                        *.py            # PyXPCOM components
                        *.js            # JavaScript XPCOM components

            templates
                A file hierarchy under here maps into Komodo's "New File"
                dialog. For example, "templates/Common/Foo.pl" will result
                in a new Perl file template called "Foo" in the "Common"
                folder of the "New File" dialog.
                
                source files:
                    templates/

            Project templates
                A file hierarchy under here maps into Komodo's "New
                Project from Template" dialog. For example,
                "project-templates/Common/ILoveChocolate.kpz" will result
                in a new project template called "ILoveChocolate" in the
                "Common" folder of the "New Project from Template" dialog.
                Note: You must put templates in a $category sub-folder.
                
                source files:
                    project-templates/$category

            lexers
                Komodo User-Defined Languages (UDL) system provides a
                facility for writing regular expression, state-based lexers
                for new languages (including for multi-lang languages).
                ".lexres" files are built from ".udl" source files with
                the "luddite" tool (in this SDK). See `koext help udl' and
                Komodo's UDL documentation for more details.
                
                source files:
                    udl/
                        *-mainlex.udl   # a .lexres will be build for each of these
                        *.udl           # support files to be included by
                                        #   "*-mainlex.udl" files

            XML catalogs
                An extension can include an XML catalog (and associated
                schemas -- DTDs, XML Schemas, Relax NG) defining
                namespace to schema mappings for XML autocomplete.
                
                source files:
                    xmlcatalogs/
                        catalog.xml
                        *.dtd
                        *.rng

            API catalogs
                An extension can include API catalogs to provide autocomplete
                and calltips for 3rd party libraries. An API catalog is a CIX
                file (an XML dialect) that defines the API of a
                library/project/toolkit.
                
                source files:
                    apicatalogs/        # .cix files here will be included
                                        #   in the API catalog list in the
                                        #   "Code Intelligence" prefs panel

            Python modules
                An extension can supply Python modules by placing then in
                the "pylib" directory of the extension. This "pylib" directory
                will be appended to Komodo's Python runtime sys.path.
                
                source files:
                    pylib/

            codeintel
                An extension can provide the Code
                Intelligence logic (for autocomplete and calltips, for
                "Jump to Definition" and for the Code Browser in Komodo IDE)
                for new languages.

                source files:
                    pylib/              # lang_*.py files here are picked up
                                        #   by the codeintel system.

        """

    def help_gettingstarted(self):
        """how building a Komodo extension is done"""
        return """
            Getting Started building a Komodo Extension
            -------------------------------------------
            
            The typical process for building a Komodo extension is:
            
            1. Create a starter extension source directory with:

                koext startext fuzzy_wuzzy ...

            2. Add the necessary files to implement specific functionality
               using one or more of Komodo's extension hooks. For example,
               you might add the following to add a dialog to Komodo:
               
                fuzzy_wuzzy/chrome.manifest
                fuzzy_wuzzy/content/dialog_fuzzy.xul
                fuzzy_wuzzy/content/dialog_fuzzy.js
            
               or you might add the following to add the following to a
               template to Komodo "New File" dialog:
               
                fuzzy_wuzzy/templates/Common/Fuzzy.wuzzy

               See `koext help hooks', the other koext help topics and
               Komodo's documentation for full details.
            
            3. Build your extension (a Komodo extension package is a `.xpi'
               file) with:
               
                cd fuzzy_wuzzy
                koext build
            
            4. Upload and announce you extension on Komodo Addons site:
            
                http://community.activestate.com/addons
        """

    def help_chrome(self):
        """some tips for writing extension chrome"""
        try:
            ext_info = koextlib.ExtensionInfo()
        except KoExtError:
            codename = 'myext'
        else:
            codename = ext_info.codename

        return """
            # How to add "content"
            
            If you will have any chrome "content" (any XUL, JavaScript or XBL)
            in your extension you must add a line like the following to
            "chrome.manifest":
            
                content %(codename)s jar:%(codename)s.jar!/content/%(codename)s xpcnativewrappers=yes
                
            Create a "content" directory in your source dir. You can now add
            .xul and .js files under the "content" directory. The new
            "chrome.manifest" line creates a runtime mapping from, for example,
            "chrome://%(codename)s/content/foo.xul" to "content/foo.xul"
            in your extension.
            
            
            # How to add "skin"
            
            If your extension will have any chrome "skin" (typically CSS
            and images go here) then you must add a line like the following
            to "chrome.manifest":
            
                skin %(codename)s classic/1.0 %(codename)s/skin/
            
            Create a "skin" directory in your source dir and place your
            CSS and images there. In your XUL, refer to these files with
            "chrome://%(codename)s/skin/...".
            
            Here "classic/1.0" refers to the default theme in Komodo.
            Currently there aren't any other Komodo themes, but if one or
            more were added you would be able to add additional mapping in
            "chrome.manifest" to allow your extension UI to adapt to the
            different themes.
            
            # How to add an overlay
            
            TODO
            
            # How to add "locale" info
            
            TODO
            
        """ % locals()


    def help_udl(self):
        "TODO"
        return "TODO"
    def help_codeintel(self):
        "TODO"
        return "TODO"


#---- internal support functions

# Recipe: pretty_logging (0.1+)
class _PerLevelFormatter(logging.Formatter):
    """Allow multiple format string -- depending on the log level.
    
    A "fmtFromLevel" optional arg is added to the constructor. It can be
    a dictionary mapping a log record level to a format string. The
    usual "fmt" argument acts as the default.
    """
    def __init__(self, fmt=None, datefmt=None, fmtFromLevel=None):
        logging.Formatter.__init__(self, fmt, datefmt)
        if fmtFromLevel is None:
            self.fmtFromLevel = {}
        else:
            self.fmtFromLevel = fmtFromLevel
    def format(self, record):
        record.levelname = record.levelname.lower()
        if record.levelno in self.fmtFromLevel:
            #XXX This is a non-threadsafe HACK. Really the base Formatter
            #    class should provide a hook accessor for the _fmt
            #    attribute. *Could* add a lock guard here (overkill?).
            _saved_fmt = self._fmt
            self._fmt = self.fmtFromLevel[record.levelno]
            try:
                return logging.Formatter.format(self, record)
            finally:
                self._fmt = _saved_fmt
        else:
            return logging.Formatter.format(self, record)

def _setup_logging():
    hdlr = logging.StreamHandler()
    defaultFmt = "%(name)s: %(levelname)s: %(message)s"
    infoFmt = "%(message)s"
    fmtFromLevel={logging.INFO: "%(name)s: %(message)s"}
    fmtr = _PerLevelFormatter(defaultFmt, fmtFromLevel=fmtFromLevel)
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)



#---- mainline

def _do_main(argv):
    shell = KoExtShell()
    return shell.main(argv)

def main(argv=sys.argv):
    _setup_logging()
    try:
        retval = _do_main(argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except SystemExit:
        raise
    except:
        skip_it = False
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            exc_class, exc, tb = exc_info
            if isinstance(exc, IOError) and exc.args[0] == 32:
                # Skip 'IOError: [Errno 32] Broken pipe'.
                skip_it = True
            if not skip_it:
                #tb_path, tb_lineno, tb_func = traceback.extract_tb(tb)[-1][:3]
                #log.error("%s (%s:%s in %s)", exc_info[1], tb_path,
                #          tb_lineno, tb_func)
                log.error(exc_info[1])
        else:  # string exception
            log.error(exc_info[0])
        if not skip_it:
            if log.isEnabledFor(logging.DEBUG):
                print
                traceback.print_exception(*exc_info)
            sys.exit(1)
    else:
        sys.exit(retval)

if __name__ == "__main__":
    main(sys.argv)


