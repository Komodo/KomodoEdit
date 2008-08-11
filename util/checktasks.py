
"""Tasks for checking things in the Komodo source tree.

    mk check:*
"""

import os
from os.path import join, dirname, normpath, abspath, isabs, exists, \
                    splitext, basename
import re
import sys
from pprint import pprint
from glob import glob

from mklib import Task, Alias
from mklib import sh
from mklib.common import MkError


class all(Alias):
    deps = ["langinfo"]
    default = True

class langinfo(Task):
    """Check if langinfo has all the ko*Language files that Komodo defines."""

    def get_lidb(self):
        pylib_dir = join(dirname(self.dir), "src", "python-sitelib")
        sys.path.insert(0, pylib_dir)
        import langinfo
        return langinfo.get_default_database()

    def gen_ko_langs_and_exts(self):
        languages_dir = join(dirname(self.dir), "src", "languages")
        udl_skel_dir = join(dirname(self.dir), "src", "udl", "skel")
        name_re = re.compile(r'''^    name = ('|")(.*?)\1''', re.M)
        ext_re = re.compile(r'''^    defaultExtension = (?:('|")(.*?)\1|None)''', re.M)
        skips = set(["koErrorLanguage.py", "koRegexLanguage.py",
                     "koRxLanguage.py", "koOthersLanguage.py"])
        hacks = {
            "koSQLLanguage.py": {
                "ext_hits": [('"', '.sql'), ('"', '.sql')],
            },
            "koTeXLanguage.py": {
                "ext_hits": [('"', '.tex'), ('"', '.tex'), ('"', None)],
            },
        }
        for comp_path in glob(join(languages_dir, "ko*Language.*py")) \
                + glob(join(udl_skel_dir, "*", "components", "ko*Language.py")):
            comp_base = basename(comp_path)
            if comp_base in skips:
                continue
            content = open(comp_path, 'r').read()
            name_hits = name_re.findall(content)
            ext_hits = ext_re.findall(content)
            if comp_base in hacks:
                if "ext_hits" in hacks[comp_base]:
                    ext_hits = hacks[comp_base]["ext_hits"]
            if len(name_hits) != len(ext_hits):
                raise MkError("%d 'name' hits and %d 'ext' hits for %r"
                              % (len(name_hits), len(ext_hits), comp_path))
            for n, e in zip(name_hits, ext_hits):
                yield n[1], e[1]

    def make(self):
        lidb = self.get_lidb()
        li_langs = set(hasattr(li, "komodo_name") and li.komodo_name or li.name
                       for li in lidb.langinfos())
        ko_ext_from_lang = dict(i for i in self.gen_ko_langs_and_exts())

        num_warnings = 0
        for li in lidb.langinfos():
            if not li.is_text:
                continue
            if li.name not in ko_ext_from_lang:
                print "warning: `%s' langinfo not in Komodo" % li.name
                num_warnings += 1

        num_errors = 0
        for ko_lang in sorted(ko_ext_from_lang):
            if ko_lang not in li_langs:
                ext = ko_ext_from_lang[ko_lang]
                ext_str = ext and (" (ext: %s)" % ext) or ""
                print "error: `%s' Komodo lang%s not in langinfo" \
                      % (ko_lang, ext_str)
                num_errors += 1

        self.log.info("%d errors, %d warnings", num_errors, num_warnings)



#---- internal support stuff

