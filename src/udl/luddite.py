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

r"""A command-line interface for managing UDL (User-Defined Language)
files for Komodo.
"""

import os
from os.path import basename, dirname, join, exists, abspath, splitext
import sys
import re
import logging
from glob import glob
from pprint import pprint
import webbrowser

def _set_lib_path():
    if exists(join(dirname(__file__), "ludditelib")):  # dev layout
        pass
    else: # install layout (in Komodo SDK)
        sys.path.insert(0, join(dirname(dirname(abspath(__file__))), "pylib"))
_set_lib_path()

from ludditelib import cmdln
from ludditelib import parser, gen, constants, commands
from ludditelib.common import LudditeError, __version__, \
                              guid_pat, norm_guid, generate_guid


log = logging.getLogger("luddite")


#---- command line interface

class Shell(cmdln.Cmdln):
    """
    luddite: compile and build Komodo language extensions

    usage:
        ${name} SUBCOMMAND [ARGS...]
        ${name} help SUBCOMMAND

    Language syntax-highlighting in Komodo requires a lexer. For most of
    Komodo's core supported languages these lexers are written in C++.
    However, as of Komodo 4, you can define custom lexers for languages that
    Komodo doesn't support out of the box. This system is called UDL -- for
    User-Defined Languages.
    
    Luddite is a tool for building and packaging a Komodo language
    extension. The typical process is:
    
    1. Use the 'koext' tool (also part of the Komodo SDK) to start a Komodo
       extension source tree and create stub files for a new Komodo language.
       
            koext startext fuzzy_language
            cd fuzzy_language/
            koext startlang fuzzy
    
    2. Author the 'udl/LANG-mainlex.udl' file defining syntax highlighting
       rules for your language and the 'components/koFuzzy_UDL_Language.py'
       language service as appropriate.
       
       The 'luddite lex' and 'luddite lexhtml' commands can help you debug
       your .udl code.

    3. Build the extension. 'koext' knows how to compile your UDL code into
       the '.lexres' files that Komodo uses at runtime.
    
            koext build

    4. Upload and announce your new extension on Komodo's add-ons site:
    
            http://community.activestate.com/addons

    For more information on writing .udl files see Komodo's UDL
    documentation.

    ${option_list}
    ${command_list}
    ${help_list}
    """
    name = "luddite"
    version = __version__
    helpindent = ' '*2

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

    @cmdln.option("-d", "--output-dir",
                  help="specify the output dir for the .lexres file (by "
                       "default the same dir as the input .udl path")
    @cmdln.option("-I", dest="include_dirs", action="append",
                  help="extra dirs to search for include'd UDL files")
    def do_just_compile(self, subcmd, opts, udl_path):
        """${cmd_name}: compile a .udl file into a .lexres file
        
        ${cmd_usage}
        ${cmd_option_list}
        Note: This is a replacement for the deprecated `luddite compile'. In
        a subsequent release this will get the name `luddite compile'.
        """
        return commands.compile(
            udl_path, output_dir=opts.output_dir,
            include_path=opts.include_dirs, log=log)

    @cmdln.option("--ext",
                  help="specify a default file extension for this language")
    @cmdln.option("-g", "--guid", 
                  help="specify an XPCOM component GUID to use, or a path "
                       "to GUIDs text file")
    @cmdln.option("-G", dest="new_guid", action="store_true",
                  help="create a new XPCOM component GUID for this build")
    @cmdln.option("--skel", action="store_true",
                  help="also build skeleton Language Service and template files")
    @cmdln.option("--add-missing", action="store_true",
                  help="only add in missing files for skeleton")
    @cmdln.option("-f", "--force", action="store_true",
                  help="allow build outputs to overwrite existing files")
    @cmdln.option("-c", "--creator", action="store",
                  help="creator of this extension, used for creating install.rdf if it's missing")
    @cmdln.option("-V", "--version", action="store",
                  help="the extension version, used for creating install.rdf if it's missing")
    @cmdln.alias("compile")
    def do_deprecated_compile(self, subcmd, opts, udl_path):
        """${cmd_name}: compile a .udl file into lang resources
        
        Note: This has been deprecated in favour of `luddite just_compile'
        and the more generic functionality of the 'koext' tool.
        
        ${cmd_usage}
        ${cmd_option_list}
        If you specify '--skel' to build a skeleton Language Service
        then you must also specify one of the -G or -g|--guid options.
        The Language Service is a Python file that controls language
        support in Komodo. It requires a unique GUID (for the XPCOM
        component's class id).

        If you are just building the skeleton language service for every
        build (you can get away with this for minimal language support)
        the using a GUIDs text file to ensure the same GUID is used for
        your component from build to build is recommended. This file
        must be of the form (one entry per line):
            <lang> <guid>
        """
        log.warn("the 'skel' generation facilities of 'luddite compile' "
                 "have been deprecated in favour of (a) the simpler "
                 "'luddite just_compile' and (b) the more generic support "
                 "of the 'koext' tool")
        guid = guid_from_lang = None
        if not opts.skel:
            if opts.add_missing:
                raise Luddite("cannot specify --add-missing without --skel")
        elif opts.new_guid and opts.guid:
            raise LudditeError("cannot specify both -G and -g|--guid "
                               "options at the same time")
        elif opts.new_guid:
            guid = None
        elif opts.guid:
            if guid_pat.match(opts.guid):
                guid = norm_guid(opts.guid)
            else:
                if not exists(opts.guid):
                    raise LudditeError("`%s' is not a GUID and does not "
                                       "exist" % opts.guid)
                guid_from_lang = {} #dict((lang, g) for lang, g in)
                for line in file(opts.guid):
                    if line.startswith("#"): continue
                    if not line.strip(): continue
                    lang, g = line.strip().split(None, 1)
                    guid_from_lang[lang] = norm_guid(g)
        else:
            raise LudditeError("must specify one of -G or -g|--guid")
        if opts.force and opts.add_missing:
            raise LudditeError("cannot specify both -f|--force and "
                               "--add-missing options at the same time")
        return commands.deprecated_compile(
            udl_path, skel=opts.skel, guid=guid, 
            guid_from_lang=guid_from_lang, ext=opts.ext,
            version=opts.version, creator=opts.creator,
            force=opts.force, add_missing=opts.add_missing, log=log)

    def _do_parse(self, subcmd, opts, *udl_paths):
        """${cmd_name}: parse the given .udl file (for debugging)
        
        ${cmd_usage}
        ${cmd_option_list}
        """
        for udl_path in udl_paths:
            tree = commands.parse(udl_path, log=log)
            pprint(tree)

    def do_lex(self, subcmd, opts, lang, path):
        """${cmd_name}: lex the given file (for debugging)

        ${cmd_usage}
        ${cmd_option_list}
        Lex the given path with the UDL-based lexer for the given language,
        printing a summary to stdout. This is for debugging a .udl file
        during development.
        """
        from ludditelib.debug import lex
        content = open(path, 'r').read()
        lex(content, lang)

    @cmdln.option("-o", "--output",
                  help="path to which to write HTML output (instead of "
                       "PATH.html, use '-' for stdout)")
    @cmdln.option("-b", "--browse", action="store_true",
                  help="open output file in browser")
    def do_lexhtml(self, subcmd, opts, lang, path):
        """${cmd_name}: lex the given file to styled HTML (for debugging)

        ${cmd_usage}
        ${cmd_option_list}
        """
        from ludditelib.debug import lex_to_html
        content = open(path, 'r').read()
        html = lex_to_html(content, lang)

        if opts.output == '-':
            output_path = None
            output_file = sys.stdout
        else:
            if opts.output:
                output_path = opts.output
            else:
                output_path = path+".html"
            if exists(output_path):
                os.remove(output_path)
            output_file = open(output_path, 'w')
        if output_file:
            output_file.write(html)
        if output_path:
            output_file.close()

        if opts.browse:
            if not output_path:
                raise LudditeError("cannot open in browser if stdout used "
                                   "for output")
            import webbrowser
            url = _url_from_local_path(output_path)
            webbrowser.open_new(url)            



#---- internal support stuff

# Recipe: pretty_logging (0.1) in C:\trentm\tm\recipes\cookbook
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
    infoFmt = "%(name)s: %(message)s"
    fmtr = _PerLevelFormatter(fmt=defaultFmt,
                              fmtFromLevel={logging.INFO: infoFmt})
    hdlr.setFormatter(fmtr)
    logging.root.addHandler(hdlr)
    log.setLevel(logging.INFO)
    #log.setLevel(logging.DEBUG)


def _url_from_local_path(local_path):
    # HACKy: This isn't super-robust.
    from os.path import abspath, normpath
    url = normpath(abspath(local_path))
    if sys.platform == "win32":
        url = "file:///" + url.replace('\\', '/')
    else:
        url = "file://" + url
    return url



#---- mainline

if __name__ == "__main__":
    _setup_logging() # defined in recipe:pretty_logging
    try:
        shell = Shell()
        retval = shell.main(sys.argv)
    except KeyboardInterrupt:
        sys.exit(1)
    except:
        exc_info = sys.exc_info()
        if hasattr(exc_info[0], "__name__"):
            log.error("%s: %s", exc_info[0].__name__, exc_info[1])
        else:  # string exception
            log.error(exc_info[0])
        if log.isEnabledFor(logging.DEBUG):
            import traceback
            print
            traceback.print_exception(*exc_info)
        sys.exit(1)
    else:
        sys.exit(retval)


