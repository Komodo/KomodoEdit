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

"""Basic luddite commands."""

import os
from os.path import basename, dirname, join, exists, abspath, splitext
import logging
import string
import re

from ludditelib import parser, gen, constants
from ludditelib.common import LudditeError, guid_pat, norm_guid, \
                              generate_guid
import chromereg # see __init__.py for finding where that is

_log = logging.getLogger("luddite.commands")


def compile(udl_path, output_dir=None, include_path=None, log=None):
    """Compile the given .udl file to a Komodo lexer resource.
    
    If not given, the output dir will be the same as the input .udl file.
    The output filename is "${safe_lang}.lexres", where "safe_lang" is a
    slightly massaged version of the language name defined in the .udl
    file with the "language" UDL statement.
    
    "include_path" is a list of directories from which support .udl files
    can be included (by default the current dir, the dir of the input .udl
    file is alway part of the include path).
    """
    log = log or _log
    if output_dir is None:
        output_dir = dirname(udl_path) or os.curdir

    # Clean up after PLY. It leaves some turds that can break subsequent
    # parsing if the parser source is changed.
    turds = ["parser.out", "parsetab.py", "parsetab.pyc"]
    for turd in turds:
        if exists(turd):
            log.debug("remove `%s'", turd)
            os.remove(turd)

    # Parse and load the UDL definition.
    log.debug("parse `%s'", udl_path)
    parse_tree = parse(udl_path, include_path=include_path)
    if parse_tree is None:
        raise LudditeError("parse failed");
    mainObj = gen.MainObj()
    analyzer = gen.Analyzer(mainObj)
    analyzer.processTree(parse_tree)
    mainObj.calcUniqueStates()

    #XXX Grr. Crappy error handling again. This should be changed to
    #    raise a LudditeError if the semanticCheck fails then just call:
    #       analyzer.semanticCheck()
    if analyzer.semanticCheck() is None:
        return 1

    # Make sure don't trounce files before generating outputs and setup
    # output dir.
    lang_name = mainObj.languageName
    safe_lang_name = mainObj.safeLangName
    lexres_path = join(output_dir, safe_lang_name+".lexres")
    log.info("compile `%s' to `%s'", udl_path, lexres_path)
    if exists(lexres_path):
        log.debug("rm `%s'", lexres_path)
        os.remove(lexres_path)

    # Generate all outputs.
    if not exists(dirname(lexres_path)):
        os.makedirs(dirname(lexres_path))
    log.debug("create `%s'", lexres_path)
    mainObj.dumpAsTable(constants.vals, lexres_path)



def deprecated_compile(udl_path, skel=False, guid=None, guid_from_lang=None,
                       ext=None, force=False, add_missing=False, log=None,
                       version=None, creator=None, ext_id=None,
                       description=None):
    """Compile the given .udl file to Komodo language resources.
    
    DEPRECATED: The 'skel' generation in luddite has been deprecated in
    favour of the more generic support of the 'koext' tool.
    
    One of "guid" or "guid_from_lang" can be given to specify the XPCOM
    language service GUID. If neither is given then a new one will be
    generated.
    """
    # Dev Notes:
    # - Compiling builds into build/$languange/... and creates:
    #       ${language}.lexres                  lexer resource
    # - If skel is True then also build skeletons for:
    #       ko${language}_UDL_Language.py       language component
    #       ${language}.${ext}                  empty Komodo template
    # - Add support for other options that Eric had in the preceding
    #   luddite.py?
    log = log or _log
    log.debug("compile('%s', ...)", udl_path)

    # Clean up after PLY. It leaves some turds that can break subsequent
    # parsing if the parser source is changed.
    turds = ["parser.out", "parsetab.py", "parsetab.pyc"]
    for turd in turds:
        if exists(turd):
            log.debug("remove `%s'", turd)
            os.remove(turd)

    # Parse and load the UDL definition.
    parse_tree = parse(udl_path)
    if parse_tree is None:
        raise LudditeError("parse failed");
    mainObj = gen.MainObj()
    analyzer = gen.Analyzer(mainObj)
    analyzer.processTree(parse_tree)
    mainObj.calcUniqueStates()

    #XXX Grr. Crappy error handling again. This should be changed to
    #    raise a LudditeError if the semanticCheck fails then just call:
    #       analyzer.semanticCheck()
    if analyzer.semanticCheck() is None:
        return 1

    def raise_force_error(path):
        raise LudditeError("`%s' already exists: use "
                           "-f|--force option to allow it to be "
                           "overwritten" % path)

    # Make sure don't trounce files before generating outputs and setup
    # output dir.
    lang_name = mainObj.languageName
    safe_lang_name = mainObj.safeLangName
    build_dir = _get_build_dir(safe_lang_name)
    if not exists(build_dir):
        log.debug("mkdir `%s'", build_dir)
        os.makedirs(build_dir)

    # Generate all outputs.
    lexres_path = join(build_dir, "lexers", safe_lang_name+".lexres")
    lexres_exists = exists(lexres_path)
    if lexres_exists and not force:
        if not add_missing:
            raise_force_error(lexres_path)
    else:
        if lexres_exists:
            log.debug("rm `%s'", lexres_path)
            os.remove(lexres_path)
        elif not exists(dirname(lexres_path)):
            os.makedirs(dirname(lexres_path))
        log.info("create lexres `%s'", lexres_path)
        mainObj.dumpAsTable(constants.vals, lexres_path)

    if skel:
        lang_service_path \
            = join(build_dir, "components", "ko%s_UDL_Language.py" % safe_lang_name)
        lang_service_exists = exists(lang_service_path)
        if lang_service_exists and not force:
            if not add_missing:
                raise_force_error(lang_service_path)
        else:
            if lang_service_exists:
                log.debug("rm `%s'", lang_service_path)
                os.remove(lang_service_path)
            elif not exists(dirname(lang_service_path)):
                os.makedirs(dirname(lang_service_path))
            log.info("create lang service `%s'", lang_service_path)
            if guid is not None:
                assert guid_pat.match(guid)
                guid = norm_guid(guid)
            elif guid_from_lang:
                try:
                    guid = guid_from_lang[mainObj.languageName]
                except KeyError:
                    if not add_missing:
                        raise LudditeError("could not find `%s' in GUIDs text file"
                                           % mainObj.languageName)
            else:
                log.warn("generating new GUID for `%s' language service: it is "
                         "recommended that you use the -g|--guid option to ensure "
                         "a constant GUID from build to build",
                         mainObj.languageName)
                guid = generate_guid()
            if guid is not None:
                mainObj.dumpLanguageService(lang_service_path, guid, ext=ext,
                                            add_missing=add_missing)

        if not ext:
            log.warn("no file extension was given: no skeleton "
                     "Komodo templates will be created")
        else:
            template_paths = [
                join(build_dir, "templates", "All Languages",
                     safe_lang_name+ext),
                join(build_dir, "templates", "Common", safe_lang_name+ext),
            ]
            for template_path in template_paths:
                template_exists = exists(template_path)
                if template_exists and not force:
                    if not add_missing:
                        raise_force_error(template_path)
                else:
                    if template_exists:
                        log.debug("rm `%s'", template_path)
                        os.remove(template_path)
                    elif not exists(dirname(template_path)):
                        os.makedirs(dirname(template_path))
                    log.info("create template `%s'", template_path)
                    mainObj.generateKomodoTemplateFile(template_path)

    # Create the extension's install.rdf if necessary.
    install_rdf_path = join(build_dir, "install.rdf")
    if not exists(install_rdf_path):
        name = lang_name + " Language"
        codename = _codename_from_name(name)
        if ext_id is None:
            ext_id = "%s@ActiveState.com" % codename
        if version is None:
            version = "1.0.0"
            log.warn("defaulting 'version' to '%s' (use version option)",
                     version)
        #else:
        #    XXX validate version
        if description is None:
            description = "%s language support for Komodo (UDL-based)" % lang_name
        if creator is None:
            creator = "Anonymous Coward"
            log.warn("defaulting 'creator' to '%s' (use creator option)", creator)
    
        install_rdf_in = join(dirname(constants.__file__), "install.rdf.in")
        log.debug("reading 'install.rdf' template from '%s'", install_rdf_in)
        install_rdf_template = string.Template(open(install_rdf_in, 'r').read())
        install_rdf = install_rdf_template.substitute(
            id=ext_id, name=name, codename=codename, version=version,
            description=description, creator=creator)
        log.info("create `%s'", install_rdf_path)
        fout = open(install_rdf_path, 'w')
        fout.write(install_rdf)
        fout.close()

    # Clean up after PLY. It leaves some turds that can break subsequent
    # parsing if the parser source is changed.
    for turd in turds:
        if exists(turd):
            log.debug("remove `%s'", turd)
            os.remove(turd)


def parse(udl_path, include_path=None, log=None):
    """Parse the given .udl file.
    
    PLY (i.e. yacc.py and lex.py) are messy. They leave 'parser.out' and
    'parsetab.py' turds in the current directory. Attempting to hack around
    this by cd'ing into the build dir to run. However this breaks the parse
    for a reason I don't understand. It would be good to fix that at some
    point.
    
    Notes on the above analysis: The 'parser.out' debug file can be
    suppressed with `yaccdebug = 0` in yacc.py. The 'parsetab.py' file
    is generated by yacc.py::lr_write_tables() and can be suppressed
    with the `yacc(..., write_tables=0)` argument. TODO: Try this and
    see if can remove the above-mentioned hacking around.
    """
    log = log or _log
    log.debug("parse('%s')", udl_path)
    parse_tree = parser.parse_udl_path(udl_path, include_path=include_path)

    # Ick. This modules uses a global for an error count.
    if parser.num_errs:
        raise LudditeError("could not parse '%s': %d error(s)"
                           % (udl_path, parser.num_errs))
    return parse_tree
    


#---- internal support

def _get_build_dir(lang):
    return join("build", lang)

def _codename_from_name(name):
    """Transform a Komodo extension name to a "code" name, i.e. one that is
    safe for use in a filename and an extension id.
    """
    return re.sub(r'\W', '_', name.lower())


# Recipe: run (0.5.3) in C:\trentm\tm\recipes\cookbook
_RUN_DEFAULT_LOGSTREAM = ("RUN", "DEFAULT", "LOGSTREAM")
def __run_log(logstream, msg, *args, **kwargs):
    if not logstream:
        pass
    elif logstream is _RUN_DEFAULT_LOGSTREAM:
        try:
            log
        except NameError:
            pass
        else:
            if hasattr(log, "debug"):
                log.debug(msg, *args, **kwargs)
    else:
        logstream(msg, *args, **kwargs)

def _run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    retval = os.system(cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmd, status))

def _run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command in the given working directory.

        "cmd" is the command to run
        "cwd" is the directory in which the commmand is run.
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    old_dir = os.getcwd()
    try:
        os.chdir(cwd)
        __run_log(logstream, "running '%s' in '%s'", cmd, cwd)
        _run(cmd, logstream=None)
    finally:
        os.chdir(old_dir)
