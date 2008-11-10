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
                        #   As well, "lang_LANG.py" files here define codeintel
                        #   language support.

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
                    normpath, abspath
import sys
import re
import uuid
import logging
import tempfile
from glob import glob
from pprint import pprint


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

    <em:targetApplication> <!-- Komodo IDE -->
      <Description>
        <em:id>{36E66FA0-F259-11D9-850E-000D935D3368}</em:id>
        <em:minVersion>4.1</em:minVersion>
        <em:maxVersion>5.*</em:maxVersion>
      </Description>
    </em:targetApplication>
    <em:targetApplication> <!-- Komodo Edit -->
      <Description>
        <em:id>{b1042fb5-9e9c-11db-b107-000d935d3368}</em:id>
        <em:minVersion>4.1</em:minVersion>
        <em:maxVersion>5.*</em:maxVersion>
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
            open(mainlex_path, 'w').write(_dedent("""
                # UDL for %(lang)s
                
                language %(lang)s
                
                #...
                """ % locals()).lstrip())

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
            lang_from_udl_family = {'M': 'HTML'}
        else:
            base_module = "koUDLLanguageBase"
            base_class = "KoUDLLanguage"
            lang_from_udl_family = {}
    
        lang_svc = _dedent("""
            # Komodo %(lang)s language service.
            
            import logging
            from %(base_module)s import %(base_class)s
    
    
            log = logging.getLogger("ko%(safe_lang)sLanguage")
            #log.setLevel(logging.DEBUG)
    
    
            def registerLanguage(registry):
                log.debug("Registering language %(lang)s")
                registry.registerLanguage(Ko%(safe_lang)sLanguage())
    
    
            class Ko%(safe_lang)sLanguage(%(base_class)s):
                name = "%(lang)s"
                lexresLangName = "%(safe_lang)s"
                _reg_desc_ = "%%s Language" %% name
                _reg_contractid_ = "@activestate.com/koLanguage?language=%%s;1" %% name
                _reg_clsid_ = "%(guid)s"
                %(default_ext_assign)s
            
                #TODO: Update 'lang_from_udl_family' as appropriate for your
                #      lexer definition. There are four UDL language families:
                #           M (markup), i.e. HTML or XML
                #           CSL (client-side language), e.g. JavaScript
                #           SSL (server-side language), e.g. Perl, PHP, Python
                #           TPL (template language), e.g. RHTML, Django, Smarty
                #      'lang_from_udl_family' maps each UDL family code (M,
                #      CSL, ...) to the sub-langauge name in your language.
                #      Some examples:
                #        lang_from_udl_family = {   # A PHP file can contain
                #           'M': 'HTML',            #   HTML
                #           'SSL': 'PHP',           #   PHP
                #           'CSL': 'JavaScript',    #   JavaScript
                #        }
                #        lang_from_udl_family = {   # An RHTML file can contain
                #           'M': 'HTML',            #   HTML
                #           'SSL': 'Ruby',          #   Ruby
                #           'CSL': 'JavaScript',    #   JavaScript
                #           'TPL': 'RHTML',         #   RHTML template code
                #        }
                #        lang_from_udl_family = {   # A plain XML can just contain
                #           'M': 'XML',             #   XML
                #        }
                lang_from_udl_family = %(lang_from_udl_family)r
            """ % locals()).lstrip()
    
        if not dry_run and not exists(dirname(lang_svc_path)):
            _mkdir(dirname(lang_svc_path), log.debug)
        log.info("create %s (language service)", lang_svc_path)
        if not dry_run:
            open(lang_svc_path, 'w').write(lang_svc)

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

    # Create codeintel/lang_${lang}.py
    lang_path = normpath(join(base_dir, "pylib",
                              "lang_%s.py" % safe_lang.lower()))
    if exists(lang_path) and not force:
        log.warn("`%s' exists (skipping, use --force to override)",
                 lang_path)
    else:
        if not dry_run and not exists(dirname(lang_path)):
            _mkdir(dirname(lang_path), log.debug)
        log.info("create %s (codeintel language master)", lang_path)
        if not dry_run:
            template_path = join(ko_info.sdk_dir, "share",
                                 "lang_LANG.py")
            import string
            template = string.Template(open(template_path).read())
            content = template.safe_substitute(
                {"lang": lang,
                 "safe_lang": safe_lang,
                 "safe_lang_lower": safe_lang.lower(),
                 "safe_lang_upper": safe_lang.upper()})
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



def build_ext(base_dir, log=None):
    """Build a Komodo extension from the sources in the given dir.
    
    This reads the "install.rdf" in this directory and the appropriate
    source files to create a Komodo .xpi extension.
    
    - Files in "chrome/..." are put into a jar file.
    - IDL and PyXPCOM components in "components/..." are handled
      appropriately.
    - etc. (see `koext help hooks' for more details)
    """
    if log is None: log = _log
    if not is_ext_dir(base_dir):
        raise KoExtError("`%s' isn't an extension source dir: there is no "
                         "'install.rdf' file (run `koext startext' first)"
                         % base_dir)

    # Need a zip executable for building. On Windows we ship one. It
    # should be the only platform that doesn't have one handy.
    if sys.platform == "win32":
        zip_exe = join(dirname(dirname(abspath(__file__))), "bin", "zip.exe")
        if not exists(zip_exe):
            # We are running in Komodo source tree.
            zip_exe = "zip"
    else:
        zip_exe = "zip"

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
        
        ext_info = ExtensionInfo(base_dir)
        ko_info = KomodoInfo()
        xpi_manifest = ["install.rdf"]
        
        # Make the chrome jar.
        chrome_dirs = [d for d in ("content", "skin", "locale") if isdir(d)]
        if chrome_dirs:
            assert exists("chrome.manifest"), \
                "you have chrome dirs ('%s') but no 'chrome.manifest' file" \
                % "', '".join(chrome_dirs)
            jar_build_dir = join(build_dir, "jar")
            _mkdir(jar_build_dir, log.info)
            for d in chrome_dirs:
                _cp(d, join(jar_build_dir, d), log.info)
            _trim_files_in_dir(jar_build_dir, [".svn", ".hg", "CVS"], log.info)
            _run_in_dir('"%s" -X -r %s.jar *' % (zip_exe, ext_info.codename),
                        jar_build_dir, log.info)
    
            xpi_manifest += [
                join(jar_build_dir, ext_info.codename+".jar"),
                "chrome.manifest",
            ]
    
        # Handle any PyXPCOM components and idl.
        if isdir("components"):
            components_build_dir = join(build_dir, "components")
            _mkdir(components_build_dir, log.info)
            for path in glob(join("components", "*")):
                _cp(path, components_build_dir, log.info)
            _trim_files_in_dir(components_build_dir,
                               [".svn", ".hg", "CVS", "*.pyc", "*.pyo"],
                               log.info)
            xpi_manifest.append(components_build_dir)
            
            idl_build_dir = join(build_dir, "idl")
            idl_paths = glob(join("components", "*.idl"))
            if idl_paths:
                _mkdir(idl_build_dir, log.info)
                for idl_path in glob(join("components", "*.idl")):
                    _cp(idl_path, idl_build_dir, log.info)
                    xpt_path = join(components_build_dir,
                        splitext(basename(idl_path))[0] + ".xpt")
                    _xpidl(idl_path, xpt_path, ko_info, log.info)
                xpi_manifest.append(idl_build_dir)
    
        # Handle any UDL lexer compilation.
        lexers_dir = join(build_dir, "lexers")
        for mainlex_udl_path in glob(join("udl", "*-mainlex.udl")):
            if not exists(lexers_dir):
                _mkdir(lexers_dir, log.info)
            _luddite_compile(mainlex_udl_path, lexers_dir, ko_info)
        if exists(lexers_dir):
            xpi_manifest.append(lexers_dir)
    
        # Remaining hook dirs that are just included verbatim in the XPI.
        for dname in ("templates", "apicatalogs", "xmlcatalogs", "pylib",
                      "project-templates", "platform", "defaults", "plugins",
                      "searchplugins", "dictionaries"):
            if isdir(dname):
                xpi_manifest.append(dname)
    
        # Handle XML catalogs (**for compatibility with Komodo <=4.2.1**)
        # Komodo version <=4.2.1 only looked for 'catalog.xml' files for
        # XML autocomplete in the *top-level* of extension dirs. In Komodo
        # versions >=4.2.2 this has moved to 'xmlcatalogs/catalog.xml'
        # (although for a transition period Komodo looks in both areas).
        if isdir("xmlcatalogs"):
            for path in glob(join("xmlcatalogs", "*")):
                xpi_manifest.append(path)
    
        # Make the xpi.
        #pprint(xpi_manifest)
        xpi_build_dir = join(build_dir, "xpi")
        _mkdir(xpi_build_dir, log.info)
        for src in xpi_manifest:
            if isdir(src):
                _cp(src, join(xpi_build_dir, basename(src)), log.info)
            else:
                _cp(src, xpi_build_dir, log.info)
        _trim_files_in_dir(xpi_build_dir, [".svn", ".hg", "CVS"], log.info)
        _run_in_dir('"%s" -X -r %s *' % (zip_exe, ext_info.pkg_name),
                    xpi_build_dir, log.info)
        _cp(join(xpi_build_dir, ext_info.pkg_name), ext_info.pkg_name, log.info)
    finally:
        if orig_dir:
            log.info("cd %s", orig_dir)
            os.chdir(orig_dir)
            base_dir = orig_base_dir

    print "'%s' created." % join(base_dir, ext_info.pkg_name)



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

        # from: .../dist/komodo-bits/sdk/pylib/koextlib.py
        #   to: .../dist/bin
        if exists(join(up_3_dir, "bin", "is_dev_tree.txt")):
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
        assert exists(komodo_path)
        self._where_am_i_cache = "install"
        return "install"
    
    @property
    def in_src_tree(self):
        # DEPRECATED
        return self._where_am_i == "source"

    @property
    def xpidl_path(self):
        exe_ext = (".exe" if sys.platform == "win32" else "")
        return join(self.sdk_dir, "bin", "xpidl"+exe_ext)

    @property
    def sdk_dir(self):
        return dirname(dirname(abspath(__file__)))

    @property
    def idl_dir(self):
        return join(self.sdk_dir, "idl")

    @property
    def udl_dir(self):
        if self._where_am_i == "source":
            return join(dirname(self.sdk_dir), "udl", "udl")
        else:
            return join(self.sdk_dir, "udl")

    def _get_bkconfig_var(self, name):
        assert self._where_am_i == "source"
        ko_src_dir = dirname(dirname(dirname(dirname(__file__))))
        module = _module_from_path(join(ko_src_dir, "bkconfig.py"))
        return getattr(module, name)

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
                return join(up_3_dir, "Komodo.app", "Contents", "MacOS")
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
    def ext_dirs(self):
        """Generate all extension dirs in this Komodo installation
        *and* (TODO) for the current user.
        """
        # Extensions in the Komodo install tree.
        base_dir = join(self.moz_bin_dir, "extensions")
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


def _xpidl(idl_path, xpt_path, ko_info, logstream=None):
    assert xpt_path.endswith(".xpt")
    idl_name = splitext(basename(idl_path))[0]
    xpt_path_sans_ext = splitext(xpt_path)[0]
    cmd = '"%s" -I "%s" -I "%s" -o %s -m typelib %s' \
          % (ko_info.xpidl_path, ko_info.idl_dir, dirname(idl_path),
             xpt_path_sans_ext, idl_path)
    _run(cmd, logstream)


def _luddite_compile(udl_path, output_dir, ko_info):
    if ko_info.in_src_tree:
        sys.path.insert(0, dirname(ko_info.udl_dir))
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
    import shutil
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
    """My little lame cross-platform 'mv'"""
    assert ' ' not in src and ' ' not in dest,\
        "_mv: can't handle paths in spaces: src=%r, dest=%r" % (src, dest)
    if sys.platform == "win32":
        _run("move %s %s" % (src, dest), logstream=logstream)
    else:
        _run("mv %s %s" % (src, dest), logstream=logstream)

def _cp(src, dest, logstream=None):
    """My little lame cross-platform 'cp'"""
    assert ' ' not in src and ' ' not in dest,\
        "_cp: can't handle paths in spaces: src=%r, dest=%r" % (src, dest)
    if sys.platform == "win32":
        src = src.replace("/", "\\")
        dest = dest.replace("/", "\\")
        if isdir(src):
            _run("xcopy /e/i/y/q %s %s" % (src, dest), logstream=logstream)
        else:
            _run("copy /y %s %s" % (src, dest), logstream=logstream)
    else:
        if isdir(src):
            _run("cp -R %s %s" % (src, dest), logstream=logstream)
        else:
            _run("cp %s %s" % (src, dest), logstream=logstream)

def _mkdir(dir, logstream=None):
    """My little lame cross-platform 'mkdir -p'"""
    if exists(dir): return
    if logstream:
        logstream("mkdir %s" % dir)
    os.makedirs(dir)


