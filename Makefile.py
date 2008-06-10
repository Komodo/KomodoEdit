
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
from collections import defaultdict

from mklib import Task, Configuration, Alias, include
from mklib import sh
from mklib import utils
from mklib.common import MkError

sys.path.insert(0, join(dirname(__file__), "util"))
import buildsupport


include("util/checktasks.py", ns="check")


class cfg(Configuration):
    prefix = "bk"


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
