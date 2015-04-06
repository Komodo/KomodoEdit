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

"""Tools for building Komodo extensions.

Typical usage is for a Komodo extension source dir to put the Komodo SDK
bin dir on ones path and call the "koext" tool for building an extension.
"koext" is a light wrapper around this lib.

Provided that the source dir has an appropriate "install.rdf" (the main
file for describing a Komodo extension), then "build_ext" will do the rest.
The "Komodo Extension" project template provides boilerplate for this.

A Komodo extension source dir looks like this:

    install.rdf         # main extension meta-data file
                        #   (all other pieces are optional)

    # Chrome
    chrome.manifest     # necessary if have any XUL "content", "skin"
                        #   or "locale"
    content/            # XUL overlays, dialogs and JavaScript
    skin/               # CSS
    locale/             # localized chrome files (typically DTDs)

    # Other extension hooks
    components/         # XPCOM components
    platform/           # Platform specific XPCOM components and libraries.
    templates/          # Komodo "New File" templates
    project-templates/  # Komodo "New Project" templates
    lexers/             # UDL-based ".lexres" files for custom language
                        #   syntax coloring. These are built with the
                        #   "luddite" tool. Typically source ".udl" files
                        #   are placed in a "udl" dir.
    xmlcatalogs/        # XML catalog defining namespace to schema mapping
      catalog.xml       #   for XML autocomplete, and the schemas
      ...               #   themselves (DTDs, XML Schemas, Relax NG)
    apicatalogs/        # API Catalog ".cix" files for custom autocomplete
                        #   and calltips.
    pylib/              # This dir will be added to Komodo's runtime sys.path.
                        #   As well, "codeintel_LANG.py" files here define
                        #   codeintel language support.

A Mozilla extension source dir can also contain these:

    defaults/          # Default JavaScript preferences files.
    plugins/           # Plugin files.
    searchplugins/     # Specific search plugins.
    dictionaries/      # Dictionary files used by the spellchecker.


TODO: create_ext_chrome_skel
TODO: create_ext_component_skel
"""

import os
from os.path import exists, join, dirname, isdir, basename, splitext, \
                    normpath, abspath, isfile
import sys
import re
import uuid
import shutil
import distutils.dir_util
import logging
import tempfile
from glob import glob
from pprint import pprint

import chromereg

class KoExtError(Exception):
    pass



#---- globals

_log = logging.getLogger("koextlib")
_log.setLevel(logging.INFO)

_install_rdf_template = """<?xml version="1.0"?>
<RDF xmlns="http://www.w3.org/1999/02/22-rdf-syntax-ns#" 
     xmlns:em="http://www.mozilla.org/2004/em-rdf#">
  <Description about="urn:mozilla:install-manifest">
    <em:id>%(id)s</em:id>
    <em:name>%(name)s</em:name>
    <em:version>%(version)s</em:version>
    <em:description>%(desc)s</em:description>
    <em:creator>%(creator)s</em:creator>
    <em:homepageURL>%(homepage)s</em:homepageURL>
    <em:type>2</em:type> <!-- type=extension --> 
    <em:unpack>%(unpack)s</em:unpack>

    <em:targetApplication> <!-- Komodo IDE -->
      <Description>
        <em:id>{36E66FA0-F259-11D9-850E-000D935D3368}</em:id>
        <em:minVersion>7.0</em:minVersion>
        <em:maxVersion>8.*</em:maxVersion>
      </Description>
    </em:targetApplication>
    <em:targetApplication> <!-- Komodo Edit -->
      <Description>
        <em:id>{b1042fb5-9e9c-11db-b107-000d935d3368}</em:id>
        <em:minVersion>7.0</em:minVersion>
        <em:maxVersion>8.*</em:maxVersion>
      </Description>
    </em:targetApplication>
  </Description>
</RDF>
"""



#---- module api

def is_ext_dir(dir=os.curdir):
    import operator
    return operator.truth(glob(join(dir, "install.*rdf*")))

# Validation.
def validate_ext_name(name):
    if not name.strip():
        return "The name must not be empty."

def validate_ext_id(id):
    if not id.strip():
        return "You must specify an ID."
    id_pat = re.compile("(.*?)@(.*?)")
    if not id_pat.match(id):
        return "The ID does not match to '%s' pattern." % id_pat
    if ' ' in id:
        return "The ID should not contain spaces."

def validate_ext_version(version):
    if not version.strip():
        return "You must specify a version."
    if not re.match("^\d+\.\d+(\.\d+([a-z]\d*)?)?$", version):
        return "The version must be of the form X.Y.Z or X.Y where"

def validate_ext_creator(creator):
    if not creator.strip():
        return "You must specify a creator."


def create_ext_skel(base_dir, name=None, id=None, version=None, desc="",
                    creator=None, homepage="", dry_run=False, log=None):
    """Creates an empty starter Komodo extension skeleton in the given
    base directory.
    
    If not specified, this will query for all the meta-data on stdin/stdout.
    """
    if log is None: log = _log
    if exists(base_dir):
        raise KoExtError("`%s' exists (aborting creation of skeleton)"
                         % base_dir)

    # Gather info for install.rdf.
    need_to_query = (id is None or name is None or version is None
                     or creator is None)
    curr_dir = os.getcwd()
    dirs = set([d for d in os.listdir(curr_dir) if isdir(d)]).\
        difference(set(["content", "prefs", "skin", "locale"]))
    unpack = dirs and "true" or "false"
    while need_to_query:
        print _banner("Gathering extension information")
        
        if name is None:
            name = ' '.join(s.capitalize()
                            for s in basename(base_dir).split('\t _'))
        name = _query(
            "Name of your extension, for example 'Fuzzy Wuzzy'.",
            default=name, validate=validate_ext_name,
            prompt="      name: ")
        id = _query(
            "\nString ID for this extension. This shouldn't have spaces\n"
                "and must be of the form 'PROJECTNAME@DOMAIN', for\n"
                "example '%s@mydomain.com'." % name.lower().replace(' ', '_'),
            default=id, validate=validate_ext_id,
            prompt="        id: ")
        version = _query(
            "\nVersion for this extension. Examples: 1.0, 2.1.2, 0.9.0b2.",
            default=version, validate=validate_ext_version,
            prompt="   version: ")
        desc = _query(
            "\nA brief description of this extension, for example: 'Fuzzy\n"
                "Wuzzy tools for Komodo'.",
            default=desc or "",
            prompt="      desc: ")
        creator = _query(
            "\nThe creator/author of this extension, typically your name.",
            default=creator, validate=validate_ext_creator,
            prompt="   creator: ")
        homepage = _query(
            "\nThe main URL at which to get information on this extension.",
            default=homepage or "",
            prompt="  homepage: ")

        print
        print _banner(None, '-')
        sys.stdout.write(_dedent("""
            Extension information:
                  name: %(name)s
                    id: %(id)s
               version: %(version)s
                  desc: %(desc)s
               creator: %(creator)s
              homepage: %(homepage)s
            """ % locals()).lstrip())
        answer = _query_yes_no_quit("Are these details correct?")
        if answer == "yes":
            print _banner(None)
            break
        elif answer == "no":
            print _banner(None, '-')
            continue
        elif answer == "quit":
            raise SystemExit("aborting")

    # Validate ext data.
    errors = [s for s in [validate_ext_name(name),
                          validate_ext_id(id),
                          validate_ext_version(version)] if s]
    if errors:
        raise KoExtError("invalid extension information: %s"
                         % ' '.join(errors))

    # Create install.rdf.
    if not dry_run:
        _mkdir(base_dir, log.info)
    install_rdf_path = join(base_dir, "install.rdf")
    log.info(_dedent("""
        create `%(install_rdf_path)s':
              name: %(name)s
                id: %(id)s
           version: %(version)s
              desc: %(desc)s
           creator: %(creator)s
          homepage: %(homepage)s
        """ % locals()).strip())
    if not dry_run:
        open(install_rdf_path, 'w').write(
            _install_rdf_template % locals())


def create_udl_lang_skel(base_dir, lang, ext=None, is_html_based=False,
                         is_xml_based=False, dry_run=False, log=None):
    """Create the skeleton files for a new UDL-based Komodo language."""
    if log is None: log = _log
    if not is_ext_dir(base_dir):
        raise KoExtError("`%s' isn't an extension source dir: there is no "
                         "'install.rdf' file (run `koext startext' first)"
                         % base_dir)

    if is_html_based and is_xml_based:
        raise KoExtError("a language cannot be both HTML- and XML-based: "
                         "lang=%r, is_html_based=%r, is_xml_based=%r"
                         % (lang, is_html_based, is_xml_based))
    safe_lang = _code_safe_lang_from_lang(lang)
    ko_info = KomodoInfo()

    # Create udl/${lang}-mainlex.udl
    mainlex_path = normpath(join(base_dir, "udl",
                                 safe_lang.lower()+"-mainlex.udl"))
    if exists(mainlex_path):
        log.warn("`%s' exists (skipping)", mainlex_path)
    else:
        if not dry_run and not exists(dirname(mainlex_path)):
            _mkdir(dirname(mainlex_path), log.debug)
        log.info("create %s (lexer definition)", mainlex_path)
        if not dry_run:
            if is_html_based:
                template = file(join(ko_info.sdk_dir, "share", "html_template.udl")).read()
            elif is_xml_based:
                template = file(join(ko_info.sdk_dir, "share", "xml_template.udl")).read()
            else:
                template = file(join(ko_info.sdk_dir, "share", "ssl_template.udl")).read()
            open(mainlex_path, 'w').write(template % locals())

    # Create components/ko${lang}_UDL_Language.py
    lang_svc_path = normpath(join(base_dir, "components",
                                  "ko%s_UDL_Language.py" % safe_lang))
    if exists(lang_svc_path):
        log.warn("`%s' exists (skipping)", lang_svc_path)
    else:
        guid = uuid.uuid4()
        if ext is None:
            default_ext_assign = ""
        else:
            if not ext.startswith('.'):
                log.warn("extension for %s, %r, does not being with a '.': "
                         "that might cause problems" % (lang, ext))
            default_ext_assign = "defaultExtension = %r" % ext
        if is_xml_based:
            base_module = "koXMLLanguageBase"
            base_class = "koXMLLanguageBase"
            lang_from_udl_family = {'M': 'XML'}
        elif is_html_based:
            base_module = "koXMLLanguageBase"
            base_class = "koHTMLLanguageBase"
            lang_from_udl_family = {'M': 'HTML',
                                    'SSL': lang}
        else:
            base_module = "koUDLLanguageBase"
            base_class = "KoUDLLanguage"
            lang_from_udl_family = {'SSL': lang}

        if not dry_run and not exists(dirname(lang_svc_path)):
            _mkdir(dirname(lang_svc_path), log.debug)
        log.info("create %s (language service)", lang_svc_path)
        if not dry_run:
            template_path = join(ko_info.sdk_dir, "share", "koLANG_UDL_Language.py")
            lang_svc_template = file(template_path).read() % locals()
            open(lang_svc_path, 'w').write(lang_svc_template)

    # Create templates.
    if not ext:
        log.warn("no file extension given for %s: skipping generation "
                 "of 'New File' templates" % lang)
    else:
        tpl_paths = [
            normpath(join(base_dir, "templates", "All Languages", safe_lang+ext)),
            normpath(join(base_dir, "templates", "Common", safe_lang+ext)),
        ]
        for tpl_path in tpl_paths:
            if exists(tpl_path):
                log.warn("`%s' exists (skipping)", tpl_path)
                continue
            if not dry_run and not exists(dirname(tpl_path)):
                _mkdir(dirname(tpl_path), log.debug)
            log.info("create %s ('New File' template)", tpl_path)
            if not dry_run:
                open(tpl_path, 'w').write('')


def create_codeintel_lang_skel(base_dir, lang, dry_run=False, force=False,
                               log=None):
    """Create the skeleton files for Code Intelligence support for a
    new language.
    
    "New" here means a language for which Komodo has no current Code
    Intelligence support.
    """
    if log is None: log = _log
    if not is_ext_dir(base_dir):
        raise KoExtError("`%s' isn't an extension source dir: there is no "
                         "'install.rdf' file (run `koext startext' first)"
                         % base_dir)

    ko_info = KomodoInfo()
    safe_lang = _code_safe_lang_from_lang(lang)
    log.debug("safe lang: %r", safe_lang)

    # Create pylib/codeintel_${lang}.py
    lang_path = normpath(join(base_dir, "pylib",
                              "codeintel_%s.py" % safe_lang.lower()))
    if exists(lang_path) and not force:
        log.warn("`%s' exists (skipping, use --force to override)",
                 lang_path)
    else:
        if not dry_run and not exists(dirname(lang_path)):
            _mkdir(dirname(lang_path), log.debug)
        log.info("create %s (codeintel language master)", lang_path)
        if not dry_run:
            template_path = join(ko_info.sdk_dir, "share",
                                 "codeintel_LANG.py")
            file_contents = open(template_path).read()
            buffer_subclass = "CitadelBuffer"
            cile_subclass = "CileDriver"
            if exists(join(base_dir, "udl")):
                buffer_subclass = "UDLBuffer"
                cile_subclass = "UDLCILEDriver"
                # We know it's udl, so update the lexer class now.
                file_contents = file_contents.replace("# LexerClass",
                                                      """
from codeintel2.udl import UDLLexer
class ${safe_lang}Lexer(UDLLexer):
        lang = lang
""")
            import string
            template = string.Template(file_contents)
            content = template.safe_substitute(
                {"lang": lang,
                 "safe_lang": safe_lang,
                 "safe_lang_lower": safe_lang.lower(),
                 "safe_lang_upper": safe_lang.upper(),
                 "buffer_subclass": buffer_subclass,
                 "cile_subclass": cile_subclass,
                })

            open(lang_path, 'w').write(content)

    # Create codeintel/cile_${lang}.py
    cile_path = normpath(join(base_dir, "pylib",
                              "cile_%s.py" % safe_lang.lower()))
    if exists(cile_path) and not force:
        log.warn("`%s' exists (skipping, use --force to override)",
                 cile_path)
    else:
        if not dry_run and not exists(dirname(cile_path)):
            _mkdir(dirname(cile_path), log.debug)
        log.info("create %s (codeintel language scanner)", cile_path)
        if not dry_run:
            template_path = join(ko_info.sdk_dir, "share",
                                 "cile_LANG.py")
            import string
            template = string.Template(open(template_path).read())
            content = template.safe_substitute(
                {"lang": lang,
                 "safe_lang": safe_lang,
                 "safe_lang_lower": safe_lang.lower(),
                 "safe_lang_upper": safe_lang.upper()})
            open(cile_path, 'w').write(content)



def build_ext(base_dir, support_devinstall=True, unjarred=False,
              ppdefines=None, additional_includes=None, log=None,
              xpi_path=None):
    """Build a Komodo extension from the sources in the given dir.
    
    This reads the "install.rdf" in this directory and the appropriate
    source files to create a Komodo .xpi extension.
    
    - Files in "chrome/..." are put into a jar file.
    - IDL and PyXPCOM components in "components/..." are handled
      appropriately.
    - etc. (see `koext help hooks' for more details)
    
    @param base_dir {str} The source directory path of the extension.
    @param support_devinstall {bool} Whether to copy built bits to the source
        directory to support use with a 'devinstall'. Default is True.
    @param unjarred {bool} Whether to leave the chrome directory unjarred.
        Default is False, meaning all chrome files (skin, content, locale)
        are zipped up into a '$ext-name.jar' file.
    @param ppdefines {dict} Is an optional dictionary of preprocessor defines
        used for preprocessing "*.p.*" files in the source tree.
        See <http://code.google.com/p/preprocess/> for info.
        If this is None (the default), then preprocessing is not done. When
        preprocessing, *all* of the source tree except "build" and "tmp" subdirs
        are traversed.
    @param additional_includes {list} Optional - a list of paths to include in
        final xpi.
    @param log {logging.Logger} Optional.
    @param xpi_path {str} Optional. File path for the resulting .xpi file.
    @returns {str} The path to the created .xpi file.
    """
    if log is None: log = _log
    if not is_ext_dir(base_dir):
        raise KoExtError("`%s' isn't an extension source dir: there is no "
                         "'install.rdf' file (run `koext startext' first)"
                         % base_dir)

    zip_exe = _get_zip_exe()
    exclude_pats = [".svn", "CVS", ".hg", ".bzr", ".git",
        ".DS_Store", "*~", "*.pyo", "*.pyc", "__pycache__"]

    # files that do not need to cause <em:unpack>
    unpack_excludes = ["install.rdf", "chrome.manifest", "bootstrap.js",
                       "chrome", "content", "skin", "locale"]

    # Dev Note: Parts of the following don't work unless the source
    # dir is the current one. The easiest solution for now is to just
    # chdir there.
    orig_dir = None
    if base_dir != os.curdir:
        orig_base_dir = base_dir
        orig_dir = os.getcwd()
        log.info("cd %s", base_dir)
        os.chdir(base_dir)
        base_dir = os.curdir
    try:
        build_dir = normpath(join(base_dir, "build"))
        if exists(build_dir):
            _rm(build_dir, log.info)
        
        # Preprocessing.
        if ppdefines is not None:
            for path in _paths_from_path_patterns([base_dir],
                    includes=["*.p.*"],
                    excludes=["build", "tmp"] + exclude_pats,
                    skip_dupe_dirs=True):
                _preprocess(path, ppdefines, log.info)

        ext_info = ExtensionInfo(base_dir)
        ko_info = KomodoInfo()
        xpi_manifest = ["install.rdf"]
        
        # Make the chrome jar.
        chrome_dirs = [d for d in ("chrome", "content", "skin", "locale") if isdir(d)]
        if chrome_dirs:
            assert exists("chrome.manifest"), \
                "you have chrome dirs ('%s') but no 'chrome.manifest' file" \
                % "', '".join(chrome_dirs)
            chrome_build_dir = join(build_dir, unjarred and "xpi" or "jar")
            _mkdir(chrome_build_dir, log.info)
            if unjarred:
                xpi_manifest += chrome_dirs
            else:
                for d in chrome_dirs:
                    _cp(d, join(chrome_build_dir, d), log.info)
                _trim_files_in_dir(chrome_build_dir, exclude_pats, log.info)
                # zip (jar) up the chrome
                _run_in_dir('"%s" -X -r %s.jar *' % (zip_exe, ext_info.codename),
                            chrome_build_dir, log.info)
                jar_name = join(chrome_build_dir, ext_info.codename+".jar")
                xpi_manifest += [jar_name, ]
                unpack_excludes += [jar_name, ]
            xpi_manifest.append("chrome.manifest")
   
        # Handle any PyXPCOM components and idl.
        if isdir("components"):
            components_build_dir = join(build_dir, "components")
            _mkdir(components_build_dir, log.info)
            for path in glob(join("components", "*")):
                _cp(path, components_build_dir, log.info)
            _trim_files_in_dir(components_build_dir, ["*.idl"] + exclude_pats,
                log.info)
            xpi_manifest.append(components_build_dir)
            if "chrome.manifest" not in xpi_manifest:
                xpi_manifest.append("chrome.manifest")

            component_manifest = join(components_build_dir, "component.manifest")
            for path in glob(join("components", "*.py")):
                chromereg.register_file(path, component_manifest)

            idl_build_dir = join(build_dir, "idl")
            idl_paths = glob(join("components", "*.idl"))
            if idl_paths:
                _mkdir(idl_build_dir, log.info)
                for idl_path in glob(join("components", "*.idl")):
                    _cp(idl_path, idl_build_dir, log.info)
                    xpt_path = join(components_build_dir,
                        splitext(basename(idl_path))[0] + ".xpt")
                    _xpidl(idl_path, xpt_path, ko_info, log.info)
                    chromereg.register_file(xpt_path, component_manifest)
                    if support_devinstall:
                        _cp(xpt_path, "components", log.info)
                        _cp(component_manifest, "components", log.info)
                xpi_manifest.append(idl_build_dir)
    
        # Handle any UDL lexer compilation.
        if exists("udl"):
            xpi_manifest.append("udl")
            lexers_build_dir = join(build_dir, "lexers")
            for mainlex_udl_path in glob(join("udl", "*-mainlex.udl")):
                if not exists(lexers_build_dir):
                    _mkdir(lexers_build_dir, log.info)
                _luddite_compile(mainlex_udl_path, lexers_build_dir, ko_info)
            if exists(lexers_build_dir):
                xpi_manifest.append(lexers_build_dir)
                if support_devinstall:
                    if not exists("lexers"):
                        _mkdir("lexers", log.info)
                    for lexres_path in glob(join(lexers_build_dir, "*.lexres")):
                        _cp(lexres_path, "lexers", log.info)
        elif exists("lexers"):
            # Pre-compiled UDL lexer files.
            xpi_manifest.append("lexers")

        # Remaining hook dirs that are just included verbatim in the XPI.
        for dname in ("templates", "apicatalogs", "xmlcatalogs", "pylib",
                      "project-templates", "platform", "defaults", "plugins",
                      "searchplugins", "dictionaries", "modules", "tools"):
            if isdir(dname):
                xpi_manifest.append(dname)
    
        if isfile("bootstrap.js"):
            xpi_manifest.append("bootstrap.js")

        # Include any paths specified on the command line.
        if additional_includes:
            for path in additional_includes:
                # Remove any trailing slashes, otherwise koext may include
                # everything underneath this directory using a relative path
                # from this directory point onwards.
                path = path.rstrip(os.sep)
                xpi_manifest.append(path)

        # Make the xpi.
        #pprint(xpi_manifest)
        xpi_build_dir = join(build_dir, "xpi")
        _mkdir(xpi_build_dir, log.info)
        for src in xpi_manifest:
            if isdir(src):
                _cp(src, join(xpi_build_dir, basename(src)), log.info)
            elif not exists(src) and src == "chrome.manifest":
                # When the chrome.manifest file doesn't exist yet, create an
                # empty one in the build directory.
                file(join(xpi_build_dir, "chrome.manifest"), "w")
            else:
                _cp(src, xpi_build_dir, log.info)

        # add em:unpack if necessary
        if not ext_info.unpack and set(xpi_manifest).difference(unpack_excludes):
            log.warn("setting <em:unpack> due to %r",
                     list(set(xpi_manifest).difference(unpack_excludes)))
            (in_file, out_file) = (None, None)
            try:
                in_file = open("install.rdf", "r")
                out_file = open(join(xpi_build_dir, "install.rdf"), "w")
                for line in in_file:
                    out_file.write(line)
                    if re.search("""about=['"]urn:mozilla:install-manifest['"]""", line):
                        # this is *probably* right; we might break things if
                        # the tag spans more than one line, but at least in that
                        # case things will fail to install and should be easier
                        # to spot, hopefully
                        out_file.write('<em:unpack>true</em:unpack>\n')
            finally:
                if (in_file): in_file.close()
                if (out_file): out_file.close()

        # insert reference to component manifest if required
        if isdir(join(xpi_build_dir, "components")):
            log.info("Ensuring component manifest is registered")
            chromereg.register_file(join(xpi_build_dir, "components", "component.manifest"),
                                    join(xpi_build_dir, "chrome.manifest"),
                                    "components")

        if isfile(join(xpi_build_dir, "xmlcatalogs", "catalog.xml")):
            chromereg.register_category(join(xpi_build_dir, "chrome.manifest"),
                                        # "1" is a dummy entry, to avoid warnings
                                        "xmlcatalogs %s 1" % (ext_info.id))

        if exists(join(xpi_build_dir, "apicatalogs")):
            chromereg.register_category(join(xpi_build_dir, "chrome.manifest"),
                                        # "1" is a dummy entry, to avoid warnings
                                        "apicatalogs %s 1" % (ext_info.id))

        if exists(join(xpi_build_dir, "lexers")):
            chromereg.register_category(join(xpi_build_dir, "chrome.manifest"),
                                        # "1" is a dummy entry, to avoid warnings
                                        "udl-lexers %s 1" % (ext_info.id))

        if exists(join(xpi_build_dir, "tools")):
            chromereg.register_category(join(xpi_build_dir, "chrome.manifest"),
                                        # "1" is a dummy entry, to avoid warnings
                                        "toolbox %s 1" % (ext_info.id))

        _trim_files_in_dir(xpi_build_dir, exclude_pats, log.info)
        _run_in_dir('"%s" -X -r %s *' % (zip_exe, ext_info.pkg_name),
                    xpi_build_dir, log.info)
        if not xpi_path:
            xpi_path = abspath(join(base_dir, ext_info.pkg_name))
        _cp(join(xpi_build_dir, ext_info.pkg_name), xpi_path, log.info)
    finally:
        if orig_dir:
            log.info("cd %s", orig_dir)
            os.chdir(orig_dir)
            base_dir = orig_base_dir

    print "'%s' created." % xpi_path
    return xpi_path


def dev_install(base_dir, force=False, dry_run=False, log=None):
    """Setup a link for development of the extension (in `base_dir`) with
    the current Komodo.
    """
    if log is None: log = _log
    if not is_ext_dir(base_dir):
        raise KoExtError("`%s' isn't an extension source dir: there is no "
                         "'install.rdf' file (run `koext startext' first)"
                         % base_dir)

    ext_info = ExtensionInfo(base_dir)
    ko_info = KomodoInfo()
            
    dev_dir = abspath(base_dir)
    """
    Seems that pointer files, on Windows at least, need to have
    a trailing slash at the end of the path when moving from
    a true extension directory to a pointer file.

    The samples at http://blog.mozilla.com/addons/2009/01/28/how-to-develop-a-firefox-extension/
    use a trailing slash, but there's no text stating that it's required.
    """
    if not dev_dir.endswith(os.sep) and sys.platform == "win32":
        dev_dir += os.sep
    ext_file = join(ko_info.ext_base_dir, ext_info.id)
    if isfile(ext_file):
        contents = open(ext_file, 'r').read().strip()
        if contents == dev_dir:
            log.debug("`%s' already points to `%s'", ext_file, dev_dir)
            return
        elif not force:
            raise KoExtError("`%s' link file exists: use force option "
                "to overwrite" % ext_file)
        else:
            if not dry_run:
                os.remove(ext_file)
    elif isdir(ext_file):
        if not force:
            raise KoExtError("`%s' *directory* exists: use force option "
                "to overwrite" % ext_file)
        else:
            if not dry_run:
                _rmtree(ext_file)
    elif exists(ext_file):
        raise KoExtError("`%s' exists but isn't a regular file or "
            "directory (aborting)" % ext_file)
    log.info("create `%s' link", ext_file)
    if not dry_run:
        open(ext_file, 'w').write(dev_dir)

def komodo_build_install(base_dir, ppdefines=None, dry_run=False, log=None,
                         unjarred=False, xpi_path=None, distinstall=False,
                         additional_includes=None, packed=False):
    """Install the extension in `base_dir` into a Komodo build.
        
    This command is for building *core* Komodo extensions into a Komodo
    build. This is *not* a command for installing an extension into a
    Komodo installation (either install the .xpi for use `koext devinstall`
    for that).
    
    @param base_dir {str}
    @param ppdefines {dict} Is an optional dictionary of preprocessor defines
        used for preprocessing "*.p.*" files in the source tree.
        See <http://code.google.com/p/preprocess/> for info.
        If this is None (the default), then preprocessing is not done. When
        preprocessing, *all* of the source tree except "build" and "tmp" subdirs
        are traversed.
    @param log {logging.Logger} Optional.
    @param unjarred {bool} Whether to leave the chrome directory unjarred.
        Default is False, meaning all chrome files (skin, content, locale)
        are zipped up into a '$ext-name.jar' file.
    @param xpi_path {str} Optional. File path for the built .xpi file.
    @param distinstall {bool} Optional. Install into the "distributions" dir.
    @param additional_includes {list} Optional - a list of paths to include in
        final xpi.
    """
    if log is None: log = _log
    if not is_ext_dir(base_dir):
        raise KoExtError("`%s' isn't an extension source dir: there is no "
                         "'install.rdf' file (run `koext startext' first)"
                         % base_dir)

    src_dir = abspath(base_dir)
    
    # `build_ext` knows how to build the extension. We just call it and
    # use the .xpi it produces.
    custom_xpi_path = xpi_path
    xpi_path = build_ext(base_dir, ppdefines=ppdefines, log=log,
                         unjarred=unjarred, xpi_path=xpi_path,
                         additional_includes=additional_includes)

    destdir = None
    if distinstall:
        ko_info = KomodoInfo()
        destdir = ko_info.distext_base_dir

    if packed:
        if custom_xpi_path:
            # All done here.
            return
        # Copy the .xpi into the destination.
        if destdir is None:
            ko_info = KomodoInfo()
            destdir = ko_info.ext_base_dir
        # The xpi file most be named exactly as the ID in the install.rdf file.
        ext_info = ExtensionInfo(base_dir)
        destfile = join(destdir, ext_info.id + ".xpi")
        _cp(xpi_path, destfile)
    else:
        # Unzip the .xpi into the destination.
        komodo_unpack_xpi(xpi_path, destdir=destdir)

def komodo_unpack_xpi(xpi_path, log=None, destdir=None):
    """Unpack an extension .xpi file into a Komodo build.
    
    This command is for installing *core* Komodo extensions into a Komodo
    build. This is *not* a command for installing an extension into a
    Komodo installation.
    
    @param xpi_path {str} Path to the .xpi file.
    @param log {logging.Logger} Optional.
    @param destdir {str} Optional. The directory to extract into.
   """
    if log is None: log = _log
    if not isfile(xpi_path):
        raise KoExtError('%s is not a file' % xpi_path)
    ko_info = KomodoInfo()
    if destdir is None:
        destdir = ko_info.ext_base_dir
    # We don't know the extension directory name, until we have extracted the
    # xpi. Extract it to a temp dir and move that once we figured out the name.
    tmp_dir = join(destdir, '__%s' % basename(xpi_path))
    if exists(tmp_dir):
        _rm(tmp_dir, logstream=log.info)
    _mkdir(tmp_dir, logstream=log.info)
    unzip_exe = _get_unzip_exe()
    try:
        _run('"%s" -q "%s" -d "%s"' % (unzip_exe, xpi_path, tmp_dir), log.info)
        ext_info = ExtensionInfo(tmp_dir)
    except (OSError, KoExtError), e:
        _rm(tmp_dir, logstream=log.info)
        log.error(e)
        raise KoExtError("%s xpi_path is not a valid .xpi file" % xpi_path)
    install_dir = join(destdir, ext_info.id)
    if exists(install_dir):
        _rm(install_dir, logstream=log.info)
    _mv(tmp_dir, install_dir)
    
    print "installed to `%s'" % install_dir

def komodo_distunpack_xpi(xpi_path, log=None):
    """Unpack an extension .xpi file into a Komodo build.
    
    This command is for installing *core* Komodo extensions into a Komodo
    build. This is *not* a command for installing an extension into a
    Komodo installation.
    
    @param xpi_path {str} Path to the .xpi file.
    @param log {logging.Logger} Optional.
    """
    ko_info = KomodoInfo()
    destdir = ko_info.distext_base_dir
    komodo_unpack_xpi(xpi_path, log=log, destdir=destdir)

#---- internal support routines

class KomodoInfo(object):
    """Information about this Komodo build/installation.
    
    This class is meant to hide the details of whether you are working
    with a Komodo development build or just in the Komodo source tree
    or with a Komodo installation.
    """
    #TODO: Move this a new komodolib.py (or something like that).
    
    _where_am_i_cache = None
    @property
    def _where_am_i(self):
        """This module is running from one of three locations:
            source      the Komodo source tree
            build       in the Komodo/Mozilla $MOZ_OBJDIR tree
            install     in a Komodo installation (in the "SDK" area)
        """
        if self._where_am_i_cache is not None:
            return self._where_am_i_cache
        
        # from: src/sdk/pylib/koextlib.py
        #   to: Blackfile.py
        up_3_dir = dirname(dirname(dirname(dirname(abspath(__file__)))))
        if exists(join(up_3_dir, "Blackfile.py")):
            self._where_am_i_cache = "source"
            return "source"

        if sys.platform == "darwin":
            # from: .../dist/komodo-bits/sdk/pylib/koextlib.py
            #   to: .../dist/Komodo.app/Contents/MacOS/is_dev_tree.txt
            appBundle = join(up_3_dir, "Komodo.app")
            if not exists(appBundle):
                appBundle = join(up_3_dir, "KomodoDebug.app")
            is_dev_tree_txt = join(appBundle, "Contents", "MacOS",
                                   "is_dev_tree.txt")
        else:
            # from: .../dist/komodo-bits/sdk/pylib/koextlib.py
            #   to: .../dist/bin/is_dev_tree.txt
            is_dev_tree_txt = join(up_3_dir, "bin", "is_dev_tree.txt")
        if exists(is_dev_tree_txt):
            self._where_am_i_cache = "build"
            return "build"

        if sys.platform == "darwin":
            # from: .../Contents/SharedSupport/sdk/pylib/koextlib.py
            #   to: .../Contents/MacOS/komodo
            komodo_path = join(up_3_dir, "MacOS", "komodo")
        elif sys.platform == "win32":
            # from: ...\lib\sdk\pylib\koextlib.py
            #   to: ...\komodo.exe
            komodo_path = join(up_3_dir, "komodo.exe")
        else:
            # from: .../lib/sdk/pylib/koextlib.py
            #   to: .../bin/komodo
            komodo_path = join(up_3_dir, "bin", "komodo")
        if not exists(komodo_path):
            _log.warn("`%s' doesn't exist", komodo_path)
        self._where_am_i_cache = "install"
        return "install"
    
    @property
    def in_src_tree(self):
        return self._where_am_i == "source"

    @property
    def sdk_dir(self):
        if self._where_am_i == "source":
            return self._get_bkconfig_var("sdkDir")
        else:
            return dirname(dirname(abspath(__file__)))

    @property
    def typelib_path(self):
        return join(self.sdk_dir, "pylib", "typelib.py")

    @property
    def idl_dirs(self):
        dirs = []
        if self._where_am_i == "build":
            # HACK for Cons: For a clean build we can't (without insane effort)
            # sequence launching 'koext' in the Komodo SDK *after* the Mozilla
            # SDK IDLs have been copied to the Komodo SDK area.
            mozDist = dirname(dirname(dirname(dirname(__file__))))
            dirs.append(join(mozDist, "idl"))
        dirs.append(join(self.sdk_dir, "idl"))
        return dirs

    @property
    def udl_dir(self):
        return join(self.sdk_dir, "udl")

    _bkconfig_module_cache = None
    def _get_bkconfig_var(self, name):
        assert self._where_am_i == "source"
        if self._bkconfig_module_cache is None:
            ko_src_dir = dirname(dirname(dirname(dirname(__file__))))
            self._bkconfig_module_cache \
                = _module_from_path(join(ko_src_dir, "bkconfig.py"))
        return getattr(self._bkconfig_module_cache, name)

    @property
    def py_lib_dirs(self):
        return [join(self.moz_bin_dir, "python"),
                join(self.moz_bin_dir, "python", "komodo")]

    @property
    def moz_bin_dir(self):
        if self._where_am_i == "source":
            return self._get_bkconfig_var("mozBin")
        elif self._where_am_i == "build":
            up_3_dir = dirname(dirname(dirname(dirname(abspath(__file__)))))
            if sys.platform == "darwin":
                # from: .../dist/komodo-bits/sdk/pylib/koextlib.py
                #   to: .../dist/Komodo.app/Contents/MacOS
                appBundle = join(up_3_dir, "Komodo.app")
                if not exists(appBundle):
                    appBundle = join(up_3_dir, "KomodoDebug.app")
                return join(appBundle, "Contents", "MacOS")
            else:
                # from: .../dist/komodo-bits/sdk/pylib/koextlib.py
                #   to: .../dist/bin
                return join(up_3_dir, "bin")
        else: # self._where_am_i == "install"
            up_2_dir = dirname(dirname(dirname(abspath(__file__))))
            if sys.platform == "darwin":
                # from: .../Contents/SharedSupport/sdk/pylib/koextlib.py
                #   to: .../Contents/MacOS
                return join(dirname(up_2_dir), "MacOS")
            else:
                # from: .../lib/sdk/pylib/koextlib.py
                #   to: .../lib/mozilla
                return join(up_2_dir, "mozilla")
    
    @property
    def ext_base_dir(self):
        """The 'extensions' base dir in which extensions are installed."""
        return join(self.moz_bin_dir, "extensions")

    @property
    def distext_base_dir(self):
        """The 'distribution/bundle' base dir for hidden extensions."""
        return join(self.moz_bin_dir, "distribution", "bundles")

    @property
    def ext_dirs(self):
        """Generate all extension dirs in this Komodo installation
        *and* (TODO) for the current user.
        """
        # Extensions in the Komodo install tree.
        base_dir = self.ext_base_dir
        try:
            for d in os.listdir(base_dir):
                yield join(base_dir, d)
        except EnvironmentError:
            pass
        
        #TODO: Extensions in the user's app data dir.
    

class ExtensionInfo(object):
    """Information about this Komodo extension gathered from install.rdf."""
    def __init__(self, base_dir=os.curdir):
        self.base_dir = base_dir
        candidates = ["install.p.rdf", "install.rdf"]
        for name in candidates:
            path = normpath(join(base_dir, name))
            if exists(path):
                self._install_rdf_path = path
                break
        else:
            raise KoExtError("couldn't find any of '%s' for this project"
                             % "' or '".join(candidates))

    _install_rdf_info_cache = None
    @property
    def _install_rdf_info(self):
        if self._install_rdf_info_cache is None:
            info = {}
            install_rdf = open(self._install_rdf_path, 'r').read()
            id_pat = re.compile(r'<em:id>(.*?)</em:id>')
            info["id"] = id = id_pat.search(install_rdf).group(1)
            codename_pat = re.compile("(.*?)@(.*?)")
            try:
                info["codename"] = codename_pat.search(id).group(1) \
                                    .replace(' ', '_')
            except AttributeError:
                raise KoExtError("couldn't extract extension code name from "
                                 "the id, '%s': you must use an id of the "
                                 "form 'name@example.com'" % id)
            name_pat = re.compile(r'<em:name>(.*?)</em:name>')
            info["name"] = name_pat.search(install_rdf).group(1)
            ver_pat = re.compile(r'<em:version>(.*?)</em:version>')
            info["version"] = ver_pat.search(install_rdf).group(1)
            unpack_pat = re.compile(r'<em:unpack>true</em:unpack>')
            info["unpack"] = unpack_pat.search(install_rdf) and True or False
            self._install_rdf_info_cache = info
        return self._install_rdf_info_cache
    
    @property
    def name(self):
        return self._install_rdf_info["name"]

    @property
    def version(self):
        return self._install_rdf_info["version"]

    @property
    def id(self):
        return self._install_rdf_info["id"]

    @property
    def codename(self):
        return self._install_rdf_info["codename"]

    @property
    def pkg_name(self):
        return "%s-%s-ko.xpi" % (self.codename, self.version)

    @property
    def unpack(self):
        return self._install_rdf_info["unpack"]


def _code_safe_lang_from_lang(lang):
    """Return a language name safe to use in a code identifier for the
    given language name.
    
    Note that a leading number is not escaped.
    """
    safe_lang = lang.replace('+', 'P')  # e.g., nicer for C++
    return re.sub(r'[^-_.\w\d]+', '_', safe_lang)


# Recipe: module_from_path (1.0.1)
def _module_from_path(path):
    import imp, os
    dir = os.path.dirname(path) or os.curdir
    name = os.path.splitext(os.path.basename(path))[0]
    iinfo = imp.find_module(name, [dir])
    return imp.load_module(name, *iinfo)


# Recipe: query_yes_no_quit (1.0)
def _query_yes_no_quit(question, default="yes"):
    """Ask a yes/no/quit question via raw_input() and return their answer.
    
    "question" is a string that is presented to the user.
    "default" is the presumed answer if the user just hits <Enter>.
        It must be "yes" (the default), "no", "quit" or None (meaning
        an answer is required of the user).

    The "answer" return value is one of "yes", "no" or "quit".
    """
    valid = {"yes":"yes",   "y":"yes",    "ye":"yes",
             "no":"no",     "n":"no",
             "quit":"quit", "qui":"quit", "qu":"quit", "q":"quit"}
    if default == None:
        prompt = " [y/n/q] "
    elif default == "yes":
        prompt = " [Y/n/q] "
    elif default == "no":
        prompt = " [y/N/q] "
    elif default == "quit":
        prompt = " [y/n/Q] "
    else:
        raise ValueError("invalid default answer: '%s'" % default)

    while 1:
        sys.stdout.write(question + prompt)
        choice = raw_input().lower()
        if default is not None and choice == '':
            return default
        elif choice in valid.keys():
            return valid[choice]
        else:
            sys.stdout.write("Please repond with 'yes', 'no' or 'quit'.\n")


# Recipe: query (1.0)
def _query(preamble, default=None, prompt="> ", validate=None):
    """Ask the user a question using raw_input() and looking something
    like this:

        PREAMBLE
        Hit <Enter> to use the default, DEFAULT.
        PROMPT
        ...validate...

    Arguments:
        "preamble" is a string to display before the user is prompted
            (i.e. this is the question).
        "default" (optional) is a default value.
        "prompt" (optional) is the prompt string.
        "validate" (optional) is either a string naming a stock validator:\

                notempty        Ensure the user's answer is not empty.
                yes-or-no       Ensure the user's answer is 'yes' or 'no'.
                                ('y', 'n' and any capitalization are
                                also accepted)

            or a callback function with this signature:
                validate(answer) -> errmsg
            It should return None to indicate a valid answer.

            By default no validation is done.
    """
    if isinstance(validate, (str, unicode)):
        if validate == "notempty":
            def validate_notempty(answer):
                if not answer:
                    return "You must enter some non-empty value."
            validate = validate_notempty
        elif validate == "yes-or-no":
            def validate_yes_or_no(answer):
                if answer.lower() not in ('yes', 'no', 'y', 'n', 'ye'):
                    return "Please enter 'yes' or 'no'."
            validate = validate_yes_or_no
        else:
            raise ValueError("unknown stock validator: '%s'" % validate)
    
    def indented(text, indent=' '*4):
        lines = text.splitlines(1)
        return indent + indent.join(lines)

    sys.stdout.write(preamble+'\n')
    if default:
        sys.stdout.write("Hit <Enter> to use the default, %r.\n" % default)
    elif default is not None:
        default_str = default and repr(default) or '<empty>'
        sys.stdout.write("Hit <Enter> to leave blank.\n")
    while True:
        if True:
            answer = raw_input(prompt)
        else:
            sys.stdout.write(prompt)
            sys.stdout.flush()
            answer = sys.stdout.readline()
        if not answer and default:
            answer = default
        if validate is not None:
            errmsg = validate(answer)
            if errmsg:
                sys.stdout.write(errmsg+'\n')
                continue
        break
    return answer

def _symlink(source_path, target_path, force=False):
    """Make a symlink (if supported on this OS) or copy.
    
    @param source_path {str}
    @param target_path {str}
    @param force {bool} Whether to overwrite `target_path` if it exists.
        Default is false.
    """
    if exists(target_path) and force:
        os.remove(target_path)
    if sys.platform == "win32":
        _cp(source_path, target_path)
    else:
        _run('ln -s "%s" "%s"' % (source_path, target_path))


# Recipe: banner (1.0.1)
def _banner(text, ch='=', length=78):
    """Return a banner line centering the given text.
    
        "text" is the text to show in the banner. None can be given to have
            no text.
        "ch" (optional, default '=') is the banner line character (can
            also be a short string to repeat).
        "length" (optional, default 78) is the length of banner to make.

    Examples:
        >>> _banner("Peggy Sue")
        '================================= Peggy Sue =================================='
        >>> _banner("Peggy Sue", ch='-', length=50)
        '------------------- Peggy Sue --------------------'
        >>> _banner("Pretty pretty pretty pretty Peggy Sue", length=40)
        'Pretty pretty pretty pretty Peggy Sue'
    """
    if text is None:
        return ch * length
    elif len(text) + 2 + len(ch)*2 > length:
        # Not enough space for even one line char (plus space) around text.
        return text
    else:
        remain = length - (len(text) + 2)
        prefix_len = remain / 2
        suffix_len = remain - prefix_len
        if len(ch) == 1:
            prefix = ch * prefix_len
            suffix = ch * suffix_len
        else:
            prefix = ch * (prefix_len/len(ch)) + ch[:prefix_len%len(ch)]
            suffix = ch * (suffix_len/len(ch)) + ch[:suffix_len%len(ch)]
        return prefix + ' ' + text + ' ' + suffix


# Recipe: dedent (0.1.2)
def _dedentlines(lines, tabsize=8, skip_first_line=False):
    """_dedentlines(lines, tabsize=8, skip_first_line=False) -> dedented lines
    
        "lines" is a list of lines to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    Same as dedent() except operates on a sequence of lines. Note: the
    lines list is modified **in-place**.
    """
    DEBUG = False
    if DEBUG: 
        print "dedent: dedent(..., tabsize=%d, skip_first_line=%r)"\
              % (tabsize, skip_first_line)
    indents = []
    margin = None
    for i, line in enumerate(lines):
        if i == 0 and skip_first_line: continue
        indent = 0
        for ch in line:
            if ch == ' ':
                indent += 1
            elif ch == '\t':
                indent += tabsize - (indent % tabsize)
            elif ch in '\r\n':
                continue # skip all-whitespace lines
            else:
                break
        else:
            continue # skip all-whitespace lines
        if DEBUG: print "dedent: indent=%d: %r" % (indent, line)
        if margin is None:
            margin = indent
        else:
            margin = min(margin, indent)
    if DEBUG: print "dedent: margin=%r" % margin

    if margin is not None and margin > 0:
        for i, line in enumerate(lines):
            if i == 0 and skip_first_line: continue
            removed = 0
            for j, ch in enumerate(line):
                if ch == ' ':
                    removed += 1
                elif ch == '\t':
                    removed += tabsize - (removed % tabsize)
                elif ch in '\r\n':
                    if DEBUG: print "dedent: %r: EOL -> strip up to EOL" % line
                    lines[i] = lines[i][j:]
                    break
                else:
                    raise ValueError("unexpected non-whitespace char %r in "
                                     "line %r while removing %d-space margin"
                                     % (ch, line, margin))
                if DEBUG:
                    print "dedent: %r: %r -> removed %d/%d"\
                          % (line, ch, removed, margin)
                if removed == margin:
                    lines[i] = lines[i][j+1:]
                    break
                elif removed > margin:
                    lines[i] = ' '*(removed-margin) + lines[i][j+1:]
                    break
            else:
                if removed:
                    lines[i] = lines[i][removed:]
    return lines

def _dedent(text, tabsize=8, skip_first_line=False):
    """_dedent(text, tabsize=8, skip_first_line=False) -> dedented text

        "text" is the text to dedent.
        "tabsize" is the tab width to use for indent width calculations.
        "skip_first_line" is a boolean indicating if the first line should
            be skipped for calculating the indent width and for dedenting.
            This is sometimes useful for docstrings and similar.
    
    textwrap.dedent(s), but don't expand tabs to spaces
    """
    lines = text.splitlines(1)
    _dedentlines(lines, tabsize=tabsize, skip_first_line=skip_first_line)
    return ''.join(lines)

def _get_zip_exe(): 
    # On Windows we ship one. It should be the only platform that doesn't have
    # one handy.
    if sys.platform == "win32":
        zip_exe = join(dirname(dirname(abspath(__file__))), "bin", "zip.exe")
        if not exists(zip_exe):
            # We are running in Komodo source tree.
            zip_exe = "zip"
    else:
        zip_exe = "zip"
    return zip_exe

def _get_unzip_exe():
    # Not yet shipping this on Windows (because the only current user is
    # the internal `koext koinstall` command).
    return "unzip"


def _xpidl(idl_path, xpt_path, ko_info, logstream=None):
    assert xpt_path.endswith(".xpt")
    idl_name = splitext(basename(idl_path))[0]
    xpt_path_sans_ext = splitext(xpt_path)[0]
    includes = ['-I "%s"' % d for d in ko_info.idl_dirs + [dirname(idl_path)]]
    cmd = '"%s" "%s" %s -o %s.xpt %s' \
          % (sys.executable, ko_info.typelib_path, ' '.join(includes),
             xpt_path_sans_ext, idl_path)
    _run(cmd, logstream)


def _luddite_compile(udl_path, output_dir, ko_info):
    if ko_info.in_src_tree:
        udl_dev_dir = join(dirname(dirname(dirname(__file__))), "udl")
        sys.path.insert(0, udl_dev_dir)
        try:
            from ludditelib.commands import compile
        finally:
            del sys.path[0]
    else:
        from ludditelib.commands import compile
    compile(udl_path, output_dir, [ko_info.udl_dir], log=_log)

def _trim_files_in_dir(dir, patterns, log=None):
    if log:
        log("trim '%s' files under '%s'", "', '".join(patterns), dir)
    from fnmatch import fnmatch
    for dirpath, dirnames, filenames in os.walk(dir):
        for d in dirnames[:]:
            for pat in patterns:
                if fnmatch(d, pat):
                    _rmtree(join(dirpath, d))
                    dirnames.remove(d)
                    break
        for f in filenames[:]:
            for pat in patterns:
                if fnmatch(f, pat):
                    os.remove(join(dirpath, f))
                    break

# Recipe: rmtree (0.5)
def _rmtree_OnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)
def _rmtree(dirname):
    shutil.rmtree(dirname, 0, _rmtree_OnError)

# Recipe: run (0.5.3)
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
    fixed_cmd = cmd
    if sys.platform == "win32" and cmd.count('"') > 2:
        fixed_cmd = '"' + cmd + '"'
    retval = os.system(fixed_cmd)
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

def _preprocess(path, defines=None, logstream=None):
    """Preprocess the given `FOO.p.EXT` file to `FOO.EXT`.
    
    @param path {str} The input path to preprocess.
    @param defines {dict} A dict of preprocess defines.
    @param logstream {callable} A callable on this to log. This is expected to
        behave as does a Logger method, e.g. `logging.Logger.info`.
    """
    from os.path import split, join
    import preprocess
    dir, base = split(path)
    assert base.count(".p.") == 1, "unexpected input path: `%s'" % path
    output_path = join(dir, base.replace(".p.", "."))
    if logstream:
        logstream("preprocess `%s' to `%s' %r", path, output_path, defines)
    preprocess.preprocess(path, output_path, defines, force=True, keepLines=True)

def _rm(path, logstream=None):
    """My little lame cross-platform 'rm -rf'"""
    assert ' ' not in path,\
        "_rm: can't handle paths in spaces: '%s'" % path
    if sys.platform == "win32":
        path = path.replace("/", "\\")
        assert "*" not in path and "?" not in path,\
            "_rm on win32: can't yet handle wildcards: '%s'" % path
        if not exists(path):
            pass
        elif isdir(path):
            _run("rd /s/q %s" % path, logstream=logstream)
        else:
            if not os.access(path, os.W_OK):
                _run("attrib -R %s" % path, logstream=logstream)
            _run("del /q %s" % path, logstream=logstream)
    else:
        _run("rm -rf %s" % path, logstream=logstream)

def _mv(src, dest, logstream=None):
    """Move src (a file or a directory) to dest."""
    shutil.move(src, dest)

def _cp(src, dest, logstream=None):
    """My little lame cross-platform 'cp'"""
    dest_parent = dirname(dest)
    if dest_parent:
        _mkdir(dest_parent)
    if isdir(src):
        #shutil.copytree(src, dest)
        distutils.dir_util.copy_tree(src, dest)
    else:
        shutil.copy(src, dest)

def _mkdir(dir, logstream=None):
    """My little lame cross-platform 'mkdir -p'"""
    if exists(dir): return
    if logstream:
        logstream("mkdir %s" % dir)
    os.makedirs(dir)


# Recipe: paths_from_path_patterns (0.5.1)
def _should_include_path(path, includes, excludes):
    """Return True iff the given path should be included."""
    from os.path import basename
    from fnmatch import fnmatch

    base = basename(path)
    if includes:
        for include in includes:
            if fnmatch(base, include):
                try:
                    log.debug("include `%s' (matches `%s')", path, include)
                except (NameError, AttributeError):
                    pass
                break
        else:
            try:
                log.debug("exclude `%s' (matches no includes)", path)
            except (NameError, AttributeError):
                pass
            return False
    for exclude in excludes:
        if fnmatch(base, exclude):
            try:
                log.debug("exclude `%s' (matches `%s')", path, exclude)
            except (NameError, AttributeError):
                pass
            return False
    return True

def _walk(top, topdown=True, onerror=None, follow_symlinks=False):
    """A version of `os.walk()` with a couple differences regarding symlinks.
    
    1. follow_symlinks=False (the default): A symlink to a dir is
       returned as a *non*-dir. In `os.walk()`, a symlink to a dir is
       returned in the *dirs* list, but it is not recursed into.
    2. follow_symlinks=True: A symlink to a dir is returned in the
       *dirs* list (as with `os.walk()`) but it *is conditionally*
       recursed into (unlike `os.walk()`).
       
       A symlinked dir is only recursed into if it is to a deeper dir
       within the same tree. This is my understanding of how `find -L
       DIR` works.

    TODO: put as a separate recipe
    """
    from os.path import join, isdir, islink, abspath

    # We may not have read permission for top, in which case we can't
    # get a list of the files the directory contains.  os.path.walk
    # always suppressed the exception then, rather than blow up for a
    # minor reason when (say) a thousand readable directories are still
    # left to visit.  That logic is copied here.
    try:
        names = os.listdir(top)
    except OSError, err:
        if onerror is not None:
            onerror(err)
        return

    dirs, nondirs = [], []
    if follow_symlinks:
        for name in names:
            if isdir(join(top, name)):
                dirs.append(name)
            else:
                nondirs.append(name)
    else:
        for name in names:
            path = join(top, name)
            if islink(path):
                nondirs.append(name)
            elif isdir(path):
                dirs.append(name)
            else:
                nondirs.append(name)

    if topdown:
        yield top, dirs, nondirs
    for name in dirs:
        path = join(top, name)
        if follow_symlinks and islink(path):
            # Only walk this path if it links deeper in the same tree.
            top_abs = abspath(top)
            link_abs = abspath(join(top, os.readlink(path)))
            if not link_abs.startswith(top_abs + os.sep):
                continue
        for x in _walk(path, topdown, onerror, follow_symlinks=follow_symlinks):
            yield x
    if not topdown:
        yield top, dirs, nondirs

_NOT_SPECIFIED = ("NOT", "SPECIFIED")
def _paths_from_path_patterns(path_patterns, files=True, dirs="never",
                              recursive=True, includes=[], excludes=[],
                              skip_dupe_dirs=False,
                              follow_symlinks=False,
                              on_error=_NOT_SPECIFIED):
    """_paths_from_path_patterns([<path-patterns>, ...]) -> file paths

    Generate a list of paths (files and/or dirs) represented by the given path
    patterns.

        "path_patterns" is a list of paths optionally using the '*', '?' and
            '[seq]' glob patterns.
        "files" is boolean (default True) indicating if file paths
            should be yielded
        "dirs" is string indicating under what conditions dirs are
            yielded. It must be one of:
              never             (default) never yield dirs
              always            yield all dirs matching given patterns
              if-not-recursive  only yield dirs for invocations when
                                recursive=False
            See use cases below for more details.
        "recursive" is boolean (default True) indicating if paths should
            be recursively yielded under given dirs.
        "includes" is a list of file patterns to include in recursive
            searches.
        "excludes" is a list of file and dir patterns to exclude.
            (Note: This is slightly different than GNU grep's --exclude
            option which only excludes *files*.  I.e. you cannot exclude
            a ".svn" dir.)
        "skip_dupe_dirs" can be set True to watch for and skip
            descending into a dir that has already been yielded. Note
            that this currently does not dereference symlinks.
        "follow_symlinks" is a boolean indicating whether to follow
            symlinks (default False). To guard against infinite loops
            with circular dir symlinks, only dir symlinks to *deeper*
            dirs are followed.
        "on_error" is an error callback called when a given path pattern
            matches nothing:
                on_error(PATH_PATTERN)
            If not specified, the default is look for a "log" global and
            call:
                log.error("`%s': No such file or directory")
            Specify None to do nothing.

    Typically this is useful for a command-line tool that takes a list
    of paths as arguments. (For Unix-heads: the shell on Windows does
    NOT expand glob chars, that is left to the app.)

    Use case #1: like `grep -r`
      {files=True, dirs='never', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield nothing
        script PATH*    # yield all files matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #2: like `file -r` (if it had a recursive option)
      {files=True, dirs='if-not-recursive', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files (not dirs) recursively under DIR
        script -r PATH* # yield files matching PATH* and files recursively
                        # under dirs matching PATH*; if none, call
                        # on_error(PATH*) callback

    Use case #3: kind of like `find .`
      {files=True, dirs='always', recursive=(if '-r' in opts)}
        script FILE     # yield FILE, else call on_error(FILE)
        script DIR      # yield DIR, else call on_error(DIR)
        script PATH*    # yield all files and dirs matching PATH*; if none,
                        # call on_error(PATH*) callback
        script -r DIR   # yield files and dirs recursively under DIR
                        # (including DIR)
        script -r PATH* # yield files and dirs matching PATH* and recursively
                        # under dirs; if none, call on_error(PATH*)
                        # callback

    TODO: perf improvements (profile, stat just once)
    """
    from os.path import basename, exists, isdir, join, normpath, abspath, \
                        lexists, islink, realpath
    from glob import glob

    assert not isinstance(path_patterns, basestring), \
        "'path_patterns' must be a sequence, not a string: %r" % path_patterns
    GLOB_CHARS = '*?['

    if skip_dupe_dirs:
        searched_dirs = set()

    for path_pattern in path_patterns:
        # Determine the set of paths matching this path_pattern.
        for glob_char in GLOB_CHARS:
            if glob_char in path_pattern:
                paths = glob(path_pattern)
                break
        else:
            if follow_symlinks:
                paths = exists(path_pattern) and [path_pattern] or []
            else:
                paths = lexists(path_pattern) and [path_pattern] or []
        if not paths:
            if on_error is None:
                pass
            elif on_error is _NOT_SPECIFIED:
                try:
                    log.error("`%s': No such file or directory", path_pattern)
                except (NameError, AttributeError):
                    pass
            else:
                on_error(path_pattern)

        for path in paths:
            if (follow_symlinks or not islink(path)) and isdir(path):
                if skip_dupe_dirs:
                    canon_path = normpath(abspath(path))
                    if follow_symlinks:
                        canon_path = realpath(canon_path)
                    if canon_path in searched_dirs:
                        continue
                    else:
                        searched_dirs.add(canon_path)

                # 'includes' SHOULD affect whether a dir is yielded.
                if (dirs == "always"
                    or (dirs == "if-not-recursive" and not recursive)
                   ) and _should_include_path(path, includes, excludes):
                    yield path

                # However, if recursive, 'includes' should NOT affect
                # whether a dir is recursed into. Otherwise you could
                # not:
                #   script -r --include="*.py" DIR
                if recursive and _should_include_path(path, [], excludes):
                    for dirpath, dirnames, filenames in _walk(path, 
                            follow_symlinks=follow_symlinks):
                        dir_indeces_to_remove = []
                        for i, dirname in enumerate(dirnames):
                            d = join(dirpath, dirname)
                            if skip_dupe_dirs:
                                canon_d = normpath(abspath(d))
                                if follow_symlinks:
                                    canon_d = realpath(canon_d)
                                if canon_d in searched_dirs:
                                    dir_indeces_to_remove.append(i)
                                    continue
                                else:
                                    searched_dirs.add(canon_d)
                            if dirs == "always" \
                               and _should_include_path(d, includes, excludes):
                                yield d
                            if not _should_include_path(d, [], excludes):
                                dir_indeces_to_remove.append(i)
                        for i in reversed(dir_indeces_to_remove):
                            del dirnames[i]
                        if files:
                            for filename in sorted(filenames):
                                f = join(dirpath, filename)
                                if _should_include_path(f, includes, excludes):
                                    yield f

            elif files and _should_include_path(path, includes, excludes):
                yield path
