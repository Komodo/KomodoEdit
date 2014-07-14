# coding=utf-8

import logging
from os.path import dirname
import sys
import unittest
from xpcom.components import interfaces as Ci
from codeintel2.common import TRG_FORM_CPLN, TRG_FORM_CALLTIP, TRG_FORM_DEFN
from codeintel2.util import dedent, unmark_text, lines_from_pos
from functools import partial
from testlib import tag

sys.path.insert(0, dirname(__file__))
try:
    from xpcom_ci_utils import _CodeIntelTestCaseBase, _BufferTestCaseBase, AsyncSpinner, UIHandler
finally:
    sys.path.remove(dirname(__file__))

log = logging.getLogger("test.codeintel.xpcom")

class ServiceTestCase(_CodeIntelTestCaseBase):
    def test_svc(self):
        """Test things directly on the codeintel service"""
        self.assertTrue(self.svc.enabled)
        self.assertTrue(self.svc.isBackEndActive)
        self.assertTrue(self.svc.is_cpln_lang("Python"),
                        "Python should support code completion")
        self.assertFalse(self.svc.is_cpln_lang("Tcl"),
                         "Tcl should not support code completion")
        langs = set(self.svc.get_cpln_langs())
        self.assertIn("CSS", langs)
        self.assertTrue(self.svc.is_citadel_lang("Perl"))
        self.assertFalse(self.svc.is_citadel_lang("Less"))
        langs = set(self.svc.get_citadel_langs())
        self.assertIn("Ruby", langs)
        # This fails for now; presumably a PyXPCOM issue?
        #self.assertIs(self.doc.ciBuf,
        #              self.svc.buf_from_koIDocument(self.doc))
        self.assertTrue(self.svc.is_xml_lang("HTML"))
        self.assertIn("HTML5", self.svc.get_xml_langs())

class PythonBufferTestCase(_BufferTestCaseBase):
    language = "Python"
    longMessage = True
    def setUp(self):
        _BufferTestCaseBase.setUp(self)
        self.doc.buffer, self.positions = unmark_text(dedent(u"""
            # Ťĥíš ƒíłé ĥáš Ůɳíčóďé ťéхť ťó ťéšť ƀýťé νš čĥář ƿóšíťíóɳš
            def silly():
                indent = 4<5>
                import <1>pprint
                pprint.pformat(<2>obj, indent<3>, width, depth)
            def other_method():
                pass<6>
            def third_method():
                pass<7>
            """).strip())

    def test_attributes(self):
        """Test various XPCOM attributes that can be obtains synchronously"""
        self.longMessage = True
        self.assertEqual(self.buf.lang, "Python", "Unexpected language")
        # Don't really care about self.buf.path
        self.assertIsNone(self.buf.project, "Unexpected project")
        self.assertEqual(set(self.buf.cpln_fillup_chars),
                         set(r"""~`!@#$%^&()-=+{}[]|\;:'",.<>?/ """),
                         "Unexpected fillup characters (actual results in first set)")
        self.assertEqual(set(self.buf.cpln_stop_chars),
                         set(r"""~`!@#$%^&*()-=+{}[]|\;:'",.<>?/ """),
                         "Unexpected stop characters (actual results in first set)")

    def test_completion(self):
        spinner = AsyncSpinner(self, callback=partial(setattr, self, "trg"))
        with spinner:
            self.buf.trg_from_pos(self.positions[1], True, spinner)
        self.assertIsNotNone(self.trg)
        self.assertEqual(self.trg.form, TRG_FORM_CPLN)
        # don't really care about the rest of the internals of the trigger
        # as long as it actually works...
        spinner = AsyncSpinner(self)
        with spinner:
            handler = UIHandler(spinner)
            self.buf.async_eval_at_trg(self.trg, handler,
                                       Ci.koICodeIntelBuffer.EVAL_SILENT)
        self.assertIn(UIHandler.AutoCompleteInfo("sys", "module"),
                      handler.completions)

    def test_calltip(self):
        spinner = AsyncSpinner(self, callback=partial(setattr, self, "trg"))
        with spinner:
            self.buf.preceding_trg_from_pos(self.positions[2],
                                            self.positions[3], spinner)
        self.assertIsNotNone(self.trg)
        self.assertEqual(self.trg.form, TRG_FORM_CALLTIP)
        spinner = AsyncSpinner(self)
        with spinner:
            handler = UIHandler(spinner)
            self.buf.async_eval_at_trg(self.trg, handler,
                                       Ci.koICodeIntelBuffer.EVAL_SILENT)
        calltip, calltip_pos = unmark_text(dedent("""
            pformat(object, <1>indent=1<2>, width=80, depth=None)
            Format a Python object into a pretty-printed representation.
            """).strip())
        self.assertEqual(handler.calltip, calltip)
        with spinner:
            positions = []
            def callback(start, end):
                positions[:] = [start, end]
            spinner.callback = callback
            self.buf.get_calltip_arg_range(self.trg.pos,
                                           calltip,
                                           self.positions[3],
                                           spinner)
        self.assertEquals(positions, [calltip_pos[1], calltip_pos[2]],
                          "Unexpected calltip range positions; should cover "
                          "second argument")

    def test_defn(self):
        spinner = AsyncSpinner(self, callback=partial(setattr, self, "trg"))
        with spinner:
            self.buf.defn_trg_from_pos(self.positions[3], spinner)
        self.assertIsNotNone(self.trg)
        self.assertEqual(self.trg.form, TRG_FORM_DEFN)
        handler = UIHandler(spinner)
        with spinner:
            spinner.callback = None
            self.buf.async_eval_at_trg(self.trg, handler,
                                       Ci.koICodeIntelBuffer.EVAL_SILENT)
        self.assertEqual(len(handler.defns), 1)
        self.assertEqual(handler.defns[0].lang, "Python")
        self.assertEqual(handler.defns[0].name, "indent")
        self.assertEqual([handler.defns[0].line],
                         lines_from_pos(self.doc.buffer, [self.positions[5]]))
        self.assertEqual(handler.defns[0].ilk, "variable")

class PerlBufferTestCase(_BufferTestCaseBase):
    language = "Perl"
    longMessage = True

    @tag("bug99676")
    def test_unicode_in_defn(self):
        self.doc.buffer, self.positions = unmark_text(dedent(u"""
            #Ůɳíčóďé<3>
            my $pCnt = 0;<1>
            # Some filler text to make sure we do not accidentally find the
            # previous definition
            $p<2>Cnt++;
            """).strip())
        self.assertGreater(self.positions[3], len("#Unicode"),
                           "Unicode positions are character positions "
                           "instead of byte positions")
        spinner = AsyncSpinner(self, callback=partial(setattr, self, "trg"))
        with spinner:
            self.buf.defn_trg_from_pos(self.positions[2], spinner)
        self.assertIsNotNone(self.trg)
        self.assertEqual(self.trg.form, TRG_FORM_DEFN)
        handler = UIHandler(spinner)
        with spinner:
            spinner.callback = None
            self.buf.async_eval_at_trg(self.trg, handler,
                                       Ci.koICodeIntelBuffer.EVAL_SILENT)
        self.assertEqual(len(handler.defns), 1)
        self.assertEqual(handler.defns[0].lang, "Perl")
        self.assertEqual(handler.defns[0].name, "$pCnt")
        self.assertEqual([handler.defns[0].line],
                         lines_from_pos(self.doc.buffer, [self.positions[1]]))
        self.assertEqual(handler.defns[0].ilk, "variable")
