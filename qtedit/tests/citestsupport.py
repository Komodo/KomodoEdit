"""Support for the codeintel3 test modules -- Python 3 port of
src/codeintel/test2/citestsupport.py, targeting codeintel3 (qtedit's
from-scratch Python-3 port of codeintel2) instead of the legacy codeintel2.

Ported mechanically, not redesigned: citestsupport.py drives codeintel2
entirely in-process (Manager/CitadelBuffer/EvalController/util calls, not
the OOP wire protocol qtedit's real UI uses), and codeintel3's equivalents
turned out to have near-identical method names/signatures at the same
lines as the codeintel2 originals -- confirmed by direct comparison before
starting this port, not assumed. What changed relative to the original:

- XPCOM init branch and init_xml_catalogs()/koXMLDatasetInfo call dropped
  entirely (dead/irrelevant outside Komodo and for XML linting, which no
  test here exercises).
- `unicode` -> `str`; deprecated unittest aliases (failIf/failUnless/
  failUnlessEqual/assertNotEquals) -> their modern equivalents (removed
  from unittest as of Python 3.12, not just deprecated).
- `_get_buf_and_data`'s buffer-naming logic was genuinely buggy under a
  literal Python 3 translation: `unmark_text()` needs a `str` (its regex
  patterns are str, and it does `isinstance(text, str)` internally to
  decide byte-length accounting) but the original encoded to bytes first
  for the md5 buffer-name hash and then fed those bytes into unmark_text
  too -- harmless under Python 2 (str upmulti-hatted as bytes) but a
  `TypeError` under Python 3. Fixed to keep the md5 hashing on encoded
  bytes but pass the original `str` through to unmark_text/adjust_content.
- `override_encoding` (a `sys.setdefaultencoding()`-based decorator) is
  dropped outright rather than ported: that hook doesn't exist in Python 3
  at all (there is no mutable global default string encoding anymore,
  since all `str` is already Unicode) -- not an unported detail, an
  inapplicable one. Unused by test_python.py.
"""
import json
import os
import random
import re
from glob import glob
from hashlib import md5
from os.path import abspath, dirname, exists, join
from pprint import pformat
import unittest

from codeintel3.manager import Manager
from codeintel3.util import indent, markup_text, unmark_text
from codeintel3.citadel import CitadelBuffer
from codeintel3.common import *
from codeintel3.environment import SimplePrefsEnvironment


#---- globals

test_db_base_dir = join(dirname(abspath(__file__)), "tmp-db-base-dir")


#---- test support class (CodeIntelTestCase) and other support stuff

class _CaptureEvalController(EvalController):
    log = None

    def _log(self, lvl, msg, *args):
        if self.log is None:
            self.log = []
        self.log.append((lvl, msg % args))

    def debug(self, msg, *args): self._log("debug", msg, *args)
    def info(self, msg, *args): self._log("info", msg, *args)
    def warn(self, msg, *args): self._log("warn", msg, *args)
    def error(self, msg, *args): self._log("error", msg, *args)


class CodeIntelTestCase(unittest.TestCase):
    # Subclasses can override this to have setUp pass these settings to the
    # codeintel Manager.
    _ci_db_base_dir_ = None
    _ci_db_catalog_dirs_ = []
    _ci_db_import_everything_langs = None
    _ci_env_prefs_ = None
    # A test case can set this to false to have the setUp/tearDown *not*
    # create a `self.mgr'.
    _ci_test_setup_mgr_ = True
    _ci_extra_module_dirs_ = None

    def ci_setUpClass(cls):
        if cls._ci_test_setup_mgr_:
            env = None
            if cls._ci_env_prefs_ is not None:
                env = SimplePrefsEnvironment(**cls._ci_env_prefs_)

            def get_extra_module_dirs():
                spec = join(dirname(__file__), "..", "..", "udl", "skel", "*", "pylib")
                for d in glob(spec):
                    if glob(join(spec, "lang_*.py")):
                        yield d
                for d in cls._ci_extra_module_dirs_ or []:
                    yield d

            cls.mgr = Manager(
                extra_module_dirs=get_extra_module_dirs(),
                db_base_dir=cls._ci_db_base_dir_ or test_db_base_dir,
                db_catalog_dirs=cls._ci_db_catalog_dirs_,
                db_import_everything_langs=cls._ci_db_import_everything_langs,
                env=env)
            cls.mgr.upgrade()
            cls.mgr.initialize()

    def ci_tearDownClass(cls):
        if cls._ci_test_setup_mgr_:
            cls.mgr.finalize()
            cls.mgr = None

    setUpClass = classmethod(ci_setUpClass)
    tearDownClass = classmethod(ci_tearDownClass)

    def adjust_content(self, content):
        """A hook for subclasses to modify markedup_content before use in
        test cases. This is useful for sharing test cases between pure-
        and multi-lang uses of a given lang.
        """
        return content

    def adjust_pos(self, pos):
        """An accompanying hook for `adjust_content' to adjust trigger
        pos values accordingly.
        """
        return pos

    def _get_buf_and_data(self, markedup_content, lang, path=None, env=None):
        encoding = None
        if path is None:
            # Try to ensure no accidental re-use of the same buffer name
            # across the whole test suite. Also try to keep the buffer
            # names relatively short (keeps tracebacks cleaner).
            markedup_bytes = markedup_content.encode("utf-8")
            encoding = "utf-8"
            name = "buf-" + md5(markedup_bytes).hexdigest()[:16]
            path = os.path.join("<Unsaved>", name)
        content, data = unmark_text(self.adjust_content(markedup_content))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path,
                                        env=env, encoding=encoding)
        return buf, data

    def _get_buf_and_trg(self, markedup_content, lang, path=None,
                         implicit=True, env=None):
        buf, data = self._get_buf_and_data(markedup_content, lang, path, env)
        trg = buf.trg_from_pos(data["pos"], implicit=implicit)
        if trg is not None:
            # We want to make sure that triggers are serializable (for oop);
            # there doesn't seem to be more reasonable places for it.
            # We don't actually care what the serialization is, though
            try:
                json.dumps(trg.to_dict())
            except Exception:
                self.fail("Trigger could not be serialized")
        return buf, trg

    def assertCITDLExprUnderPosIs(self, markedup_content, citdl_expr, lang=None,
                          prefix_filter=None, implicit=True, trigger_name=None,
                          **fields):
        """Assert that the CITDL expression at the current position
        is as expected.

        This uses langintel.citdl_expr_from_trg() -- or, for Perl,
        langintel.citdl_expr_and_prefix_filter_from_trg().

        The "prefix_filter" optional argument can be used for Perl to test
        the value its relevant function returns.
        """
        if lang is None:
            lang = self.lang
        content, data = unmark_text(self.adjust_content(markedup_content))
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        langintel = self.mgr.langintel_from_lang(lang)
        if trigger_name is None:
            trigger_name = "fakey-completion-type"

        if lang == "Perl":
            trg = Trigger(lang, TRG_FORM_DEFN, trigger_name,
                          data["pos"], implicit=implicit, length=0,
                          **fields)
            actual_citdl_expr, actual_prefix_filter \
                = langintel.citdl_expr_and_prefix_filter_from_trg(buf, trg)
        else:
            trg = Trigger(lang, TRG_FORM_DEFN, trigger_name,
                          data["pos"], implicit=implicit,
                          **fields)
            actual_citdl_expr = langintel.citdl_expr_from_trg(buf, trg)
        self.assertEqual(actual_citdl_expr, citdl_expr,
                         "unexpected actual %s CITDL expr under pos:\n"
                         "  expected: %r\n"
                         "  got:      %r\n"
                         "  buffer:\n%s"
                         % (lang, citdl_expr, actual_citdl_expr,
                            indent(markedup_content)))
        if prefix_filter is not None:
            self.fail("prefix_filter comparison not implemented")  # TODO, matches legacy `XXX`

    def _assertDefnMatches(self, buf, pos, lang=None, **fields):
        ctlr = _CaptureEvalController()
        trg = buf.defn_trg_from_pos(pos)
        defns = buf.defns_from_trg(trg, ctlr=ctlr)
        if not defns:
            self.fail("unexpectedly did not find a definition in %r at pos %d\n"
                "  eval log\n%s\n"
                "  buffer:\n%s"
                % (buf, pos,
                   indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
                   indent(buf.accessor.text)))
        if "pos" in fields:
            fields["pos"] = self.adjust_pos(fields["pos"])
        defn = defns[0]
        for name, value in fields.items():
            try:
                actual_value = getattr(defn, name)
            except AttributeError:
                actual_value = None
            self.assertEqual(actual_value, value,
                "%s definition, unexpected value for field %r\n"
                "  defn:     %r\n"
                "  expected: %r\n"
                "  got:      %r\n"
                "  eval log\n%s\n"
                "  buffer:\n%s"
                % (buf.lang, name, defn, value, actual_value,
                   indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
                   indent(buf.accessor.text)))

    def assertDefnMatches(self, markedup_content, lang=None, **fields):
        if lang is None:
            lang = self.lang
        buf, data = self._get_buf_and_data(markedup_content, lang)
        self._assertDefnMatches(buf, data["pos"], lang, **fields)

    def assertDefnMatches2(self, buf, pos, lang=None, **fields):
        self._assertDefnMatches(buf, pos, lang, **fields)

    def assertDefnIncludes(self, buf, pos, lang=None, **fields):
        """Check that a definition is found within one of the results for a
        given position.
        Note that this is not very useful; we normally only use the first
        definition. It can however be used to ensure we don't regress things
        before they get fixed correctly.
        """
        ctlr = _CaptureEvalController()
        trg = buf.defn_trg_from_pos(pos)
        defns = buf.defns_from_trg(trg, ctlr=ctlr)
        if not defns:
            self.fail("unexpectedly did not find a definition in %r at pos %d\n"
                "  eval log\n%s\n"
                "  buffer:\n%s"
                % (buf, pos,
                   indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
                   indent(buf.accessor.text)))
        if "pos" in fields:
            fields["pos"] = self.adjust_pos(fields["pos"])

        filtered_defns = []
        for defn in defns:
            filtered_defn = dict((key, getattr(defn, key, None))
                                 for key in fields.keys())
            filtered_defns.append(filtered_defn)
        self.assertIn(fields, filtered_defns)

    def assertNoDuplicateDefns(self, markedup_content, lang=None):
        if lang is None:
            lang = self.lang
        buf, data = self._get_buf_and_data(markedup_content, lang)
        self.assertNoDuplicateDefns2(buf, data["pos"])

    def assertNoDuplicateDefns2(self, buf, pos):
        markedup_content = markup_text(buf.accessor.text, pos=pos)
        ctlr = _CaptureEvalController()
        trg = buf.defn_trg_from_pos(pos)
        actual_defns = buf.defns_from_trg(trg, ctlr=ctlr)
        if not actual_defns:
            self.fail("%s trigger resulted in no definitions when expecting "
                      "to check for duplicate definitions:\n%s"
                      % (buf.lang, indent(markedup_content)))

        count_from_defn_repr = {}
        for defn_repr in (repr(d) for d in actual_defns):
            count_from_defn_repr[defn_repr] = count_from_defn_repr.get(defn_repr, 0) + 1
        defn_dupes = [(count, defn_repr)
                      for defn_repr, count in count_from_defn_repr.items()
                      if count > 1]
        self.assertFalse(defn_dupes,
            "unexpectedly got duplicate completions at the given position\n"
            "  duplicates:\n%s\n"
            "  eval log\n%s\n"
            "  buffer:\n%s"
            % (indent('\n'.join('%d of %s' % d for d in defn_dupes)),
               indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
               indent(markedup_content)))

    def assertTriggerMatches(self, markedup_content, lang=None,
                             implicit=True, env=None, **fields):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        if trg is None:
            self.fail("unexpectedly did not find a %s trigger, buffer:\n%s"
                      % (lang, indent(markedup_content)))
        if "pos" in fields:
            fields["pos"] = self.adjust_pos(fields["pos"])
        for name, value in fields.items():
            try:
                actual_value = getattr(trg, name)
            except AttributeError:
                actual_value = trg.extra[name]
            self.assertEqual(actual_value, value,
                "unexpected %s trigger '%s' value: expected %r, "
                "got %r, buffer:\n%s"
                % (lang, name, value, actual_value,
                   indent(markedup_content)))

    def assertTriggerDoesNotMatch(self, markedup_content, lang=None,
                                  implicit=True, env=None, **fields):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        if trg is None:
            return  # no trigger is as good as
        if "pos" in fields:
            fields["pos"] = self.adjust_pos(fields["pos"])
        for name, value in fields.items():
            try:
                actual_value = getattr(trg, name)
            except AttributeError:
                actual_value = trg.extra[name]
            self.assertNotEqual(actual_value, value,
                "unexpected %s trigger '%s' value: expected not %r, "
                "got %r, buffer:\n%s"
                % (lang, name, value, actual_value,
                   indent(markedup_content)))

    def assertNoTrigger(self, markedup_content, lang=None, implicit=True,
                        env=None):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        if trg is not None:
            self.fail("unexpectedly found a %s trigger %r when didn't expect "
                      "one, buffer:\n%s"
                      % (lang, trg, indent(markedup_content)))

    def assertPrecedingTriggerMatches(self, markedup_content, lang=None,
                                      **fields):
        if lang is None:
            lang = self.lang
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        content, data = unmark_text(self.adjust_content(markedup_content))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        trg = buf.preceding_trg_from_pos(data["start_pos"], data["pos"])
        if trg is None:
            self.fail("unexpectedly did not find a preceding %s trigger, "
                      "buffer:\n%s" % (lang, indent(markedup_content)))
        if "pos" in fields:
            fields["pos"] = self.adjust_pos(fields["pos"])
        for name, value in fields.items():
            actual_value = getattr(trg, name)
            self.assertEqual(actual_value, value,
                "unexpected preceding %s trigger '%s' value: expected %r, "
                "got %r, buffer:\n%s"
                % (lang, name, value, actual_value,
                   indent(markedup_content)))

    def assertNoPrecedingTrigger(self, markedup_content, lang=None):
        if lang is None:
            lang = self.lang
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        content, data = unmark_text(self.adjust_content(markedup_content))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        trg = buf.preceding_trg_from_pos(data["start_pos"], data["pos"])
        if trg is not None:
            self.fail("unexpectedly found a preceding %s trigger '%s' when "
                      "didn't expect one, buffer:\n%s"
                      % (lang, trg.name, indent(markedup_content)))

    def assertScopeLpathIs(self, markedup_content, lpath, lang=None):
        if lang is None:
            lang = self.lang
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        content, data = unmark_text(self.adjust_content(markedup_content))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        buf.scan(skip_scan_time_check=True)
        actual_blob, actual_lpath = buf.scoperef_from_pos(data["pos"])
        self.assertEqual(lpath, actual_lpath,
            "unexpected %s scope lookup path (lpath) at the given position\n"
            "  expected: %r\n"
            "  got:      %r\n"
            "  buffer:\n%s"
            % (self.lang, lpath, actual_lpath, indent(markedup_content)))

    def assertCompletionsAre2(self, buf, pos, completions, lang=None, implicit=True, env=None):
        if lang is None:
            lang = self.lang
        markedup_content = markup_text(buf.accessor.text, pos=pos)
        trg = buf.trg_from_pos(pos, implicit=implicit)
        self._assertCompletionsAre(markedup_content, buf, trg, completions, lang, implicit)

    def assertCompletionsAre(self, markedup_content, completions,
                             lang=None, implicit=True, env=None):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        self._assertCompletionsAre(markedup_content, buf, trg, completions, lang, implicit)

    def _assertCompletionsAre(self, markedup_content, buf, trg, completions,
                             lang, implicit):
        if trg is None:
            self.fail("given position is not a %s trigger point, "
                      "expected completions to be %r:\n%s"
                      % (lang, completions, indent(markedup_content)))
        if isinstance(buf, CitadelBuffer):
            buf.unload()  # remove any entry from CIDB to ensure clean test
        ctlr = _CaptureEvalController()
        actual_completions = buf.cplns_from_trg(trg, ctlr=ctlr)
        self.assertEqual(completions, actual_completions,
            "unexpected %s completions at the given position\n"
            "  expected: %r\n"
            "  got:      %r\n"
            "  extra:    %r\n"
            "  missing:  %r\n"
            "  eval log\n%s\n"
            "  buffer:\n%s"
            % (lang, completions,
               actual_completions,
               list(set(actual_completions or []).difference(completions or [])),
               list(set(completions or []).difference(actual_completions or [])),
               indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
               indent(markedup_content)))

    def assertNoDuplicateCompletions(self, markedup_content, lang=None,
                                     implicit=True, env=None):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        if trg is None:
            self.fail("given position is not a %s trigger point, "
                      "expected there to be completions:\n%s"
                      % (lang, indent(markedup_content)))

        if isinstance(buf, CitadelBuffer):
            buf.unload()
        ctlr = _CaptureEvalController()
        actual_completions = buf.cplns_from_trg(trg, ctlr=ctlr)
        if actual_completions is None:
            self.fail("%s trigger resulted in no completions when expecting "
                      "to check for duplicate completions:\n%s"
                      % (lang, indent(markedup_content)))

        count_from_cpln = {}
        for cpln in actual_completions:
            count_from_cpln[cpln] = count_from_cpln.get(cpln, 0) + 1
        cpln_dupes = [(count, cpln) for cpln, count in count_from_cpln.items()
                      if count > 1]
        self.assertFalse(cpln_dupes,
            "unexpectedly got duplicate completions at the given position\n"
            "  duplicates:\n%s\n"
            "  eval log\n%s\n"
            "  buffer:\n%s"
            % (indent('\n'.join('%d of %r' % d for d in cpln_dupes)),
               indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
               indent(markedup_content)))

    def _assertCompletionsInclude(self, buf, trg, completions, unload=True):
        markedup_content = markup_text(buf.accessor.text, pos=trg.pos)
        if unload and isinstance(buf, CitadelBuffer):
            buf.unload()
        ctlr = _CaptureEvalController()
        actual_completions = buf.cplns_from_trg(trg, ctlr=ctlr)
        missing_completions = [c for c in completions
                               if c not in (actual_completions or [])]
        self.assertFalse(missing_completions,
            "%s completions at the given position did not "
            "include all expected values\n"
            "  missing:         %r\n"
            "  expected all of: %r\n"
            "  got:             %r\n"
            "  eval log:\n%s\n"
            "  buffer:\n%s"
            % (buf.lang, missing_completions, completions,
               actual_completions,
               indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
               indent(markedup_content)))

    def assertCompletionsInclude(self, markedup_content, completions,
                                 lang=None, implicit=True, env=None):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        if trg is None:
            self.fail("given position is not a %s trigger point, "
                      "expected completions to include %r:\n%s"
                      % (lang, completions, indent(markedup_content)))
        self._assertCompletionsInclude(buf, trg, completions)

    def assertCompletionsInclude2(self, buf, pos, completions, implicit=True,
                                  unload=True):
        """A version of assertCompletionsInclude() where you pass in
        a Buffer instance instead of marked up content. Sometimes
        this is more convenient.
        """
        trg = buf.trg_from_pos(pos, implicit=implicit)
        if trg is None:
            markedup_content = markup_text(buf.accessor.text, pos=pos)
            self.fail("given position is not a %s trigger point, "
                      "expected completions to include %r:\n%s"
                      % (buf.lang, completions, indent(markedup_content)))
        self._assertCompletionsInclude(buf, trg, completions, unload=unload)

    def _assertCompletionsDoNotInclude(self, buf, trg, completions, unload=True):
        markedup_content = markup_text(buf.accessor.text, pos=trg.pos)
        if unload and isinstance(buf, CitadelBuffer):
            buf.unload()
        ctlr = _CaptureEvalController()
        actual_completions = buf.cplns_from_trg(trg, ctlr=ctlr)
        completions_that_shouldnt_be_there = [
            c for c in (actual_completions or []) if c in completions
        ]
        self.assertFalse(completions_that_shouldnt_be_there,
            "%s completions at the given position included "
            "some unexpected values\n"
            "  shouldn't have had these: %r\n"
            "  expected none of:         %r\n"
            "  got:                      %r\n"
            "  eval log:\n%s\n"
            "  buffer:\n%s"
            % (buf.lang, completions_that_shouldnt_be_there, completions,
               actual_completions,
               indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
               indent(markedup_content)))

    def assertCompletionsDoNotInclude(self, markedup_content, completions,
                                      lang=None, implicit=True, env=None):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        if trg is None:
            self.fail("given position is not a %s trigger point, "
                      "expected completions to exclude %r:\n%s"
                      % (lang, completions, indent(markedup_content)))
        self._assertCompletionsDoNotInclude(buf, trg, completions)

    def assertCompletionsDoNotInclude2(self, buf, pos, completions,
                                       implicit=True, unload=True):
        """A version of assertCompletionsDoNotInclude() where you pass in
        a Buffer instance instead of marked up content. Sometimes
        this is more convenient.
        """
        trg = buf.trg_from_pos(pos, implicit=implicit)
        if trg is None:
            markedup_content = markup_text(buf.accessor.text, pos=pos)
            self.fail("given position is not a %s trigger point, "
                      "expected completions to exclude %r:\n%s"
                      % (buf.lang, completions, indent(markedup_content)))
        self._assertCompletionsDoNotInclude(buf, trg, completions, unload=unload)

    def assertCalltipIs2(self, buf, pos, calltip, implicit=True):
        """A variant of assertCalltipIs() where you pass in
        a Buffer instance instead of marked up content. Sometimes
        this is more convenient.
        """
        trg = buf.trg_from_pos(pos, implicit=implicit)
        markedup_content = markup_text(buf.accessor.text, pos=trg.pos)
        self._assertCalltipIs(buf, trg, markedup_content, calltip, self.lang)

    def assertCalltipIs(self, markedup_content, calltip, lang=None,
                        implicit=True, env=None):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        self._assertCalltipIs(buf, trg, markedup_content, calltip, lang)

    def _assertCalltipIs(self, buf, trg, markedup_content, calltip, lang):
        if trg is None:
            self.fail("given position is not a %s trigger point, "
                      "expected the following calltip:\n"
                      "  calltip:\n%s\n"
                      "  buffer:\n%s"
                      % (lang, indent(calltip), indent(markedup_content)))

        if isinstance(buf, CitadelBuffer):
            buf.unload()
        ctlr = _CaptureEvalController()
        actual_calltips = buf.calltips_from_trg(trg, ctlr=ctlr)
        if actual_calltips and actual_calltips[0]:
            actual_calltip = actual_calltips[0]
        else:
            actual_calltip = None
        self.assertEqual(calltip, actual_calltip,
            "unexpected %s calltip at the given position\n"
            "  expected:\n%s\n"
            "  got:\n%s\n"
            "  eval log:\n%s\n"
            "  buffer:\n%s"
            % (trg.name, indent(calltip and calltip or "(none)"),
               indent(actual_calltip and actual_calltip or "(none)"),
               indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
               indent(markedup_content)))

    def assertCalltipMatches(self, markedup_content, calltip, lang=None,
                        implicit=True, env=None, flags=0):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        self._assertCalltipMatches(buf, trg, markedup_content, calltip, lang, flags)

    def _assertCalltipMatches(self, buf, trg, markedup_content, expr, lang, flags):
        if trg is None:
            self.fail("given position is not a %s trigger point, "
                      "expected the calltip to match the following:\n"
                      "  exression:\n%s\n"
                      "  buffer:\n%s"
                      % (lang, indent(expr), indent(markedup_content)))

        if isinstance(buf, CitadelBuffer):
            buf.unload()
        ctlr = _CaptureEvalController()
        actual_calltips = buf.calltips_from_trg(trg, ctlr=ctlr)
        if actual_calltips and actual_calltips[0]:
            actual_calltip = actual_calltips[0]
        else:
            actual_calltip = None
        self.assertNotEqual(re.search(expr, actual_calltip, flags), None,
            "unexpected %s calltip at the given position\n"
            "  expression:\n%s\n"
            "  got:\n%s\n"
            "  eval log:\n%s\n"
            "  buffer:\n%s"
            % (trg.name, indent(expr and expr or "(none)"),
               indent(actual_calltip and actual_calltip or "(none)"),
               indent('\n'.join('%5s: %s' % (lvl, m) for lvl, m in ctlr.log)),
               indent(markedup_content)))

    def assertCurrCalltipArgRange(self, markedup_content, calltip,
                                  expected_range, lang=None, implicit=True):
        if lang is None:
            lang = self.lang
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        content, data = unmark_text(self.adjust_content(markedup_content))
        pos = data["pos"]
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        trg = buf.trg_from_pos(data["trg_pos"], implicit=implicit)
        actual_range = buf.curr_calltip_arg_range(trg.pos, calltip, curr_pos=data["pos"])
        self.assertEqual(actual_range, expected_range,
            "unexpected current calltip arg range\n"
            "   expected: %s\n"
            "   got:      %s\n"
            "   calltip:\n%s\n"
            "   buffer:\n%s"
            % (expected_range, actual_range, indent(calltip), indent(markedup_content)))

    def assertEvalError(self, markedup_content, log_pattern, lang=None,
                        implicit=True, env=None):
        if lang is None:
            lang = self.lang

        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        if trg is None:
            self.fail("given position is not a %s trigger point, "
                      "no completion can be done to see if errors"
                      % self.lang)
        if isinstance(buf, CitadelBuffer):
            buf.unload()

        class TestEvalController(EvalController):
            """A completion controller that captures all eval logging."""
            def __init__(self):
                EvalController.__init__(self)
                self.log = []
            def debug(self, msg, *args):
                self.log.append(("debug", msg % args))
            def info(self, msg, *args):
                self.log.append(("info", msg % args))
            def warn(self, msg, *args):
                self.log.append(("warn", msg % args))
            def error(self, msg, *args):
                self.log.append(("error", msg % args))

        ctlr = TestEvalController()
        buf.async_eval_at_trg(trg, ctlr=ctlr)
        ctlr.wait()
        if not ctlr.is_done():
            self.fail("evaluation is not 'done': didn't expect that")
        if trg.form == TRG_FORM_CPLN and ctlr.cplns:
            self.fail("evalution had results: didn't expect that: %r" % ctlr.cplns)
        elif trg.form == TRG_FORM_CALLTIP and ctlr.calltips:
            self.fail("evalution had results: didn't expect that: %r" % ctlr.cplns)
        if log_pattern:
            matching_logs = [(level, msg) for level, msg in ctlr.log
                             if log_pattern.search(msg)]
            self.assertTrue(matching_logs,
                "the given completion failed but no logs matched the given pattern:\n"
                "  log_pattern: /%s/\n"
                "  log messages:\n%s\n"
                "  buffer:\n%s"
                % (log_pattern.pattern,
                   indent('\n'.join(['%s: %s' % lg for lg in ctlr.log])),
                   indent(markedup_content)))

    def assertCITDLExprIs(self, markedup_content, citdl_expr, lang=None,
                          prefix_filter=None, implicit=True, trigger_name=None,
                          **fields):
        """Assert that the preceding CITDL expression at the current position
        is as expected.

        This uses buf.citdl_expr_from_trg() -- or, for Perl,
        buf.citdl_expr_and_prefix_filter_from_trg().

        The "prefix_filter" optional argument can be used for Perl to test
        the value its relevant function returns.
        """
        if lang is None:
            lang = self.lang
        content, data = unmark_text(self.adjust_content(markedup_content))
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        langintel = self.mgr.langintel_from_lang(lang)
        if trigger_name is None:
            trigger_name = "fakey-completion-type"

        if lang == "Perl":
            if content[data["pos"] - 1] in ('>', ':'):
                length = 2
            else:
                length = 1
            trg = Trigger(lang, TRG_FORM_CPLN, trigger_name,
                          data["pos"], implicit=implicit, length=length,
                          **fields)
            actual_citdl_expr, actual_prefix_filter \
                = langintel.citdl_expr_and_prefix_filter_from_trg(buf, trg)
        else:
            trg = Trigger(lang, TRG_FORM_CPLN, trigger_name,
                          data["pos"], implicit=implicit,
                          **fields)
            actual_citdl_expr = langintel.citdl_expr_from_trg(buf, trg)
        self.assertEqual(actual_citdl_expr, citdl_expr,
                         "unexpected actual %s CITDL expr preceding trigger:\n"
                         "  expected: %r\n"
                         "  got:      %r\n"
                         "  buffer:\n%s"
                         % (lang, citdl_expr, actual_citdl_expr,
                            indent(markedup_content)))
        if lang == "Perl" and prefix_filter is not None:
            self.assertEqual(actual_prefix_filter, prefix_filter,
                             "unexpected actual %s variable prefix filter "
                             "preceding trigger:\n"
                             "  expected: %r\n"
                             "  got:      %r\n"
                             "  buffer:\n%s"
                             % (lang, prefix_filter, actual_prefix_filter,
                                indent(markedup_content)))

    def _unmark_lex_text(self, markedup_text):
        from SilverCity import ScintillaConstants
        tokenizer = re.compile(r'(<(SCE_\w+)>(.*?)</\2>)')

        tokens = []
        text = ''
        while markedup_text:
            match = tokenizer.search(markedup_text)
            if match:
                text += markedup_text[:match.start()]
                token = {
                    'end_index': len(text) + len(match.group(3)) - 1,
                    'start_index': len(text),
                    'style': getattr(ScintillaConstants, match.group(2)),
                    'text': match.group(3),
                }
                tokens.append(token)
                text += match.group(3)
                markedup_text = markedup_text[match.end():]
            else:
                text += markedup_text
                markedup_text = ''
        return text, tokens

    def assertLex(self, markedup_content, lang=None):
        """Lex the given content and assert that the lexed tokens are as
        expected.

        What is "expected" is given via pseudo-xml markup like this:

            fuzzy wuzzy <SCE_UDL_SSL_COMMENTBLOCK>wuzza</SCE_UDL_SSL_COMMENTBLOCK> bear

        This example expects that "wuzza" will be a token with style
        SCE_UDL_SSL_COMMENTBLOCK.
        """
        from codeintel3.accessor import SilverCityAccessor
        if lang is None:
            lang = self.lang

        content, tokens = self._unmark_lex_text(markedup_content)

        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        assert isinstance(buf.accessor, SilverCityAccessor)
        actual_tokens = buf.accessor.tokens  # cheating
        for actual_token in actual_tokens:
            del actual_token["end_column"]
            del actual_token["end_line"]
            del actual_token["start_column"]
            del actual_token["start_line"]

        unmatched_tokens = [t for t in tokens if t not in actual_tokens]
        if unmatched_tokens:
            self.fail("not all expected %s lex tokens were found in the "
                      "actual lexer output:\n"
                      "  buffer:\n%s\n"
                      "  actual lexer tokens:\n%s\n"
                      "  unmatched tokens:\n%s\n"
                      % (lang, indent(content), indent(pformat(actual_tokens)),
                         indent(pformat(unmatched_tokens))))


def writefile(path, content, mode='wb'):
    if not exists(dirname(path)):
        os.makedirs(dirname(path))
    if "b" in mode and isinstance(content, str):
        content = content.encode("utf-8")
    with open(path, mode) as fout:
        fout.write(content)


# Recipe: rmtree (0.5) in /home/trentm/tm/recipes/cookbook
def _rmtree_OnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        os.chmod(filePath, 0o777)
        rmFunction(filePath)


def rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, onerror=_rmtree_OnError)


# Recipe: run (0.5.3) in /home/trentm/tm/recipes/cookbook
def run(cmd):
    """Run the given command. Raises OSError if the command returns a
    non-zero exit status."""
    retval = os.system(cmd)
    status = os.WEXITSTATUS(retval) if hasattr(os, "WEXITSTATUS") else retval
    if status:
        raise OSError("error running '%s': %r" % (cmd, status))


def run_in_dir(cmd, cwd):
    """Run the given command in the given working directory."""
    old_dir = os.getcwd()
    try:
        os.chdir(cwd)
        run(cmd)
    finally:
        os.chdir(old_dir)
