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

"""support for codeintel test modules"""

import functools
import json
import os
import sys
from os.path import dirname, join, normpath, exists, basename, abspath
from glob import glob
from pprint import pprint, pformat
import unittest
import random
from hashlib import md5
import re

from codeintel2.manager import Manager
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text
from codeintel2.citadel import CitadelBuffer
from codeintel2.common import *
from codeintel2.environment import SimplePrefsEnvironment

if _xpcom_:
    from xpcom import components



#---- globals

test_db_base_dir = join(dirname(abspath(__file__)), "tmp-db-base-dir")



#---- test support class (CodeIntelTestCase) and other support stuff

class _CaptureEvalController(EvalController):
    log = None
    def _log(self, lvl, msg, *args):
        if self.log is None: self.log = []
        self.log.append((lvl, msg % args))
    def debug(self, msg, *args): self._log("debug", msg, *args)
    def  info(self, msg, *args): self._log( "info", msg, *args)
    def  warn(self, msg, *args): self._log( "warn", msg, *args)
    def error(self, msg, *args): self._log("error", msg, *args)

class CodeIntelTestCase(unittest.TestCase):
    # Subclasses can override this to have setUp pass these settings to the
    # codeintel.Manager.
    _ci_db_base_dir_ = None
    _ci_db_catalog_dirs_ = []
    _ci_db_import_everything_langs = None
    _ci_env_prefs_ = None
    # A test case can set this to false to have the setUp/tearDown *not*
    # create a `self.mgr'.
    _ci_test_setup_mgr_ = True
    _ci_extra_module_dirs_ = None

    def ci_setUpClass(cls):
        if _xpcom_:
            # The tests are run outside of Komodo. If run with PyXPCOM up
            # parts codeintel will try to use the nsIDirectoryService and
            # will query dirs only provided by nsXREDirProvider -- which
            # isn't registered outside of Komodo (XRE_main() isn't called).
            # The KoTestService provides a backup.
            koTestSvc = components.classes["@activestate.com/koTestService;1"] \
                .getService(components.interfaces.koITestService)
            koTestSvc.init()

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

        init_xml_catalogs()

    def ci_tearDownClass(cls):
        if cls._ci_test_setup_mgr_:
            cls.mgr.finalize()
            cls.mgr = None

    if sys.version_info[:2] < (2, 7):
        # Python 2.6 and earlier does not support class setup/teardown, so we
        # have to initialize the manager on every test, icky!
        def setUp(self):
            self.__class__.ci_setUpClass(self)
        def tearDown(self):
            self.__class__.ci_tearDownClass(self)
    else:
        # Python 2.7 provides classlevel methods for setup/teardown.
        setUpClass = classmethod(ci_setUpClass)
        tearDownClass = classmethod(ci_tearDownClass)

    def adjust_content(self, content):
        """A hook for subclasses to modify markedup_content before use in
        test cases. This is useful for sharing test cases between pure-
        and multi-lang uses of a given lang.
        """
        return content
    def adjust_pos(self, pos):
        """A accompanying hook for `adjust_content' to adjust trigger
        pos values accordingly.
        """
        return pos

    def _get_buf_and_data(self, markedup_content, lang, path=None, env=None):
        encoding = None
        if path is None:
            # Try to ensure no accidental re-use of the same buffer name
            # across the whole test suite. Also try to keep the buffer
            # names relatively short (keeps tracebacks cleaner).
            if isinstance(markedup_content, unicode):
                markedup_bytes = markedup_content.encode("utf-8")
                encoding = "utf-8"
            else:
                markedup_bytes = markedup_content
            name = "buf-" + md5(markedup_bytes).hexdigest()[:16]
            path = os.path.join("<Unsaved>", name)
        content, data = unmark_text(self.adjust_content(markedup_bytes))
        #print banner(path)
        #sys.stdout.write(content)
        #print banner(None)
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
            except:
                self.fail("Trigger could not be serialized")
        return buf, trg

    def assertCITDLExprUnderPosIs(self, markedup_content, citdl_expr, lang=None,
                          prefix_filter=None, implicit=True, trigger_name=None,
                          **fields):
        """Assert that the CITDL expression at the current position
        is as expected.

        This uses buf.citdl_expr_under_pos() -- or, for Perl,
        buf.citdl_expr_and_prefix_filter_from_trg().
        Note: This API is a mess right now. C.f. bug 65776.

        The "prefix_filter" optional argument can be used for Perl to test
        the value its relevant function returns.
        """
        if lang is None:
            lang = self.lang
        content, data = unmark_text(
            self.adjust_content(markedup_content))
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
            #actual_citdl_expr = langintel.citdl_expr_under_pos(buf, data["pos"])
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
            XXX #TODO: compare prefix_filter to given value

    def _assertDefnMatches(self, buf, pos, lang=None, **fields):
        ctlr = _CaptureEvalController()
        trg = buf.defn_trg_from_pos(pos)
        defns = buf.defns_from_trg(trg, ctlr=ctlr)
        if not defns:
            self.fail("unexpectedly did not find a definition in %r at pos %d\n"
                "  eval log\n%s\n"
                "  buffer:\n%s"
                % (buf, pos,
                   indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
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
                   indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
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
        definition.  It can however be used to ensure we don't regress things
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
                   indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
                   indent(buf.accessor.text)))
        if "pos" in fields:
            fields["pos"] = self.adjust_pos(fields["pos"])

        # Copy defns over to filter for keys we care about
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
            if defn_repr not in count_from_defn_repr:
                count_from_defn_repr[defn_repr] = 0
            count_from_defn_repr[defn_repr] += 1
        defn_dupes = [(count, defn_repr)
                      for defn_repr, count in count_from_defn_repr.items()
                      if count > 1]
        self.failIf(defn_dupes,
            "unexpectedly got duplicate completions at the given position\n"
            "  duplicates:\n%s\n"
            "  eval log\n%s\n"
            "  buffer:\n%s"
            % (indent('\n'.join('%d of %s' % d for d in defn_dupes)),
               indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
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

    # Used when a position generates a trigger, but it's not the one specified
    def assertTriggerDoesNotMatch(self, markedup_content, lang=None,
                                  implicit=True, env=None, **fields):
        if lang is None:
            lang = self.lang
        buf, trg = self._get_buf_and_trg(markedup_content, lang,
                                         implicit=implicit, env=env)
        if trg is None:
            # No trigger is as good as
            return
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
        content, data = unmark_text(
            self.adjust_content(markedup_content))
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
        content, data = unmark_text(
            self.adjust_content(markedup_content))
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
        content, data = unmark_text(
            self.adjust_content(markedup_content))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        buf.scan(skip_scan_time_check=True)
        actual_blob, actual_lpath = buf.scoperef_from_pos(data["pos"])
        self.failUnlessEqual(lpath, actual_lpath,
            "unexpected %s scope lookup path (lpath) at the given position\n"
            "  expected: %r\n"
            "  got:      %r\n"
            "  buffer:\n%s"
            % (self.lang, lpath,
               actual_lpath,
               indent(markedup_content)))

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
            buf.unload() # remove any entry from CIDB to ensure clean test
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
               indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
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
            buf.unload() # remove any entry from CIDB to ensure clean test
        ctlr = _CaptureEvalController()
        actual_completions = buf.cplns_from_trg(trg, ctlr=ctlr)
        if actual_completions is None:
            self.fail("%s trigger resulted in no completions when expecting "
                      "to check for duplicate completions:\n%s"
                      % (lang, indent(markedup_content)))

        count_from_cpln = {}
        for cpln in actual_completions:
            if cpln not in count_from_cpln:
                count_from_cpln[cpln] = 0
            count_from_cpln[cpln] += 1
        cpln_dupes = [(count, cpln) for cpln, count in count_from_cpln.items()
                      if count > 1]
        self.failIf(cpln_dupes,
            "unexpectedly got duplicate completions at the given position\n"
            "  duplicates:\n%s\n"
            "  eval log\n%s\n"
            "  buffer:\n%s"
            % (indent('\n'.join('%d of %r' % d for d in cpln_dupes)),
               indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
               indent(markedup_content)))

    def _assertCompletionsInclude(self, buf, trg, completions, unload=True):
        markedup_content = markup_text(buf.accessor.text, pos=trg.pos)
        if unload and isinstance(buf, CitadelBuffer):
            buf.unload() # remove any entry from CIDB to ensure clean test
        ctlr = _CaptureEvalController()
        actual_completions = buf.cplns_from_trg(trg, ctlr=ctlr)
        missing_completions = [c for c in completions
                               if c not in (actual_completions or [])]
        self.failIf(missing_completions,
            "%s completions at the given position did not "
            "include all expected values\n"
            "  missing:         %r\n"
            "  expected all of: %r\n"
            "  got:             %r\n"
            "  eval log:\n%s\n"
            "  buffer:\n%s"
            % (buf.lang, missing_completions, completions,
               actual_completions,
               indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
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
            buf.unload() # remove any entry from CIDB to ensure clean test
        ctlr = _CaptureEvalController()
        actual_completions = buf.cplns_from_trg(trg, ctlr=ctlr)
        completions_that_shouldnt_be_there = [
            c for c in (actual_completions or []) if c in completions
        ]
        self.failIf(completions_that_shouldnt_be_there,
            "%s completions at the given position included "
            "some unexpected values\n"
            "  shouldn't have had these: %r\n"
            "  expected none of:         %r\n"
            "  got:                      %r\n"
            "  eval log:\n%s\n"
            "  buffer:\n%s"
            % (buf.lang, completions_that_shouldnt_be_there, completions,
               actual_completions,
               indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
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
                      % (lang, indent(calltip),
                         indent(markedup_content)))

        if isinstance(buf, CitadelBuffer):
            buf.unload() # remove any entry from CIDB to ensure clean test
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
               indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
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
                      % (lang, indent(expr),
                         indent(markedup_content)))

        if isinstance(buf, CitadelBuffer):
            buf.unload() # remove any entry from CIDB to ensure clean test
        ctlr = _CaptureEvalController()
        actual_calltips = buf.calltips_from_trg(trg, ctlr=ctlr)
        if actual_calltips and actual_calltips[0]:
            actual_calltip = actual_calltips[0]
        else:
            actual_calltip = None
        self.assertNotEquals(re.search(expr, actual_calltip, flags), None,
            "unexpected %s calltip at the given position\n"
            "  expression:\n%s\n"
            "  got:\n%s\n"
            "  eval log:\n%s\n"
            "  buffer:\n%s"
            % (trg.name, indent(expr and expr or "(none)"),
               indent(actual_calltip and actual_calltip or "(none)"),
               indent('\n'.join('%5s: %s' % (lvl,m) for lvl,m in ctlr.log)),
               indent(markedup_content)))

    def assertCurrCalltipArgRange(self, markedup_content, calltip,
                                  expected_range, lang=None, implicit=True):
        if lang is None:
            lang = self.lang
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        content, data = unmark_text(
            self.adjust_content(markedup_content))
        pos = data["pos"]
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        trg = buf.trg_from_pos(data["trg_pos"], implicit=implicit)
        actual_range = buf.curr_calltip_arg_range(trg.pos, calltip,
                                                  curr_pos=data["pos"])
        self.assertEqual(actual_range, expected_range,
            "unexpected current calltip arg range\n"
            "   expected: %s\n"
            "   got:      %s\n"
            "   calltip:\n%s\n"
            "   buffer:\n%s"
            % (expected_range, actual_range, indent(calltip),
               indent(markedup_content)))

    #def assertCompletionRaises(self, markedup_content, exception, lang=None,
    #                           **kwargs):
    #    """Assert that the given completion raises the given exception.
    #    
    #    You may also specify either of the "exc_args" or "exc_pattern"
    #    keyword args to match the exception's "args" attribute or match
    #    the stringified exception against a regex pattern.
    #    
    #    c.f. http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/307970
    #    """
    #    if lang is None:
    #        lang = self.lang
    #    if "exc_args" in kwargs:
    #        exc_args = kwargs["exc_args"]
    #        del kwargs["exc_args"]
    #    else:
    #        exc_args = None
    #    if "exc_pattern" in kwargs:
    #        exc_pattern = kwargs["exc_pattern"]
    #        del kwargs["exc_pattern"]
    #    else:
    #        exc_pattern = None
    #
    #    callsig = "the given %s completion" % lang
    #    try:
    #        buf, trg = self._get_buf_and_trg(markedup_content, lang)
    #        if trg is None:
    #            self.fail("given position is not a %s trigger point, "
    #                      "no completion can be done to see if it raises"
    #                      % self.lang)
    #        callsig = "completion at %s" % trg
    #        cplns = buf.cplns_from_trg(trg)
    #    except exception, exc:
    #        if exc_args is not None:
    #            self.failIf(exc.args != exc_args,
    #                        "%s raised %s with unexpected args: "\
    #                        "expected=%r, actual=%r"\
    #                        % (callsig, exc.__class__, exc_args, exc.args))
    #        if exc_pattern is not None:
    #            self.failUnless(exc_pattern.search(str(exc)),
    #                            "%s raised %s, but the exception "\
    #                            "does not match '%s': %r"\
    #                            % (callsig, exc.__class__, exc_pattern.pattern,
    #                               str(exc)))
    #    except:
    #        exc_info = sys.exc_info()
    #        print exc_info
    #        self.fail("%s raised an unexpected exception type: "\
    #                  "expected=%s, actual=%s"\
    #                  % (callsig, exception, exc_info[0]))
    #    else:
    #        self.fail("%s did not raise %s" % (callsig, exception))

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
            buf.unload() # remove any entry from CIDB to ensure clean test

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
            self.fail("evalution had results: didn't expect that: %r"
                      % ctlr.cplns)
        elif trg.form == TRG_FORM_CALLTIP and ctlr.calltips:
            self.fail("evalution had results: didn't expect that: %r"
                      % ctlr.cplns)
        if log_pattern:
            #pprint(ctlr.log)
            matching_logs = [(level, msg) for level, msg in ctlr.log
                             if log_pattern.search(msg)]
            self.failUnless(matching_logs,
                "the given completion failed but no logs matched the given pattern:\n"
                "  log_pattern: /%s/\n"
                "  log messages:\n%s\n"
                "  buffer:\n%s"
                % (log_pattern.pattern,
                   indent('\n'.join(['%s: %s' % lg for lg in ctlr.log])),
                   indent(markedup_content)))
            #pprint(matching_logs)

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
        content, data = unmark_text(
            self.adjust_content(markedup_content))
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        langintel = self.mgr.langintel_from_lang(lang)
        if trigger_name is None:
            trigger_name = "fakey-completion-type"

        if lang == "Perl":
            # Bit of a hack to fake the trigger length.
            if content[data["pos"]-1] in ('>', ':'): # '->' or '::' triggers
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
                    #'end_column': ???,
                    #'end_line': ???,
                    #'start_column': ???,
                    #'start_line': ???,
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
        from codeintel2.accessor import SilverCityAccessor
        if lang is None:
            lang = self.lang

        content, tokens = self._unmark_lex_text(markedup_content)

        # Do lexing of this content via the codeintel Buffer's, because
        # they already handle all the SilverCity lexer hookup.
        path = os.path.join("<Unsaved>", "rand%d" % random.randint(0, 100))
        buf = self.mgr.buf_from_content(content, lang=lang, path=path)
        assert isinstance(buf.accessor, SilverCityAccessor)
        actual_tokens = buf.accessor.tokens # cheating
        for actual_token in actual_tokens:
            # There are a few SilverCity token dict keys that we
            # don't bother checking.
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
                      % (lang,
                         indent(content), 
                         indent(pformat(actual_tokens)),
                         indent(pformat(unmatched_tokens))))

def gen_crimper_support_dir_candidates():
    if sys.platform == "win32":
        yield r"\\crimper\apps\Komodo\support\codeintel"
    else:
        yield "/mnt/crimper.home/apps/Komodo/support/codeintel"
        yield "/mnt/crimper/apps/Komodo/support/codeintel"
        yield "/mnt/crimper/home/apps/Komodo/support/codeintel"


def writefile(path, content, mode='wb'):
    if not exists(dirname(path)):
        os.makedirs(dirname(path))
    fout = open(path, mode)
    try:
        fout.write(content)
    finally:
        fout.close()


_xml_catalogs_initialized = False
def init_xml_catalogs():
    global _xml_catalogs_initialized
    if _xml_catalogs_initialized:
        return
    # We have to initialize the catalog service so completion testing
    # will work.
    _xml_catalogs_initialized = True
    import koXMLDatasetInfo
    kodevel_basedir = dirname(dirname(dirname(dirname(abspath(__file__)))))
    catalog = join(kodevel_basedir, "test", "stuff", "xml", "testcat.xml")
    catsvc = koXMLDatasetInfo.getService()
    catsvc.resolver.resetCatalogs([catalog])


# Recipe: rmtree (0.5) in /home/trentm/tm/recipes/cookbook
def _rmtree_OnError(rmFunction, filePath, excInfo):
    if excInfo[0] == OSError:
        # presuming because file is read-only
        os.chmod(filePath, 0777)
        rmFunction(filePath)
def rmtree(dirname):
    import shutil
    shutil.rmtree(dirname, 0, _rmtree_OnError)


# Recipe: run (0.5.3) in /home/trentm/tm/recipes/cookbook
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

def run(cmd, logstream=_RUN_DEFAULT_LOGSTREAM):
    """Run the given command.

        "cmd" is the command to run
        "logstream" is an optional logging stream on which to log the 
            command. If None, no logging is done. If unspecifed, this 
            looks for a Logger instance named 'log' and logs the command 
            on log.debug().

    Raises OSError is the command returns a non-zero exit status.
    """
    __run_log(logstream, "running '%s'", cmd)
    retval = os.system(cmd)
    if hasattr(os, "WEXITSTATUS"):
        status = os.WEXITSTATUS(retval)
    else:
        status = retval
    if status:
        #TODO: add std OSError attributes or pick more approp. exception
        raise OSError("error running '%s': %r" % (cmd, status))

def run_in_dir(cmd, cwd, logstream=_RUN_DEFAULT_LOGSTREAM):
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
        run(cmd, logstream=None)
    finally:
        os.chdir(old_dir)



# Recipe: splitall (0.2) in /home/trentm/tm/recipes/cookbook
def splitall(path):
    r"""Split the given path into all constituent parts.

    Often, it's useful to process parts of paths more generically than
    os.path.split(), for example if you want to walk up a directory.
    This recipe splits a path into each piece which corresponds to a
    mount point, directory name, or file.  A few test cases make it
    clear:
        >>> splitall('')
        []
        >>> splitall('a/b/c')
        ['a', 'b', 'c']
        >>> splitall('/a/b/c/')
        ['/', 'a', 'b', 'c']
        >>> splitall('/')
        ['/']
        >>> splitall('C:\\a\\b')
        ['C:\\', 'a', 'b']
        >>> splitall('C:\\a\\')
        ['C:\\', 'a']

    (From the Python Cookbook, Files section, Recipe 99.)
    """
    allparts = []
    while 1:
        parts = os.path.split(path)
        if parts[0] == path:  # sentinel for absolute paths
            allparts.insert(0, parts[0])
            break
        elif parts[1] == path: # sentinel for relative paths
            allparts.insert(0, parts[1])
            break
        else:
            path = parts[0]
            allparts.insert(0, parts[1])
    allparts = [p for p in allparts if p] # drop empty strings 
    return allparts


# Recipe: relpath (0.2) in /home/trentm/tm/recipes/cookbook
def relpath(path, relto=None):
    """Relativize the given path to another (relto).

    "relto" indicates a directory to which to make "path" relative.
        It default to the cwd if not specified.
    """
    if not os.path.isabs(path):
        path = os.path.abspath(path)
    if relto is None:
        relto = os.getcwd()
    else:
        relto = os.path.abspath(relto)

    if sys.platform.startswith("win"):
        def _equal(a, b): return a.lower() == b.lower()
    else:
        def _equal(a, b): return a == b

    pathDrive, pathRemainder = os.path.splitdrive(path)
    if not pathDrive:
        pathDrive = os.path.splitdrive(os.getcwd())[0]
    relToDrive, relToRemainder = os.path.splitdrive(relto)
    if not _equal(pathDrive, relToDrive):
        # Which is better: raise an exception or return ""?
        return ""
        #raise OSError("Cannot make '%s' relative to '%s'. They are on "\
        #              "different drives." % (path, relto))

    pathParts = splitall(pathRemainder)[1:] # drop the leading root dir
    relToParts = splitall(relToRemainder)[1:] # drop the leading root dir
    #print "_relpath: pathPaths=%s" % pathParts
    #print "_relpath: relToPaths=%s" % relToParts
    for pathPart, relToPart in zip(pathParts, relToParts):
        if _equal(pathPart, relToPart):
            # drop the leading common dirs
            del pathParts[0]
            del relToParts[0]
    #print "_relpath: pathParts=%s" % pathParts
    #print "_relpath: relToParts=%s" % relToParts
    # Relative path: walk up from "relto" dir and walk down "path".
    relParts = [os.curdir] + [os.pardir]*len(relToParts) + pathParts
    #print "_relpath: relParts=%s" % relParts
    relPath = os.path.normpath( os.path.join(*relParts) )
    return relPath


def override_encoding(encoding=None):
    """
    Decorator to override the system default encoding for a test; this is usually
    used to trigger errors that occur when the system default encoding is ASCII.
    """
    def decorator(test_function):
        @functools.wraps(test_function)
        def wrapper(*args, **kwargs):
            previous_encoding = sys.getdefaultencoding()
            # We need to reload(sys) to have access to sys.setdefaultencoding;
            # save stdin/stdout/stderr redirection to avoid those getting clobbered.
            if not hasattr(sys, "setdefaultencoding"):
                stdin = sys.stdin
                stdout = sys.stdout
                stderr = sys.stderr
                reload(sys)
                sys.stdin = stdin
                sys.stdout = stdout
                sys.stderr = stderr
            sys.setdefaultencoding(encoding)
            try:
                return test_function(*args, **kwargs)
            finally:
                sys.setdefaultencoding(previous_encoding)
        return wrapper
    if callable(encoding):
        # @override_encoding instead of @override_encoding("ascii")...
        function = encoding
        encoding = "ascii"
        return decorator(function)
    return decorator
