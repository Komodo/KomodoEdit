
"""Makefile for the 'komodo' project.

${common_task_list}

See `mk -h' for options.
"""

import os
from os.path import join, dirname, normpath, abspath, isabs, exists, \
                    splitext, basename
import re
import sys
from pprint import pprint
import codecs
from collections import defaultdict
import subprocess

from mklib import Task, Configuration, Alias, include
from mklib import sh
from mklib import utils
from mklib.common import MkError

sys.path.insert(0, join(dirname(__file__), "util"))
import buildsupport

sys.path.append(join(dirname(__file__), "contrib", "zope", "cachedescriptors", "src"))
sys.path.insert(0, join(dirname(__file__), "src", "python-sitelib"))
import textinfo



include("util/checktasks.py", ns="check")


class cfg(Configuration):
    prefix = "bk"


class langpack(Task):
    """Make a lang-pack XPI for translation on babelzilla.org.
    
    See this thread for background:
    http://community.activestate.com/forum-topic/localizing-komodo-using-babelzilla-dream-team
    """
    LANGPACK_VERSION = "0.1"

    def _svnversion_from_dir(self, dir):
        try:
            p = subprocess.Popen(["svnversion"], cwd=dir, stdout=subprocess.PIPE)
        except EnvironmentError, ex:
            self.log.debug("error running 'svnversion': %s", ex)
            return None
        version = p.stdout.read().strip()
        status = p.wait()
        if status:
            self.log.debug("error running 'svnversion': status=%r", status)
            return None
        return version

    def _writefile(self, path, content, encoding=None):
        self.log.info("create `%s'", path)
        f = codecs.open(path, 'w', encoding)
        try:
            f.write(content)
        finally:
            f.close()

    def make(self):
        build_dir = join(self.dir, "build", "langpack")
        pkg_dir = join(self.dir, "packages")
        locale_dir = join(self.dir, "src", "chrome", "komodo", "locale")
        
        # Clean build dir.
        if exists(build_dir):
            sh.rm(build_dir, self.log)
        os.makedirs(build_dir)
        
        # Version
        ver_bits = [self.LANGPACK_VERSION,
                    self._svnversion_from_dir(locale_dir)]
        version = '.'.join([v for v in ver_bits if v])

        # Create the package contents.
        os.makedirs(join(build_dir, "chrome"))
        sh.cp(locale_dir, join(build_dir, "chrome", "locale"),
              recursive=True,
              log=self.log.info)
        for dirpath, dnames, fnames in os.walk(build_dir):
            if ".svn" in dnames:
                sh.rm(join(dirpath, ".svn"), self.log)
                dnames.remove(".svn")
            for fname in [".consign", "Conscript"]:
                if fname in fnames:
                    sh.rm(join(dirpath, fname), self.log)
        self._writefile(join(build_dir, "chrome.manifest"),
                        "locale komodo-langpack en-US chrome/locale/en-US/")
        self._writefile(join(build_dir, "install.rdf"), _dedent("""\
            <?xml version="1.0"?>
            
            <RDF xmlns="http://www.w3.org/1999/02/22-rdf-syntax-ns#"
                 xmlns:em="http://www.mozilla.org/2004/em-rdf#">
            
              <Description about="urn:mozilla:install-manifest">
                <em:name>Komodo Langpack</em:name>
                <em:description>Interface Langpack for Komodo</em:description>
                <em:version>%s</em:version>
                <em:id>komodo-langpack@ActiveState.com</em:id>
                <em:creator>ActiveState</em:creator>
                <em:type>2</em:type>

                <!-- Komodo IDE -->
                <em:targetApplication>
                  <Description>
                    <em:id>{36E66FA0-F259-11D9-850E-000D935D3368}</em:id>
                    <em:minVersion>4.0</em:minVersion>
                    <em:maxVersion>5.*</em:maxVersion>
                  </Description>
                </em:targetApplication>
                <!-- Komodo Edit -->
                <em:targetApplication>
                  <Description>
                    <em:id>{b1042fb5-9e9c-11db-b107-000d935d3368}</em:id>
                    <em:minVersion>4.0</em:minVersion>
                    <em:maxVersion>5.*</em:maxVersion>
                  </Description>
                </em:targetApplication>
            </Description>
            </RDF>
            """ % version))
        
        # Package it up.
        if not exists(pkg_dir):
            os.makedirs(pkg_dir)
        pkg_name = ["Komodo", "LangPack", version]
        pkg_name = '-'.join(pkg_name) + ".xpi"
        pkg_path = join(pkg_dir, pkg_name)
        sh.run_in_dir('zip -rq "%s" .' % abspath(pkg_path), build_dir,
                      self.log.info)
        self.log.info("created `%s'", pkg_path)


class todo(Task):
    """Print out todo's and xxx's in the docs area."""
    def make(self):
        excludes = [".svn", "*.pyc", "TO""DO.txt",
                    "*.png", "*.gif", "build", "preprocess.py",
                    "externals"]
        paths = buildsupport.paths_from_path_patterns(['.'], excludes=excludes)
        for path in paths:
            self._dump_pattern_in_path("TO\DO\\|XX\X", normpath(path))

    def _dump_pattern_in_path(self, pattern, path):
        os.system('grep -nH "%s" "%s"' % (pattern, path))


class lscolors(Task):
    """List colors used in the Mozilla toolkit themes."""
    def make(self):
        themes_dir = join(self.cfg.mozSrc, "mozilla", "toolkit", "themes")
        
        color_names = set()
        for css_path in utils.paths_from_path_patterns(
                            [themes_dir], includes=["*.css"]):
            for color_name in self._color_names_from_css_path(css_path):
                if color_name not in color_names:
                    color_names.add(color_name)
                    print color_name

    # This doesn't get colors listed in groups CSS productions like
    #   border: 1px solid black;
    _css_color_re = re.compile("(?:\w-)?color\s*: (?P<color>.*?)[;}]")
    def _color_names_from_css_path(self, css_path):
        #print css_path
        css = open(css_path, 'r').read()
        for hit in self._css_color_re.findall(css):
            color = hit.strip()
            if color.endswith("!important"):
                color = color.rsplit(None, 1)[0]
            yield color


class lsunusedentities(Task):
    """List unused entities in Komodo's chrome/locale/en-US.
    
    This isn't yet doing the match up of which XUL files pull in which
    DTD files, so the results aren't perfect.
    """
    dtd_paths_from_entity = None
    duplicate_entities = None
    
    def make(self):
        en_us_dir = join(dirname(__file__), "src", "chrome", "komodo",
                         "locale", "en-US")
        content_dir = join(dirname(__file__), "src", "chrome", "komodo",
                           "content")
        
        entities = self.entities_from_locale_dir(en_us_dir)
        if self.duplicate_entities:
            self.log.warn("have %d entities with the same name",
                          len(self.duplicate_entities))

        entity_use_re = re.compile("&(.*?);")
        for xul_path in utils.paths_from_path_patterns(
                            [content_dir], includes=["*.xul"]):
            xul = open(xul_path, 'r').read()
            for entity in entity_use_re.findall(xul):
                entities.discard(entity)
        for entity in entities:
            print entity
        if entities:
            self.log.info("%d unused entities", len(entities))
    
    def entities_from_locale_dir(self, locale_dir):
        self.duplicate_entities = set()
        self.dtd_paths_from_entity = defaultdict(set)
        entities = set()
        for dtd_path in utils.paths_from_path_patterns(
                            [locale_dir], includes=["*.dtd"]):
            for entity in self._entities_from_dtd_path(dtd_path):
                self.dtd_paths_from_entity[entity].add(dtd_path)
                if entity in entities:
                    self.duplicate_entities.add(entity)
                    #self.log.warn("duplicate entity: %r (one defn in `%s')",
                    #              entity, dtd_path)
                else:
                    entities.add(entity)
        return entities
    
    _dtd_entity_re = re.compile('<!ENTITY ([\.\w]+) ".*?">')
    def _entities_from_dtd_path(self, dtd_path):
        #print "\n-- ", dtd_path
        dtd = open(dtd_path, 'r').read()
        for hit in self._dtd_entity_re.findall(dtd):
            #print hit
            yield hit


class lsnosvneolstyle(Task):
    """List text files in the working copy without svn:eol-style set.
    
    The main point of this is that Komodo's source files in SVN should set
    `svn:eol-style=native` because not doing so can cause minor headaches
    E.g. patching files on Windows resets the EOLs in the file '\r\n',
    if the file is using '\n' EOLs then you get useless `svn diff` results.
    """
    def make(self):
        for path in self._no_svn_eol_style_files(os.curdir):
            print path

    def _no_svn_eol_style_files(self, d):
        from os.path import split
        for path in self._files_in_svn(d):
            ti = textinfo.textinfo_from_path(path)
            if not ti.is_text:
                continue
            if "svn:eol-style" in _svn_proplist(*split(path)):
                continue
            yield path

    def _files_in_svn(self, d):
        p = subprocess.Popen(["svn", "ls", "-R", d], stdout=subprocess.PIPE)
        for line in p.stdout.readlines():
            path = line.strip()
            if path.endswith("/"):
                continue
            yield normpath(path)


class svneolstylenative(lsnosvneolstyle):
    """Set svn:eol-style=native for text files under the current dir
    that don't already have it set.
    """
    def make(self):
        for path in self._no_svn_eol_style_files(os.curdir):
            os.system('svn propset svn:eol-style native "%s"' % path)

class sortcontributors(Task):
    """Sort CONTRIBUTORS.txt."""
    def make(self):
        path = "CONTRIBUTORS.txt"
        content = codecs.open(path, 'r', 'utf-8').read()
        lines = [ln.strip() for ln in content.splitlines(0) if ln.strip()]
        lines.sort(key=lambda s: s.split(None, 1)[1])
        eol = {"win32": "\r\n"}.get(sys.platform, "\n")
        codecs.open(path, 'w', 'utf-8').write(eol.join(lines) + eol)



#---- internal support stuff

def _svn_propfiles(root, fn):  # Derived from Python's Tools/scripts/svneol.py
    default = os.path.join(root, ".svn", "props", fn+".svn-work")
    try:
        format = int(open(os.path.join(root, ".svn", "format")).read().strip())
    except IOError:
        return []
    if format in (4, 8):
        # In version 8, committed props are stored in prop-base,
        # local modifications in props
        return [os.path.join(root, ".svn", "prop-base", fn+".svn-base"),
                os.path.join(root, ".svn", "props", fn+".svn-work")]
    raise ValueError, "Unknown repository format"

def _svn_proplist(root, fn):  # from Python's Tools/scripts/svneol.py
    "Return a list of property names for file fn in directory root"
    result = []
    for path in _svn_propfiles(root, fn):
        try:
            f = open(path)
        except IOError:
            # no properties file: not under version control,
            # or no properties set
            continue
        while 1:
            # key-value pairs, of the form
            # K <length>
            # <keyname>NL
            # V length
            # <value>NL
            # END
            line = f.readline()
            if line.startswith("END"):
                break
            if not line.strip():  # format 4: prop file can be empty
                break
            assert line.startswith("K "), "unexpected content in `%s': line=%r" % (path, line)
            L = int(line.split()[1])
            key = f.read(L)
            result.append(key)
            f.readline()
            line = f.readline()
            assert line.startswith("V ")
            L = int(line.split()[1])
            value = f.read(L)
            f.readline()
        f.close()
    return result

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

