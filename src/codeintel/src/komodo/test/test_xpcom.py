"""
Test case for XPCOM code completions
"""

import logging
from os.path import dirname
import sys
import unittest
from xpcom.components import interfaces as Ci
from codeintel2.common import TRG_FORM_CPLN, TRG_FORM_CALLTIP, TRG_FORM_DEFN
from codeintel2.util import dedent, indent, unmark_text, lines_from_pos, markup_text
from functools import partial
from testlib import tag


sys.path.insert(0, dirname(__file__))
try:
    from xpcom_ci_utils import _CodeIntelTestCaseBase, _BufferTestCaseBase, AsyncSpinner, UIHandler
finally:
    sys.path.remove(dirname(__file__))

log = logging.getLogger("test.codeintel.xpcom")

class JavaScriptXPCOMTestCase(_BufferTestCaseBase):
    language = "JavaScript"
    longMessage = True

    def setUp(self):
        _BufferTestCaseBase.setUp(self)
        # Must make sure the temporary document has the XPCOM catalog selected
        # so we will actually use the right completions.
        self.doc.prefs.setStringPref("codeintel_selected_catalogs", '["xpcom"]')

    def assertCompletionsInclude(self, markedup_content, completions,
                                 implicit=True):
        """Check that the given completions are found
        @param markedup_content Content with a <|> marking
        @param completions List of expected completions; each item is a tuple of
            (type, completion string)
        @param implicit Whether the trigger should be implicit
        """
        actual_completions = self._doEval(markedup_content,
                                          implicit=implicit).completions
        missing_completions = set()
        for typ, cpln in completions:
            if UIHandler.AutoCompleteInfo(cpln, typ) not in actual_completions:
                missing_completions.add((typ, cpln))
        self.failIf(missing_completions and True,
            "%s completions at the given position did not "
            "include all expected values\n"
            "  missing:         %r\n"
            "  expected all of: %r\n"
            "  got:             %r\n"
            "  buffer:\n%s"
            % (self.language, list(missing_completions), completions,
               [(cpln.type, cpln.completion) for cpln in actual_completions],
               indent(markedup_content)))

    def assertCompletionsDoNotInclude(self, markedup_content, completions,
                                      implicit=True):
        """Check that the given completions are NOT found
        @param markedup_content Content with a <|> marking
        @param completions List of expected completions; each item is a tuple of
            (type, completion string)
        @param implicit Whether the trigger should be implicit
        """
        actual_completions = self._doEval(markedup_content,
                                          implicit=implicit).completions
        extra_completions = set()
        for typ, cpln in completions:
            if UIHandler.AutoCompleteInfo(cpln, typ) in actual_completions:
                extra_completions.add((typ, cpln))
        self.failIf(extra_completions and True,
            "%s completions at the given position included "
            "some unexpected values\n"
            "  shouldn't have had these: %r\n"
            "  expected none of:         %r\n"
            "  got:                      %r\n"
            "  buffer:\n%s"
            % (self.language, list(extra_completions), completions,
               [(cpln.type, cpln.completion) for cpln in actual_completions],
               indent(markedup_content)))

    def assertCalltipIs(self, markedup_content, calltip, implicit=True):
        """Check that the calltip is as expected
        @param markedup_content Content with a <|> marking
        @param calltip The calltip string
        @param implicit Whether the trigger should be implicit
        """
        handler = self._doEval(markedup_content, implicit=implicit)
        actual_calltip = getattr(handler, "calltip", None)
        self.assertEqual(calltip, actual_calltip,
            "unexpected calltip at the given position\n"
            "  expected:\n%s\n"
            "  got:\n%s\n"
            "  buffer:\n%s"
            % (indent(calltip if calltip else "(none)"),
               indent(actual_calltip if actual_calltip else "(none)"),
               indent(markedup_content)))

    def _doEval(self, markedup_content, lang=None, implicit=True):
        self.doc.buffer, self.positions = unmark_text(dedent(markedup_content).strip())
        spinner = AsyncSpinner(self, callback=partial(setattr, self, "trg"))
        with spinner:
            self.buf.trg_from_pos(self.positions["pos"], implicit, spinner)
        self.assertIsNotNone(self.trg)
        # don't really care about the rest of the internals of the trigger
        # as long as it actually works...
        spinner = AsyncSpinner(self)
        with spinner:
            handler = UIHandler(spinner)
            self.buf.async_eval_at_trg(self.trg, handler,
                                       Ci.koICodeIntelBuffer.EVAL_SILENT)
        return handler

    def test_xpcom_cplns(self):
        content, positions = unmark_text(dedent("""\
            var observerSvc = Components.<1>classes["@mozilla.org/observer-service;1"].<2>
                           getService(Components.interfaces.<3>nsIObserverService);
            observerSvc.<4>;
            observerSvc.addObserver(<5>);
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("namespace", "classes"),
             ("namespace", "interfaces")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "createInstance"),
             ("function", "getService")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[3]),
            [("class", "nsIObserverService"),
             ("class", "nsIFile")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[4]),
            [("function", "addObserver"),
             ("function", "notifyObservers")])
        self.assertCalltipIs(markup_text(content, pos=positions[5]),
                             "addObserver(in nsIObserver, in String, in Boolean)")

    def test_xpcom_returns(self):
        content, positions = unmark_text(dedent("""\
            var url = Components.classes["@mozilla.org/network/standard-url;1"]
                                .createInstance(Components.interfaces.nsIURL);
            var uri = url.<1>clone();
            uri.<2>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "spec"),
             ("variable", "scheme"),
             ("function", "clone"),
             ("variable", "query"),
             ("function", "getCommonBaseSpec")])
        # clone should return a nsIURI object
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "spec"),
             ("variable", "scheme"),
             ("function", "clone")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[2]),
            [("variable", "query"),
             ("function", "getCommonBaseSpec")])

    def test_query_interface(self):
        content, positions = unmark_text(dedent("""\
            var aFile = Components.classes["@mozilla.org/file/local;1"].createInstance();
            if (aFile) {
                var qiFile = aFile.QueryInterface(Components.interfaces.nsIFile);
                // Should now know that this supports nsIFile
                qiFile.<1>;
            }
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "followLinks"),
             ("variable", "path"),
             ("function", "clone"),
             ("function", "exists"),
             ("function", "initWithPath")])

    @tag("knownfailure")
    def test_query_interface_2(self):
        content, positions = unmark_text(dedent("""\
            var aFile = Components.classes["@mozilla.org/file/local;1"].createInstance();
            if (aFile) {
                aFile.QueryInterface(Components.interfaces.nsIFile);
                // Should now know that this supports nsIFile
                aFile.<1>;
            }
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "followLinks"),
             ("variable", "path"),
             ("function", "clone"),
             ("function", "exists"),
             ("function", "initWithPath")])

    def test_xpcom_classes_array_cplns(self):
        content, positions = unmark_text(dedent("""\
            var observerCls = Components.classes["<1>@mozilla.org/observer-service;1"];
            observerCls.<2>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "@mozilla.org/observer-service;1"),
             ("variable", "@mozilla.org/embedcomp/prompt-service;1")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("function", "getService"),
             ("function", "createInstance")])

    def test_xpcom_full_expression_cplns_bug80581(self):
        content, positions = unmark_text(dedent("""\
            var ko_prefSvc = Components.classes["@activestate.com/koPrefService;1"]
                           .getService(Components.interfaces.koIPrefService);
            ko_prefSvc.<1>;
            var ko_gPrefs = Components.classes["@activestate.com/koPrefService;1"]
                           .getService(Components.interfaces.koIPrefService)
                           .prefs;
            ko_gPrefs.<2>;
        """))
        self.assertCompletionsInclude(markup_text(content, pos=positions[1]),
            [("variable", "prefs"),
             ("function", "saveState")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[1]),
            [("variable", "type"),
             ("function", "serialize")])
        self.assertCompletionsInclude(markup_text(content, pos=positions[2]),
            [("variable", "type"),
             ("function", "serialize")])
        self.assertCompletionsDoNotInclude(markup_text(content, pos=positions[2]),
            [("variable", "prefs"),
             ("function", "saveState")])
