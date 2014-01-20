
from os.path import join
import logging

from codeintel2.util import dedent, markup_text, unmark_text, lines_from_pos

from testlib import tag
from citestsupport import writefile
import test_python

log = logging.getLogger("test.codeintel.python3")

class DefnTestCase(test_python.DefnTestCase):
    lang="Python3"

    @tag("bug101868")
    def test_def_decl_trailing_comma(self):
        """Test having a trailing comma in a function definition; this needs to
        be invalid in Python 2 but valid in Python 3."""
        test_dir = join(self.test_dir, "def_decl_trailing_comma")
        content, pos = unmark_text(dedent("""\
            def foo<1>(arg:int,):
                arg<2>
        """))
        path = join(test_dir, "def_decl_trailing_comma.py")
        writefile(path, content)
        buf = self.mgr.buf_from_path(path, lang=self.lang)
        lines = lines_from_pos(content, pos)
        self.assertDefnMatches2(buf, pos[2], line=lines[1],
                                ilk="argument", name="arg", path=path)

class PythonDocTestCase(test_python.PythonDocTestCase):
    lang = "Python3"

class TrgTestCase(test_python.TrgTestCase):
    lang = "Python3"

class CplnTestCase(test_python.CplnTestCase):
    lang = "Python3"

    @tag("bug101782")
    def test_decl_default_arg_call(self):
        content, positions = unmark_text(dedent("""
            def foo(arg=int()):
                return "answer"
            foo().<1>strip
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "strip")])
        content, positions = unmark_text(dedent("""
            def foo(arg=thing[3]):
                return "answer"
            foo().<1>strip
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "strip")])
