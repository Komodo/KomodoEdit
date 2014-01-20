
from os.path import join
import logging

from codeintel2.util import dedent, markup_text, unmark_text, lines_from_pos

from testlib import tag
from citestsupport import writefile
import test_python

log = logging.getLogger("test.codeintel.python3")

class DefnTestCase(test_python.DefnTestCase):
    lang="Python3"

    @tag("bug101868", "pep3107")
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

    @tag("pep3102")
    def test_kw_only_args(self):
        content, positions = unmark_text(dedent("""
                def func(*, kw):
                    return "string"
                func().<1>s
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "strip")])

    @tag("knownfailure", "pep3104")
    def test_nonlocal(self):
        content, positions = unmark_text(dedent("""
                global_var = "string"
                def func():
                    nonlocal global_var
                    global_var = global_var
                    return global_var
                func().<1>s
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "strip")])

    @tag("knownfailure", "pep3132")
    def test_iterable_unpacking(self):
        content, positions = unmark_text(dedent("""
                (a, *rest, b) = [1, 2, 3, 4]
                rest.<1>i
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "insert")])

    @tag("knownfailure")
    def test_byte_literals(self):
        content, positions = unmark_text(dedent("""
                literal = b"hello"
                literal.<1>d
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "decode")])
        self.assertCompletionsDoNotInclude(markup_text(content, positions[1]),
                                           [("function", "encode")])

    def test_string_literals(self):
        content, positions = unmark_text(dedent("""
                literal = "hello"
                literal.<1>e
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "encode")])
        self.assertCompletionsDoNotInclude(markup_text(content, positions[1]),
                                           [("function", "decode")])

    def test_ellipsis_literal(self):
        content, positions = unmark_text(dedent("""
                var = ...
                "string".<1>e
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "encode")])

    @tag("bug89096", "knownfailure")
    def test_open(self):
        content, positions = unmark_text(dedent("""
                f = open("/dev/null", "w")
                f.<1>w
            """))
        self.assertCompletionsInclude(markup_text(content, positions[1]),
                                      [("function", "write")])
