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

"""Test the codeintel database (v2)."""

import os
import sys
import re
from os.path import (join, dirname, abspath, exists, basename, splitext,
                     isabs)
from glob import glob
from pprint import pprint
import unittest
import time
import logging

import codeintel2
from codeintel2.common import *
from codeintel2.manager import Manager
from codeintel2.util import indent, dedent, banner, markup_text, \
                            unmark_text, safe_lang_from_lang

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import (CodeIntelTestCase, writefile, run, run_in_dir,
                         gen_crimper_support_dir_candidates, relpath)

import ciElementTree as ET


log = logging.getLogger("test")
#log.setLevel(logging.DEBUG)


class DBTestCase(CodeIntelTestCase):
    def _check_db(self, db=None):
        if db is None: db = self.mgr.db
        errors = db.check()
        self.failIf(errors,
            "database internal consistency errors after run:\n%s"
            % indent('\n'.join(errors)))


class PHPCorruptionTestCase(DBTestCase):
    test_dir = join(os.getcwd(), "tmp", "php-db-corruption")

    @tag("bug78401", "php")
    def test_missing_blob_file_recovery_multilang(self):
        # Create a PHP file, load it into the database.
        path = join(self.test_dir, "missing_blob_file.php")
        writefile(path, "<?php echo 'hi'; function bar() {} ?>")
        buf = self.mgr.buf_from_path(path, lang="PHP")
        buf.scan(skip_scan_time_check=True)

        # Manually delete the blob file.
        db = self.mgr.db
        dhash = db.dhash_from_dir(dirname(path))
        bhash = db.bhash_from_blob_info(buf.path, "PHP", buf.tree[0][0].get("name"))
        blob_path = join(db.base_dir, "db", "php", dhash, bhash + ".blob")
        os.unlink(blob_path)
        assert not exists(blob_path)

        # Try to get the buf data: we expect the buffer to be re-scanned
        # and proper data returned.
        #
        # Get a new buffer instance (to avoid the buf scan data caching).
        # Note: Relying on NOT having buf caching for this. If/when buf
        # caching is added, then alternative it to cheat and remove buf's
        # cache of scan data.
        buf2 = self.mgr.buf_from_path(path, lang="PHP")
        blob = buf2.tree[0][0]

        # - ensure the corruption was noted
        self.failUnlessEqual(len(db.corruptions), 1)
        corruption = db.corruptions[0]
        self.failUnless("get_buf_data" in corruption[0])
        self.failUnless("missing_blob_file" in corruption[1])
        self.failUnlessEqual(corruption[2], "recover")

        # - ensure the scan data was obtained
        self.failUnlessEqual(blob.get("lang"), "PHP")
        self.failUnlessEqual(blob[0].get("ilk"), "function")
        self.failUnlessEqual(blob[0].get("name"), "bar")
    
class PythonCorruptionTestCase(DBTestCase):
    test_dir = join(os.getcwd(), "tmp", "python-db-corruption")

    @tag("bug78401", "python")
    def test_missing_blob_file_recovery(self):
        # Create a Python file, load it into the database.
        path = join(self.test_dir, "missing_blob_file.py")
        writefile(path, "def bar(): pass")
        buf = self.mgr.buf_from_path(path, lang="Python")
        buf.scan(skip_scan_time_check=True)

        # Manually delete the blob file.
        db = self.mgr.db
        dhash = db.dhash_from_dir(dirname(path))
        bhash = db.bhash_from_blob_info(buf.path, "Python", buf.tree[0][0].get("name"))
        blob_path = join(db.base_dir, "db", "python", dhash, bhash + ".blob")
        os.unlink(blob_path)
        assert not exists(blob_path)
        
        # Try to get the buf data: we expect the buffer to be re-scanned
        # and proper data returned.
        #
        # Get a new buffer instance (to avoid the buf scan data caching).
        # Note: Relying on NOT having buf caching for this. If/when buf
        # caching is added, then alternative it to cheat and remove buf's
        # cache of scan data.
        db.corruptions = []
        buf2 = self.mgr.buf_from_path(path, lang="Python")
        blob = buf2.tree[0][0]

        # - ensure the corruption was noted
        self.failUnlessEqual(len(db.corruptions), 1)
        corruption = db.corruptions[0]
        self.failUnless("get_buf_data" in corruption[0])
        self.failUnless("missing_blob_file" in corruption[1])
        self.failUnlessEqual(corruption[2], "recover")

        # - ensure the scan data was obtained
        self.failUnlessEqual(blob.get("lang"), "Python")
        self.failUnlessEqual(blob[0].get("ilk"), "function")
        self.failUnlessEqual(blob[0].get("name"), "bar")

class UpgradeTestCase(DBTestCase):
    # Don't create the manager and upgrade/init.
    _ci_test_setup_mgr_ = False
    test_dir = join(os.getcwd(), "tmp")

    def _test_dbs(self):
        """Generate all available test DBs.
        
        These will be paths to .zip files of the test DB.
        """
        for support_dir in gen_crimper_support_dir_candidates():
            if exists(support_dir): break
        else:
            raise TestSkipped("couldn't find the codeintel support dir "
                              "on crimper")
        for path in glob(join(support_dir, "cidb2_corpus", "*.zip")):
            yield path

    @tag("fs") # tag to indicate this is heavy on the filesystem
    def test_upgrade(self):
        for db_zip in self._test_dbs():
            db_zip_base = basename(db_zip)
            log.info("test upgrading `%s'...", db_zip_base)
            test_dir = join(self.test_dir, "upgrade",
                            splitext(db_zip_base)[0])
            # setup
            if exists(test_dir):
                import shutil
                shutil.rmtree(test_dir)
            os.makedirs(test_dir)
            run_in_dir("unzip -q %s" % db_zip, test_dir, log.info)

            db_base_dir = (glob(join(test_dir, "*"))
                           + glob(join(test_dir, ".*")))[0]
            mgr = Manager(db_base_dir)
            try:
                mgr.upgrade()
                self._check_db(db=mgr.db)
            finally:
                mgr.finalize()

YUI_BLOB_NAME = "yui_v2.8.1"

class CatalogTestCase(DBTestCase):
    test_catalog_dir = join(os.getcwd(), "tmp")
    _ci_db_catalog_dirs_ = [test_catalog_dir]

    def test_abspaths(self):
        # Ensure that loaded catalogs from the *core* catalog area
        # use the "area-relative paths".
        ci_pkg_dir = dirname(abspath(codeintel2.__file__))
        mochikit_cix = join("catalogs", "mochikit.cix")
        landmark = join(ci_pkg_dir, mochikit_cix)
        self.failUnless(exists(landmark),
            "landmark catalog CIX file `%s' does not exist: "
            "cannot run this test" % landmark)

        catalogs_zone = self.mgr.db.get_catalogs_zone()
        catalogs_zone.update()
        expected_key = ('ci-pkg-dir', mochikit_cix)
        for res_path in catalogs_zone.res_index:
            if res_path == expected_key:
                break
        else:
            self.fail("no entries in the catalog res_index matched: %r"
                      % (expected_key,))

        self._check_db()

    def test_update(self):
        # Want to test that add, removes and updates to the catalog are
        # working for multiple languages.

        cix_template = dedent("""\
            <codeintel version="2.0">
                <file path="test_update" lang="%(lang)s">
                    <scope ilk="blob" lang="%(lang)s" name="test_update">
                        <scope ilk="class" line="3" lineend="5" name="Foo">
                            <scope ilk="function" line="4" lineend="5" name="foo"/>
                        </scope>
                    </scope>
                </file>
            </codeintel>
        """)
        
        catalogs_zone = self.mgr.db.get_catalogs_zone()
        for lang in ("Python", "Perl", "Ruby", "Tcl", "PHP", "JavaScript"):
            catalog_lib = self.mgr.db.get_catalog_lib(lang)
            cix_path = join(self.test_catalog_dir, "test_update.cix")
            if exists(cix_path):
                os.remove(cix_path)
            catalogs_zone.update() # flush our test file from the catalog
            self.failIf(catalog_lib.has_blob("test_update"))

            writefile(cix_path, cix_template % {"lang": lang})
            catalogs_zone.update()
            self.failUnless(catalog_lib.has_blob("test_update"))

            # Hack into the catalog indeces so we can check that the
            # dbfile actually gets removed.
            dbfile, res_id = catalogs_zone.blob_index[lang]["test_update"]
            dbpath = join(catalogs_zone.base_dir,
                          safe_lang_from_lang(lang), dbfile)
            os.remove(cix_path)
            catalogs_zone.update()
            self.failIf(catalog_lib.has_blob("test_update"),
                "%s catalog lib has 'test_update' blob and should not" % lang)
            self.failIf(exists(dbpath),
                "'%s' was removed from the catalog, but its internal "
                "dbfile '%s' was not removed" % (cix_path, dbpath))

        self._check_db()

    def test_update_error(self):
        # Test updating catalog with bogus CIX.
        bogus_cix = join(self.test_catalog_dir, "bogus.cix")
        writefile(bogus_cix, "this is bogus cix")
        catalogs_zone = self.mgr.db.get_catalogs_zone()
        # Currently this should warn about the bogus cix. We are testing
        # that it does not fail the update.
        catalogs_zone.update()
        os.remove(bogus_cix)

        self._check_db()

    @tag("yui")
    def test_lpaths_from_blob(self):
        catalogs_zone = self.mgr.db.get_catalogs_zone()
        catalogs_zone.update() # make sure yui.cix is loaded
        yui_lpaths = catalogs_zone.lpaths_from_lang_and_blobname(
                        "JavaScript", YUI_BLOB_NAME)
        self.failUnless(("YAHOO",) in yui_lpaths)

    def test_toplevelname_index(self):
        # Test that this index is being maintained properly.
        name = "test_bftfl"
        lang = "JavaScript"
        cix = dedent("""\
            <codeintel version="2.0">
                <file path="test_update" lang="%(lang)s">
                    <scope ilk="blob" lang="%(lang)s" name="%(name)s">
                        <scope ilk="class" line="3" lineend="5" name="TestBftfl"/>
                        <scope ilk="function" line="4" lineend="5" name="%(name)s"/>
                    </scope>
                </file>
            </codeintel>
        """ % {"lang": lang, "name": name})
        
        catalogs_zone = self.mgr.db.get_catalogs_zone()
        cix_path = join(self.test_catalog_dir, name+".cix")
        writefile(cix_path, cix)
        catalogs_zone.update()

        # Hack to trigger filling-out of toplevelname_index.
        catalogs_zone.lpaths_from_lang_and_blobname(lang, name)
        catalogs_zone.lpaths_from_lang_and_blobname(lang, YUI_BLOB_NAME)

        # toplevelname_index: {lang -> ilk -> toplevelname -> res_id -> blobnames}
        toplevelname_index = catalogs_zone.toplevelname_index
        self.failUnless(lang in toplevelname_index)
        self.failUnless("TestBftfl" in toplevelname_index[lang]["class"])
        self.failUnless(name in toplevelname_index[lang]["function"])

        os.remove(cix_path)
        catalogs_zone.update()
        self.failIf("TestBftfl" in toplevelname_index[lang]["class"])
        self.failIf(name in toplevelname_index[lang]["function"])

        self._check_db()

    @tag("knownfailure")
    def test_selection(self):
        # Test enabling/disabling specific catalogs.
        # CatalogLib APIs to check:
        #   .has_blob
        #   .get_blob
        #   .get_sub_blobnames (Can't really test for JS. Test with PyWin32.)
        #   .hits_from_lpath
        import codeintel2
        catalog_dir = join(dirname(codeintel2.__file__), "catalog")

        # Baseline: test with no selection.
        catalog_lib = self.mgr.db.get_catalog_lib("JavaScript")
        self.failUnless( catalog_lib.has_blob(YUI_BLOB_NAME) )
        self.failUnless( catalog_lib.get_blob(YUI_BLOB_NAME) is not None )
        self.failUnless( catalog_lib.hits_from_lpath(("YAHOO",)) )
        self.failUnless( catalog_lib.has_blob("MochiKit.DateTime") )
        self.failUnless( catalog_lib.get_blob("MochiKit.DateTime") is not None )
        # Disabled. See test_mochikit_hits_from_lpath().
        #self.failUnless( catalog_lib.hits_from_lpath(("MochiKit.DateTime",)) )

        # Just select MochiKit.
        selections = (["mochikit"],                        # name selector
                      ["MochiKit"],                        # name selector with case diffs
                      [join(catalog_dir, "mochikit.cix")]) # path selector
        for selection in selections:
            catalog_lib = self.mgr.db.get_catalog_lib("JavaScript", selection)
            self.failIf( catalog_lib.has_blob(YUI_BLOB_NAME) )
            self.failIf( catalog_lib.get_blob(YUI_BLOB_NAME) is not None )
            self.failIf( catalog_lib.hits_from_lpath(("YAHOO",)) )
            self.failUnless( catalog_lib.has_blob("MochiKit.DateTime") )
            self.failUnless( catalog_lib.get_blob("MochiKit.DateTime") is not None )
            # Disabled. See test_mochikit_hits_from_lpath().
            #self.failUnless( catalog_lib.hits_from_lpath(("MochiKit.DateTime",)) )

        # Just select YUI.
        selections = (["yui"],                        # name selector
                      [join(catalog_dir, "yui.cix")]) # path selector
        for selection in selections:
            catalog_lib = self.mgr.db.get_catalog_lib("JavaScript", selection)
            self.failUnless( catalog_lib.has_blob(YUI_BLOB_NAME) )
            self.failUnless( catalog_lib.get_blob(YUI_BLOB_NAME) is not None )
            self.failUnless( catalog_lib.hits_from_lpath(("YAHOO",)) )
            self.failIf( catalog_lib.has_blob("MochiKit.DateTime") )
            self.failIf( catalog_lib.get_blob("MochiKit.DateTime") is not None )
            # Disabled. See test_mochikit_hits_from_lpath().
            #self.failIf( catalog_lib.hits_from_lpath(("MochiKit.DateTime",)) )

        # Test CatalogLib.get_sub_blobnames() with Python 'pywin32' catalog.
        catalog_lib = self.mgr.db.get_catalog_lib("Python")
        self.failUnless( "util" in catalog_lib.get_sub_blobnames(("win32com",)) )
        catalog_lib = self.mgr.db.get_catalog_lib("Python", ["pywin32"])
        self.failUnless( "util" in catalog_lib.get_sub_blobnames(("win32com",)) )
        catalog_lib = self.mgr.db.get_catalog_lib("Python", [])
        self.failIf( "util" in catalog_lib.get_sub_blobnames(("win32com",)) )
    

    @tag("knownfailure", "MochiKit")
    def test_mochikit_hits_from_lpath(self):
        # There is a difficulty is catalog_lib.hits_from_lpath() for
        # MochiKit because of its blob names including '.'.
        catalog_lib = self.mgr.db.get_catalog_lib("JavaScript", ["mochikit"])
        self.failUnless( catalog_lib.hits_from_lpath(("MochiKit.DateTime",)) )

    def test_avail_catalogs(self):
        catalogs_zone = self.mgr.db.get_catalogs_zone()
        avail_catalogs = catalogs_zone.avail_catalogs()
        for catalog in avail_catalogs:
            if catalog["lang"] == "JavaScript" \
               and catalog["name"] == "MochiKit":
                self.failUnless(catalog["selected"] is True)
                self.failUnless(catalog["selection"] is None)
                break
        else:
            self.fail("the 'MochiKit' JavaScript catalog was not found: "
                      "avail_catalogs=%r" % avail_catalogs)

        avail_catalogs = catalogs_zone.avail_catalogs(["yui"])
        for catalog in avail_catalogs:
            if catalog["lang"] == "JavaScript" \
               and catalog["name"] == "MochiKit":
                self.failIf(catalog["selected"],
                    "`catalog.zone.avail_catalogs' indicated that the "
                    "'mochikit' JavaScript catalog was selected when only "
                    "'yui' was selected")
                break
        else:
            self.fail("the 'MochiKit' JavaScript catalog was not found: "
                      "avail_catalogs=%r" % avail_catalogs)


class ImportEverythingTestCase(DBTestCase):
    """Test some APIs relevant for import-everything semantics.
    
    One of those is lib.toplevel_cplns().
    """
    test_dir = join(os.getcwd(), "tmp")
    test_catalog_dir = join(test_dir, "apicatalogs")
    _ci_db_catalog_dirs_ = [test_catalog_dir]
    _ci_db_import_everything_langs = set(["JavaScript", "PHP"])

    @tag("php")
    def test_stdlib(self):
        stdlib = self.mgr.db.get_stdlib("PHP")
        
        # Test without a 3-char prefix.
        self.failUnless(("function", "phpinfo")
            in stdlib.toplevel_cplns(ilk="function"))
        self.failUnless(("function", "array_pad")
            in stdlib.toplevel_cplns(ilk="function"))
        self.failIf(("function", "phpinfo")
            in stdlib.toplevel_cplns(ilk="class"))
        self.failUnless(("class", "DateTime")
            in stdlib.toplevel_cplns(ilk="class"))
        self.failUnless(("variable", "_COOKIE")
            in stdlib.toplevel_cplns(ilk="variable"))

        # Test with a 3-char prefix.
        self.failUnless(("function", "phpinfo")
            in stdlib.toplevel_cplns(prefix="php", ilk="function"))
        self.failUnless(("function", "phpinfo")
            in stdlib.toplevel_cplns(prefix="php"))
        self.failIf(("function", "array_pad")
            in stdlib.toplevel_cplns(prefix="php", ilk="function"))

    @tag("php")
    def test_multilanglib(self):
        # Setup test case.
        lang = "PHP"
        test_dir = join(self.test_dir, "impevy_multilanglib")
        manifest = [
            (join(test_dir, "foo.php"),
             "<?php global $foo_var = 42;\nfunction foo_func() { }\n ?>"),
            (join(test_dir, "bar.php"),
             "<?php global $bar_var = 42;\nfunction bar_func() { }\n ?>"),
        ]
        foo_php, foo_content = manifest[0]
        bar_php, bar_content = manifest[1]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        bar_buf = self.mgr.buf_from_path(bar_php, lang=lang)
        bar_buf.scan(skip_scan_time_check=True)
        foo_buf = self.mgr.buf_from_path(foo_php, lang=lang)
        foo_buf.scan(skip_scan_time_check=True)
        langlib = self.mgr.db.get_lang_lib(lang, "impevy_multilanglib",
                                           [test_dir], lang)

        # Test with no prefix.
        self.failUnless(("function", "foo_func")
            in langlib.toplevel_cplns(ilk="function"))
        self.failUnless(("variable", "bar_var")
            in langlib.toplevel_cplns(ilk="variable"))
        self.failIf(("function", "foo_func")
            in langlib.toplevel_cplns(ilk="variable"))
        self.failIf(("variable", "bar_var")
            in langlib.toplevel_cplns(ilk="function"))

        # Test with a prefix.
        self.failUnless(("function", "foo_func")
            in langlib.toplevel_cplns(prefix="foo"))
        self.failUnless(("variable", "foo_var")
            in langlib.toplevel_cplns(prefix="foo"))
        self.failUnless(("variable", "foo_var")
            in langlib.toplevel_cplns(prefix="foo", ilk="variable"))
        self.failIf(("variable", "bar_var")
            in langlib.toplevel_cplns(prefix="foo"))
        self.failIf(("variable", "foo_var")
            in langlib.toplevel_cplns(prefix="foo", ilk="class"))

    @tag("javascript")
    def test_langlib(self):
        # Setup test case.
        lang = "JavaScript"
        test_dir = join(self.test_dir, "impevy_langlib")
        manifest = [
            (join(test_dir, "foo.js"),
             "var foo_var = 42;\nfunction foo_func() { }\n"),
            (join(test_dir, "bar.js"),
             "var bar_var = 42;\nfunction bar_func() { }\n"),
        ]
        foo_php, foo_content = manifest[0]
        bar_php, bar_content = manifest[1]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        bar_buf = self.mgr.buf_from_path(bar_php, lang=lang)
        bar_buf.scan(skip_scan_time_check=True)
        foo_buf = self.mgr.buf_from_path(foo_php, lang=lang)
        foo_buf.scan(skip_scan_time_check=True)
        langlib = self.mgr.db.get_lang_lib(lang, "impevy_langlib",
                                           [test_dir], lang)

        # Test with no prefix.
        self.failUnless(("function", "foo_func")
            in langlib.toplevel_cplns(ilk="function"))
        self.failUnless(("variable", "bar_var")
            in langlib.toplevel_cplns(ilk="variable"))
        self.failIf(("function", "foo_func")
            in langlib.toplevel_cplns(ilk="variable"))
        self.failIf(("variable", "bar_var")
            in langlib.toplevel_cplns(ilk="function"))

        # Test with a prefix.
        self.failUnless(("function", "foo_func")
            in langlib.toplevel_cplns(prefix="foo"))
        self.failUnless(("variable", "foo_var")
            in langlib.toplevel_cplns(prefix="foo"))
        self.failUnless(("variable", "foo_var")
            in langlib.toplevel_cplns(prefix="foo", ilk="variable"))
        self.failIf(("function", "bar_var")
            in langlib.toplevel_cplns(prefix="foo"))
        self.failIf(("function", "foo_var")
            in langlib.toplevel_cplns(prefix="foo", ilk="class"))

    @tag("php", "javascript")
    def test_cataloglib(self):
        # Test that this index is being maintained properly.
        name = "sample_catalog"
        cix_template = dedent("""\
            <codeintel version="2.0">
                <file path="%(name)s%(ext)s" lang="%(lang)s">
                    <scope ilk="blob" lang="%(lang)s" name="%(name)s">
                        <scope ilk="class" line="3" lineend="5" name="SampleClass"/>
                        <scope ilk="function" line="4" lineend="5" name="sample_func"/>
                    </scope>
                </file>
            </codeintel>
        """)
        
        catalogs_zone = self.mgr.db.get_catalogs_zone()
        for lang, ext in [("PHP", ".php"), ("JavaScript", ".js")]:
            cix = cix_template % {"lang": lang, "name": name, "ext": ext}
            cix_path = join(self.test_catalog_dir, name+".cix")
            writefile(cix_path, cix)
            # HACK to ensure mtime for new catalog changes. Otherwise
            # .update() won't.
            time.sleep(1.0)
            catalogs_zone.update()

            # Test without a prefix, without a catalog selection.
            catalog_lib = self.mgr.db.get_catalog_lib(lang)
            self.failUnless(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(),
                "unexpected contents in %s top-level cplns" % lang)
            self.failUnless(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(ilk="class"))
            self.failUnless(("function", "sample_func")
                in catalog_lib.toplevel_cplns(ilk="function"))
            self.failIf(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(ilk="function"))

            # Test with a prefix, without a catalog selection.
            self.failUnless(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(prefix="Sam"))
            self.failUnless(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(prefix="Sam", ilk="class"))
            self.failIf(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(prefix="Sam", ilk="function"))
            self.failIf(("function", "sample_func")
                in catalog_lib.toplevel_cplns(prefix="Sam"))

            # Test without a prefix, with a catalog selection.
            catalog_lib = self.mgr.db.get_catalog_lib(lang, set([name]))
            self.failUnless(("class", "SampleClass")
                in catalog_lib.toplevel_cplns())
            self.failUnless(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(ilk="class"))
            self.failUnlessEqual([("class", "SampleClass")],
                catalog_lib.toplevel_cplns(ilk="class"))
            self.failUnless(("function", "sample_func")
                in catalog_lib.toplevel_cplns(ilk="function"))
            self.failIf(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(ilk="function"))
            
            # Test with a prefix, with a catalog selection.
            self.failUnless(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(prefix="Sam"))
            self.failUnless(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(prefix="Sam", ilk="class"))
            self.failIf(("class", "SampleClass")
                in catalog_lib.toplevel_cplns(prefix="Sam", ilk="function"))
            self.failIf(("function", "sample_func")
                in catalog_lib.toplevel_cplns(prefix="Sam"))

        self._check_db()



class StdLibTestCase(DBTestCase):

    def test_python(self):
        stdlib = self.mgr.db.get_stdlib("Python")
        self.failUnless(stdlib.has_blob("os"))
        self.failUnless(stdlib.has_blob("os.path"))
        self.failUnless(stdlib.has_blob("sys"))
        self.failUnless(stdlib.has_blob("gc"))
        self.failUnless(stdlib.has_blob("xml.dom"))
        self.failUnless(stdlib.has_blob("mmap"))
        builtin = stdlib.get_blob("*")
        self.failIf("license" in builtin.names)
        self.failUnless("dir" in builtin.names)

        stdlib25 = self.mgr.db.get_stdlib("Python", "2.5")
        self.failUnless(stdlib25.has_blob("xml.etree"))
        self.failUnless(stdlib25.has_blob("hashlib"))
        self.failUnless(stdlib25.has_blob("operator"))
        self.failUnless(stdlib25.has_blob("math"))
        self.failUnless(stdlib25.has_blob("cmath"))
        self.failUnless(stdlib25.has_blob("time"))

        self._check_db()

    def _do_test_perl_version(self, ver):
        stdlib = self.mgr.db.get_stdlib("Perl", ver)
        self.failUnless(stdlib.has_blob("*"))
        self.failUnless(stdlib.has_blob("CGI"))
        self.failUnless(stdlib.has_blob("LWP"))
        self.failUnless(stdlib.has_blob("AutoLoader"))
        self.failUnless(stdlib.has_blob("XML::Simple"))
        builtins = stdlib.get_blob("*")
        self.failUnless("-f" in builtins.names)
        self.failUnless("atan2" in builtins.names)
        self.failUnless("flock" in builtins.names)
        self._check_db()

    def test_perl(self):
        self._do_test_perl_version(None)

    def test_perl_58(self):
        self._do_test_perl_version("5.8")

    def test_perl_510(self):
        self._do_test_perl_version("5.10")

    def test_perl_512(self):
        self._do_test_perl_version("5.12")

    def test_ruby(self):
        stdlib = self.mgr.db.get_stdlib("Ruby")
        self.failUnless(stdlib.has_blob("*"))
        self.failUnless(stdlib.has_blob("cgi"))
        self.failUnless(stdlib.has_blob("cgi/session"))
        self._check_db()

    @tag("bug57037", "bug63217")
    def test_javascript(self):
        stdlib = self.mgr.db.get_stdlib("JavaScript")
        self.failUnless(stdlib.has_blob("*"))
        builtin = stdlib.get_blob("*")

        self.failUnless("Object" in builtin.names)
        self.failUnless("String" in builtin.names)
        self.failUnlessEqual(builtin.names["String"].tag, "scope") # bug 57037 
        self.failUnless("RegExp" in builtin.names)
        self.failUnless("window" in builtin.names)

        window_class = builtin.names["Window"]
        self.failUnless("alert" in window_class.names)
        self.failUnless("dump" in window_class.names)

        # bug 63217 
        object_class = builtin.names["Object"]
        for name in "toString toLocaleString valueOf".split():
            self.failUnless(name in object_class.names,
                "JavaScript 'Object' class has no '%s' attribute" % name)

        self._check_db()

    @tag("javascript")
    def test_toplevelname_index(self):
        # toplevelname_index: {ilk -> toplevelname -> blobnames}
        stdlib = self.mgr.db.get_stdlib("JavaScript")
        toplevelname_index = stdlib.toplevelname_index
        self.failUnless("Document" in toplevelname_index["class"])
        self.failUnless("*" in toplevelname_index["class"]["Document"])
        self.failUnless("window" in toplevelname_index["variable"])
        self.failUnless("eval" in toplevelname_index["function"])

        self._check_db()

    @tag("knownfailure", "toddw")
    def test_javascript_notinspec(self):
        stdlib = self.mgr.db.get_stdlib("JavaScript")
        builtin = stdlib.get_blob("*")

        self.failUnless("XMLHttpRequest" in builtin.names)
        self.failUnless("abort" in builtin.names)

        self._check_db()

    def test_php(self):
        builtin44 = self.mgr.db.get_stdlib("PHP", "4.4").get_blob("*")
        builtin53 = self.mgr.db.get_stdlib("PHP", "5.3").get_blob("*")
        builtin54 = self.mgr.db.get_stdlib("PHP", "5.4").get_blob("*")
        builtin55 = self.mgr.db.get_stdlib("PHP", "5.5").get_blob("*")
        # builtin should be the latest, i.e. PHP 5.5
        builtin   = self.mgr.db.get_stdlib("PHP").get_blob("*")

        # IMG_BOX constant was added in PHP 5.5
        self.failIf("IMG_BOX" in builtin44.names)
        self.failIf("IMG_BOX" in builtin53.names)
        self.failIf("IMG_BOX" in builtin54.names)
        self.failUnless("IMG_BOX" in builtin55.names)
        self.failUnless("IMG_BOX" in builtin.names)

        # password_hash function was added in PHP 5.5
        self.failIf("password_hash" in builtin44.names)
        self.failIf("password_hash" in builtin53.names)
        self.failIf("password_hash" in builtin54.names)
        self.failUnless("password_hash" in builtin55.names)
        self.failUnless("password_hash" in builtin.names)

        # php_logo_guid function was removed in PHP 5.5
        self.failUnless("php_logo_guid" in builtin53.names)
        self.failUnless("php_logo_guid" in builtin54.names)
        self.failIf("php_logo_guid" in builtin55.names)
        self.failIf("php_logo_guid" in builtin.names)

        # http_response_code function was added in PHP 5.4
        self.failIf("http_response_code" in builtin44.names)
        self.failIf("http_response_code" in builtin53.names)
        self.failUnless("http_response_code" in builtin54.names)
        self.failUnless("http_response_code" in builtin55.names)
        self.failUnless("http_response_code" in builtin.names)

        # define_syslog_variables function was removed in PHP 5.4
        self.failUnless("define_syslog_variables" in builtin53.names)
        self.failIf("define_syslog_variables" in builtin54.names)
        self.failIf("define_syslog_variables" in builtin55.names)
        self.failIf("define_syslog_variables" in builtin.names)

        self.failIf("PDO" in builtin44.names) # only in >=5.1
        self.failIf("simplexml_load_file" in builtin44.names) # only in >=5.0

        self._check_db()

    @tag("bug58387")
    def test_php_isset(self):
        # Brought up by Alex Fernandez on komodo-beta list for k4b1.
        builtin = self.mgr.db.get_stdlib("PHP").get_blob("*")
        self.failUnless("isset" in builtin.names)


class MultiLangLibTestCase(DBTestCase):
    test_dir = join(os.getcwd(), "tmp")
    _ci_db_import_everything_langs = set(["JavaScript", "PHP"])

    def test_scanning_error(self):
        # Hack into the Ruby multilang scanner so we can get RHTML
        # scanning to fail in controlled ways.
        ruby_cile_driver = self.mgr.citadel.cile_driver_from_lang("Ruby")
        orig_scan_multilang = ruby_cile_driver.scan_multilang
        def destructo_scan_multilang(buf, csl_cile_driver=None, css_cile_driver=None):
            if buf.accessor.text == "go boom":
                raise CodeIntelError("boom")
            elif buf.accessor.text == "go crazy":
                raise OSError("crazy")
            else:
                return orig_scan_multilang(buf, csl_cile_driver, css_cile_driver)
        ruby_cile_driver.scan_multilang = destructo_scan_multilang

        path = join(self.test_dir, "test_scanning_error.rhtml")
        writefile(path, dedent("""
            <% def spitit
                "word"
               end %>
        """))

        buf = self.mgr.buf_from_path(path, "RHTML")
        buf.unload()
        buf.scan(skip_scan_time_check=True)
        self.failUnless(buf.scan_error is None)
        blob = buf.blob_from_lang["Ruby"]
        self.failUnless("spitit" in blob.names)

        # Test CILE raising CodeIntelError
        buf.accessor.reset_content("go boom")
        buf.scan(skip_scan_time_check=True)
        self.failUnless(buf.scan_error is not None)
        self.failUnless("boom" in buf.scan_error)

        buf.scan(skip_scan_time_check=True)
        scan_time, scan_error, blob_from_lang \
            = self.mgr.db.get_buf_data(buf)
        self.failUnless(scan_time == buf.scan_time)
        self.failUnless(scan_error == buf.scan_error,
            "scan_error from db doesn't match that from the buffer after "
            "a buf.load():\n"
            "  scan_error (from db):\n"
            "    %s\n"
            "  buf.scan_error:\n"
            "    %s"
            % (scan_error, buf.scan_error))
        self.failUnless("Ruby" in blob_from_lang)
        new_blob = blob_from_lang["Ruby"]
        self.failUnless("spitit" in new_blob.names)

        # Test CILE raising some other exception.
        class FilterOutMatches(logging.Filter):
            def __init__(self, pattern):
                self.pattern = pattern
                self.filtered_out = []
            def filter(self, record):
                if self.pattern in record.msg:
                    self.filtered_out.append(record)
                    return False
                return True

        citadel_log = logging.getLogger("codeintel.citadel")
        filter = FilterOutMatches(basename(path))
        citadel_log.addFilter(filter)
        try:
            buf.accessor.reset_content("go crazy")
            buf.scan(skip_scan_time_check=True)
            self.failUnless(buf.scan_error is not None)
            self.failUnless("crazy" in buf.scan_error)
        finally:
            citadel_log.removeFilter(filter)
        if not _xpcom_:
            # When running in XPCOM, it uses a different logging mechanism, so
            # this test would fail there.
            self.failUnless(len(filter.filtered_out))

        buf.scan(skip_scan_time_check=True)
        scan_time, scan_error, blob_from_lang \
            = self.mgr.db.get_buf_data(buf)
        self.failUnless(scan_time == buf.scan_time)
        self.failUnless(scan_error == buf.scan_error,
            "scan_error from db doesn't match that from the buffer after "
            "a buf.load():\n"
            "  scan_error (from db):\n"
            "    %s\n"
            "  buf.scan_error:\n"
            "    %s"
            % (scan_error, buf.scan_error))
        self.failUnless("Ruby" in blob_from_lang)
        new_blob = blob_from_lang["Ruby"]
        self.failUnless("spitit" in new_blob.names)

    def test_php_multilevel_imports(self):
        test_dir = join(self.test_dir, "php-multilevel-imports")
        manifest = [
            ("whiz.php", "<?php echo('whiz.php'); ?>"),
            ("foo.inc", "<?php echo('foo.inc'); ?>"),
            ("foo/boom.php", "<?php echo('foo/boom.php'); ?>"),
            ("foo/bar.module", "<?php echo('foo/bar.module'); ?>"),
            ("foo/bar/bang.inc", "<?php echo('foo/bar/bang.inc'); ?>"),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        lib = self.mgr.db.get_lang_lib("PHP", "testdirlib", [test_dir], "PHP")
        for name in ("whiz.php", "foo.inc", "foo/boom.php",
                     "foo/bar.module", "foo/bar/bang.inc"):
            log.info("---- %s ----", name)
            self.failUnless(lib.has_blob(name))

        # Check again, should be in cache this time (different code
        # path).
        for name in ("whiz.php", "foo.inc", "foo/boom.php",
                     "foo/bar.module", "foo/bar/bang.inc"):
            log.info("---- %s ----", name)
            self.failUnless(lib.has_blob(name))

    def failUnlessIn(self, indexable, keys, *args):
        """Fail unless lookup of the given sequence of keys succeeds."""
        part = indexable
        try:
            for key in keys:
                part = part[key]
        except KeyError:
            self.fail(*args)
    def failIfIn(self, indexable, keys, *args):
        """Fail if lookup of the given sequence of keys succeeds."""
        part = indexable
        try:
            for key in keys:
                part = part[key]
        except KeyError:
            pass
        else:
            self.fail(*args)

    def test_toplevelname_index(self):
        # Setup test case.
        lang = "PHP"
        test_dir = join(self.test_dir, "toplevelname_index")
        manifest = [
            (join(test_dir, "foo.php"),
             "<?php global $foo_var = 42;\nfunction foo_func() { }\n ?>"),
            (join(test_dir, "bar.php"),
             "<?php global $bar_var = 42;\nfunction bar_func() { }\n ?>"),
        ]
        foo_php, foo_content = manifest[0]
        bar_php, bar_content = manifest[1]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        bar_buf = self.mgr.buf_from_path(bar_php, lang=lang)
        bar_buf.scan(skip_scan_time_check=True)
        foo_buf = self.mgr.buf_from_path(foo_php, lang=lang)
        foo_buf.scan(skip_scan_time_check=True)
        langlib = self.mgr.db.get_lang_lib(lang, "test_toplevelname_index",
                                           [test_dir], lang)
        lang_zone = langlib.lang_zone

        # Test away...
        # - This will fail if toplevelname_index wasn't created.
        toplevelname_index = lang_zone.load_index(test_dir, "toplevelname_index")

        self.failUnless("foo.php" in toplevelname_index._on_deck,
                        "recent 'foo.php' change isn't on-deck in "
                        "toplevelname_index")
        self.failIfIn(toplevelname_index._data,
            (lang, "variable", "foo_var"),
            "'PHP/foo_var' in 'toplevelname_index._data' and shouldn't be")
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var"))
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var", ilk="variable"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var", (), ilk="function"))
        self.failUnlessIn(toplevelname_index.data,
            (lang, "variable", "foo_var"),
            "'toplevelname_index.data' property did not merge on-deck")

        # - Change foo.php to ensure gets put back on-deck and removed
        #   from '_data'.
        foo_content = foo_content.replace("foo_func", "foo_func2")
        foo_buf.accessor.reset_content(foo_content)
        foo_buf.scan()
        foo_buf.scan(skip_scan_time_check=True)
        self.failUnless("foo.php" in toplevelname_index._on_deck,
                        "recent 'foo.php' change isn't on-deck in "
                        "toplevelname_index")
        self.failIfIn(toplevelname_index._data,
            (lang, "variable", "foo_var"),
            "'PHP/foo_var' in 'toplevelname_index._data' and shouldn't be")
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var", ()))
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var", (), ilk="variable"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var", (), ilk="function"))
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func2", ()))
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func2", (), ilk="function"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func2", (), ilk="variable"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func2", (), ilk="class"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func2", (), ilk="booga booga"))

        # - Make another change (before foo.php was merged in) to make
        # sure no heavy work is done.
        foo_content = foo_content.replace("foo_func2", "foo_func3")
        foo_buf.accessor.reset_content(foo_content)
        foo_buf.scan()
        foo_buf.scan(skip_scan_time_check=True)
        self.failUnless("foo.php" in toplevelname_index._on_deck,
                        "recent 'foo.php' change isn't on-deck in "
                        "toplevelname_index")
        self.failIfIn(toplevelname_index._data,
            (lang, "variable", "foo_var"),
            "'PHP/foo_var' in 'toplevelname_index._data' and shouldn't be")
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var", ()))
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var", (), ilk="variable"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var", (), ilk="function"))
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func3", ()))
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func3", (), ilk="function"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func3", (), ilk="variable"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func3", (), ilk="class"))
        self.failIf("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func3", (), ilk="booga booga"))

        # Make sure manual merging works.
        toplevelname_index.merge()
        self.failIf("foo.php" in toplevelname_index._on_deck,
                    "recent 'foo.php' change is still on-deck after merge")
        self.failUnlessIn(toplevelname_index._data,
            (lang, "variable", "foo_var"),
            "'PHP/foo_var' in 'toplevelname_index._data' and shouldn't be")
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_var"))
        self.failUnless("foo.php" in toplevelname_index.get_blobnames(
            lang, "foo_func3", ilk="function"))

        # Check that removal of a buffer results in proper removal from
        # toplevelname_index.
        foo_buf.unload()
        self.failIf("foo.php" in toplevelname_index._on_deck,
                    "recent 'foo.php' removal is on-deck and shouldn't be")
        self.failIfIn(toplevelname_index._data, (lang, "variable", "foo_var"))
        self.failIfIn(toplevelname_index.data, (lang, "variable", "foo_var"))


class PythonLangLibTestCase(DBTestCase):
    """Test the db/$lang/... part of the database."""
    test_dir = join(os.getcwd(), "tmp", "pylanglib")

    def test_updating(self):
        lang = "Python"

        blobname = "foo_updating"
        foo_py = join(self.test_dir, blobname + ".py")
        writefile(foo_py, dedent("""
            def whiz(): pass
            class Boom: pass
            bang = 42
        """))

        buf = self.mgr.buf_from_path(foo_py, "Python")
        buf.unload()
        buf.scan(skip_scan_time_check=True)

        lib = self.mgr.db.get_lang_lib(lang, "test_updating lib",
                                       [self.test_dir])
        self.failUnless(lib.has_blob(blobname))
        blob = lib.get_blob(blobname)
        #ET.dump(blob)
        self.assertEqual(blob.get("lang"), lang)
        self.assertEqual(blob.get("name"), blobname)
        self.assertEqual(blob.get("ilk"), "blob")
        self.assertEqual(blob[0].get("ilk"), "function")
        self.assertEqual(blob[0].get("name"), "whiz")
        self.assertEqual(blob[1].get("ilk"), "class")
        self.assertEqual(blob[1].get("name"), "Boom")
        self.assertEqual(blob[2].tag,         "variable")
        self.assertEqual(blob[2].get("name"), "bang")

        buf.unload()
        self.failIf(lib.has_blob_in_db(blobname))

        # .has_blob() and .get_blob() should automatically scan in
        # if necessary.
        self.failUnless(lib.has_blob(blobname))
        buf.unload()
        self.failUnless(lib.get_blob(blobname))

        self._check_db()

class LangLibTestCase(DBTestCase):
    """Test the db/$lang/... part of the database."""
    test_dir = join(os.getcwd(), "tmp")

    def test_scanning_error(self):
        path = join(self.test_dir, "test_scanning_error.py")
        writefile(path, dedent("""
            def whiz():
                pass
            class Boom:
                pass
            bang = 42
        """))

        buf = self.mgr.buf_from_path(path, "Python")
        buf.unload()
        buf.scan(skip_scan_time_check=True)

        self.failUnless(buf.scan_error is None)
        blob = buf.blob_from_lang["Python"]
        self.failUnless("whiz" in blob.names)

        new_content = dedent("""
            def oops whiz():
                pass
            class Boom:
                pass
            bang = 42
        """)
        buf.accessor.reset_content(new_content)
        buf.scan(skip_scan_time_check=True)
        self.failUnless(buf.scan_error is not None)

        buf.scan(skip_scan_time_check=True)
        scan_time, scan_error, blob_from_lang = self.mgr.db.get_buf_data(buf)
        self.failUnless(scan_time == buf.scan_time)
        self.failUnless(scan_error == buf.scan_error,
            "scan_error from db doesn't match that from the buffer after "
            "a buf.load():\n"
            "  scan_error (from db):\n"
            "    %s\n"
            "  buf.scan_error:\n"
            "    %s"
            % (scan_error, buf.scan_error))
        self.failUnless("Python" in blob_from_lang)
        new_blob = blob_from_lang["Python"]
        self.failUnless("whiz" in new_blob.names)

    def test_scan_error_rescanning(self):
        # Ensure that an "importable" (according to
        # ImportHandler.find_importables_in_dir()) doesn't continually get
        # re-scanned if it isn't changing.
        path = join(self.test_dir, "test_scan_error_rescanning.py")
        writefile(path, dedent("""
            def oops whiz():
                pass
            class Boom:
                pass
            bang = 42
        """))

        def counting_scan_purelang(self, *args, **kwargs):
            if not hasattr(self, "scan_count"):
                self.scan_count = 0
            self.scan_count += 1
            return self.old_scan_purelang(*args, **kwargs)

        lib = self.mgr.db.get_lang_lib("Python", "testlib", [dirname(path)])
        # This one may scan it, if not already in the db.
        self.failIf( lib.has_blob("test_scan_error_rescanning") )

        # This `lib.has_blob(...)' call must NOT scan it.
        cile_driver = self.mgr.citadel.cile_driver_from_lang("Python")
        cile_driver_class = cile_driver.__class__
        cile_driver_class.old_scan_purelang = cile_driver_class.scan_purelang
        cile_driver_class.scan_purelang = counting_scan_purelang
        try:
            lib.has_blob("test_scan_error_rescanning")
            self.failIf(hasattr(cile_driver, "scan_count"),
                "Didn't expected our tweaked CILE driver, %r, to have a "
                "`scan_count` attribute, but it does!" % cile_driver)
        finally:
            cile_driver_class.scan_purelang = cile_driver_class.old_scan_purelang
            if hasattr(cile_driver, "scan_count"):
                del cile_driver.scan_count
            del cile_driver_class.old_scan_purelang

    #TODO: test this for PHP (i.e. MultiLangLib) as well
    @tag("javascript")
    def test_hits_from_lpath(self):
        # A *very* simple test that hits_from_lpath is basically working
        # (for JavaScript, at least).
        test_dir = join(self.test_dir, "langlib_hits_from_lpath")
        lang = "JavaScript"
        foo_js = join(test_dir, "foo.js")
        writefile(foo_js, dedent("""
            var foo = 42;
            function bar() {
            }
        """))
        foo_buf = self.mgr.buf_from_path(foo_js, lang=lang)

        langlib = self.mgr.db.get_lang_lib(lang, "test_hits_from_lpath_lib",
                                           [test_dir])
        self.failUnless( langlib.hits_from_lpath(("bar",)) )

    ##TODO
    #def test_toplevelprefix_index(self):
    #    XXX

    def test_toplevelname_index(self):
        # Setup test case.
        lang = "JavaScript"
        test_dir = join(self.test_dir, "toplevelname_index")
        manifest = [
            (join(test_dir, "foo.js"),
             "var foo_var = 42;\nfunction foo_func() { }"),
            (join(test_dir, "bar.js"),
             "var bar_var = 42;\nfunction bar_func() { }"),
        ]
        foo_js, foo_content = manifest[0]
        bar_js, bar_content = manifest[1]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)
        bar_buf = self.mgr.buf_from_path(bar_js, lang=lang)
        bar_buf.scan(skip_scan_time_check=True)
        foo_buf = self.mgr.buf_from_path(foo_js, lang=lang)
        foo_buf.scan(skip_scan_time_check=True)
        langlib = self.mgr.db.get_lang_lib(lang, "test_toplevelname_index",
                                           [test_dir])
        lang_zone = langlib.lang_zone

        # Test away...
        # - This will fail if toplevelname_index wasn't created.
        toplevelname_index = lang_zone.load_index(test_dir, "toplevelname_index")

        self.failUnless("foo.js" in toplevelname_index._on_deck,
                        "recent 'foo.js' change isn't on-deck in "
                        "toplevelname_index")
        self.failIf("foo_var" in toplevelname_index._data.get("variable", ()))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_var"))
        self.failIf("foo.js" in toplevelname_index.get_blobnames(
            "foo_var", (), ilk="function"))
        self.failUnless("foo_var" in toplevelname_index.data["variable"],
                "'toplevelname_index.data' property did not merge on-deck")
        self.failUnless("foo_func" in toplevelname_index.data["function"],
                "'toplevelname_index.data' property did not merge on-deck")

        # - Change foo.js to ensure gets put back on-deck and removed
        #   from '_data'.
        foo_content = foo_content.replace("foo_func", "foo_func2")
        foo_buf.accessor.reset_content(foo_content)
        foo_buf.scan()
        foo_buf.scan(skip_scan_time_check=True)
        self.failUnless("foo.js" in toplevelname_index._on_deck,
                        "recent 'foo.js' change isn't on-deck in "
                        "toplevelname_index")
        self.failIf("foo_var" in toplevelname_index._data.get("variable", ()))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_var"))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_func2"))

        # - Make another change (before foo.js was merged in) to make
        # sure no heavy work is done.
        foo_content = foo_content.replace("foo_func2", "foo_func3")
        foo_buf.accessor.reset_content(foo_content)
        foo_buf.scan()
        foo_buf.scan(skip_scan_time_check=True)
        self.failUnless("foo.js" in toplevelname_index._on_deck,
                        "recent 'foo.js' change isn't on-deck in "
                        "toplevelname_index")
        self.failIf("foo_var" in toplevelname_index._data.get("variable", ()))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_var"))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_func3"))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_func3", ilk="function"))

        # Make sure manual merging works.
        toplevelname_index.merge()
        self.failIf("foo.js" in toplevelname_index._on_deck,
                    "recent 'foo.js' change is still on-deck after merge")
        self.failUnless("foo_var" in toplevelname_index._data.get("variable", ()))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_var"))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_func3"))
        self.failUnless("foo.js" in toplevelname_index.get_blobnames(
            "foo_func3", ilk="function"))
        
        # Check that removal of a buffer results in proper removal from
        # toplevelname_index.
        foo_buf.unload()
        self.failIf("foo.js" in toplevelname_index._on_deck,
                    "recent 'foo.js' removal is on-deck and shouldn't be")
        self.failIf("foo_var" in toplevelname_index._data.get("variable", ()))
        self.failIf("foo_var" in toplevelname_index.data.get("variable", ()))


    #XXX test: load a file, assert it is there with proper data,
    #          change it, rescan it, assert the db was updated

    #XXX test a lot of the above for all languages

    #XXX test: db.{get|remove|update}_buf_data() funcs

    #XXX test: scan-time skipping should happen when it should

    #XXX test corruption: db.get_buf_data() when entry in res_index
    #    but not in dbfile_from_blobname. Or the dbfile doesn't
    #    exist. Must first decide how *want* to react to this.

    #XXX test fs: Want to be able to hook in to fs-log and ensure
    #    that no fs writing is done for certain usages.

    @tag("knownfailure")
    def test_python_binary_modules(self):
        lang = "Python"
        bin_py = join(self.test_dir, "binary.py")
        writefile(bin_py, dedent("""
            between = 'Scylla and Charybdis'
            def to_be_or_not_to_be(): pass
            class Dilemma: pass
        """))
        import compileall
        compileall.compile_dir(self.test_dir)
        os.remove(bin_py)
        
        bin_pyc = bin_py + 'c'
        
        import_handler = self.mgr.import_handler_class_from_lang['Python'](self.mgr)
        files = list(import_handler.find_importables_in_dir(self.test_dir))
        
        self.failUnless('binary' in files)
        
        libs = self.mgr.db.get_lang_lib(lang, "curdirlib", [self.test_dir])
        ctrl = LogEvalController()
        blob = import_handler.import_blob_name("binary", [libs], ctrl)
        self.failIf(blob is None)
        del blob

        log.info("assert that 'binary' is in %s", libs)
        self.failUnless(libs.has_blob("binary"))
        self.failUnless(libs.get_blob("binary") is not None)

        self._check_db()

    @tag("knownfailure")
    def test_python_so_modules(self):
        import cmath, shutil
        dir = os.path.dirname(cmath.__file__)
        #ext = os.path.splitext(mod_path)[1]
        #path = os.path.join(self.test_dir, 'xmath' + ext)
        #shutil.copyfile(mod_path, path)
        
        import_handler = self.mgr.import_handler_class_from_lang['Python'](self.mgr)
        files = list(import_handler.find_importables_in_dir(dir))
        
        self.failUnless('cmath' in files)
        
        libs = self.mgr.db.get_lang_lib("Python", "curdirlib", [dir])
        ctrl = LogEvalController()
        blob = import_handler.import_blob_name("cmath", [libs], ctrl)
        self.failIf(blob is None)
        del blob

        log.info("assert that 'cmath' is in %s", libs)
        self.failUnless(libs.has_blob("cmath"))
        self.failUnless(libs.get_blob("cmath") is not None)

        self._check_db()

    def test_python(self):
        lang = "Python"
        dad_py = join(self.test_dir, "dad.py")
        writefile(dad_py, dedent("""
            name = 'George'
            surname = 'Bush'
        """))
        dad_buf = self.mgr.buf_from_path(dad_py, lang=lang)

        son_py = join(self.test_dir, "son.py")
        writefile(son_py, dedent("""
            import dad
            name = 'George W.'
            surname = dad.surname
        """))
        son_buf = self.mgr.buf_from_path(son_py, lang=lang)

        # Ensure neither is in the db to start
        log.info("unload dad.py and son.py from db")
        dad_buf.unload()
        son_buf.unload()

        # Get a handler for a Python library for just the test dir
        # This is akin to getting a lib for all the sitelib dirs,
        # or all the dirs on PYTHONPATH (envlib).
        lib = self.mgr.db.get_lang_lib(lang, "testdirlib",
                                       [self.test_dir])
        # This should discover that "son.py" exists in the test dir
        # and hence must be scanned and loaded, if not already. 
        log.info("assert that 'son' and 'dad' blobs in %s", lib)
        self.failUnless(lib.has_blob("son"))
        self.failUnless(lib.has_blob("dad"))
        self.failUnless(lib.get_blob("son") is not None)

        self._check_db()

    @tag("perl", "bug88826")
    def test_perl_multilevel_imports(self):
        test_dir = join(self.test_dir, "perl-multi-level-imports")
        manifest = [
            ("Foo.pm",
             "package Foo;\nprint 'Foo';\n1;"),
            ("Foo/SubFoo.pm",
             "package Foo::SubFoo;\nprint 'Foo::SubFoo';\n1;"),
            ("Bar/SubBar.pm",
             "package Bar::SubBar;\nprint 'Bar::SubBar';\n1;"),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        lib = self.mgr.db.get_lang_lib("Perl", "testdirlib", [test_dir])
        for name in ("Foo", "Foo::SubFoo", "Bar::SubBar"):
            log.info("---- %s ----", name)
            self.failUnless(lib.has_blob(name))

        # Check again, should be in cache this time (different code
        # path).
        for name in ("Foo", "Foo::SubFoo", "Bar::SubBar"):
            log.info("---- %s ----", name)
            self.failUnless(lib.has_blob(name))

        for name in ("Bar",):
            log.info("---- %s ----", name)
            self.failIf(lib.has_blob(name))

    def test_python_multilevel_imports(self):
        test_dir = join(self.test_dir, "python-multi-level-imports")
        manifest = [
            ("whiz.py", "print 'whiz'"),
            ("foo/__init__.py", "print 'foo'"),
            ("foo/boom.py", "print 'foo.boom'"),
            ("foo/bar/__init__.py", "print 'foo.bar'"),
            ("foo/bar/bang.py", "print 'foo.bar.bang'"),
        ]
        for file, content in manifest:
            path = join(test_dir, file)
            writefile(path, content)

        lib = self.mgr.db.get_lang_lib("Python", "testdirlib", [test_dir])
        for name in ("whiz", "foo", "foo.boom", "foo.bar", "foo.bar.bang"):
            log.info("---- %s ----", name)
            self.failUnless(lib.has_blob(name))

        # Check again, should be in cache this time (different code
        # path).
        for name in ("whiz", "foo", "foo.boom", "foo.bar", "foo.bar.bang"):
            log.info("---- %s ----", name)
            self.failUnless(lib.has_blob(name))

    def test_curdirlib_abs_dir(self):
        # The dir for "curdirlib" (and other libs) for a buffer should
        # be absolute, even if the given buf path is relative.
        test_dir = join(self.test_dir, "curdirlib-abs-dir")
        path = join(test_dir, "foo.py")
        writefile(path, "print 'hi'")
        rpath = relpath(path, os.getcwd())

        if isabs(rpath):
            self.fail("cannot perform this test if test_dir (%s) cannot be "
                      "made relative to the current dir (%s)"
                      % (test_dir, os.getcwd()))
        buf = self.mgr.buf_from_path(rpath)
        curdirlib = [lib for lib in buf.libs if lib.name == "curdirlib"][0]
        self.failUnless(isabs(curdirlib.dirs[0]),
            "the dir for %s's 'curdirlib' is not absolute: %s"
            % (buf, curdirlib.dirs[0]))


    #XXX Multi-thread test:
    #    Updating a langlib can happen in a separate thread. Need a
    #    test that has one (or more) thread getting results from
    #    the lib and one (or more) thread updating the db (add,
    #    remove, delete). Hit is hard and make sure all updates are
    #    as expected.
    #
    #XXX Do this for other langs as well (e.g. Perl: "Foo::Bar"). Do
    #    we want to force the langs to convert to use '.'? Would
    #    be nice to adjust per-lang. Import handlers should know
    #    how to deal with this and should abstract the details.
    #XXX Add a test where it *looks* like the lib should have
    #    a blob but when the file, e.g. son.py, is actually scanned
    #    it cannot be loaded because it had bogus content. Should
    #    fail gracefully for that case. Cpln *eval* should fail
    #    gracefully for that case.


class ProjTestCase(DBTestCase):
    """Test the db/proj/... part of the database."""
    test_dir = join(os.getcwd(), "tmp")

    def test_onedir(self):
        proj_dir = "proj-onedir"
        manifest = [
            (proj_dir+"/foo.py", dedent("""
                import bar
                bar.Bar
             """)),
            (proj_dir+"/bar.py", dedent("""
                class Bar: pass
             """)),
        ]
        for file, content in manifest:
            path = join(self.test_dir, file)
            writefile(path, content)

        db = self.mgr.db
        foo_proj = join(self.test_dir, proj_dir, "foo.proj")
        proj = MockProject(foo_proj)
        proj_zone = db.get_proj_zone(proj)
        proj_zone.update()
        lib = proj_zone.get_lib("Python")

        self.failUnless(lib.has_blob("foo"))
        self.failUnless(lib.has_blob("bar"))
        bar = lib.get_blob("bar")
        self.failUnlessEqual((bar[0].get("ilk"), bar[0].get("name")),
                             ("class",           "Bar"))
        self._check_db()
    
    def test_twodirs(self):
        proj_dir = "proj-twodirs"
        manifest = [
            (proj_dir+"/f/foo.py", dedent("""
                import bar
                bar.Bar
             """)),
            (proj_dir+"/b/bar.py", dedent("""
                class Bar: pass
             """)),
        ]
        for file, content in manifest:
            path = join(self.test_dir, file)
            writefile(path, content)

        db = self.mgr.db
        foo_proj = join(self.test_dir, proj_dir, "foo.proj")
        proj = MockProject(foo_proj)
        proj_zone = db.get_proj_zone(proj)
        proj_zone.update()
        lib = proj_zone.get_lib("Python")

        self.failUnless(lib.has_blob("foo"))
        self.failUnless(lib.has_blob("bar"))
        bar = lib.get_blob("bar")
        self.failUnlessEqual((bar[0].get("ilk"), bar[0].get("name")),
                             ("class",           "Bar"))
        self._check_db()


class MockProject(object):
    def __init__(self, path, base_dir=None):
        self.path = path
        self._base_dir = base_dir

    @property
    def base_dir(self):
        if self._base_dir is not None:
            return self._base_dir
        else:
            return dirname(self.path)
        
class CSSTestCase(DBTestCase):
    css_test_dir = join(os.getcwd(), "tmp", "css")
    less_test_dir = join(os.getcwd(), "tmp", "less")
    scss_test_dir = join(os.getcwd(), "tmp", "scss")
    
    def test_css_import_handler(self):
        """
        Tests that the CSS import handler loads all CSS files from a directory,
        including nested CSS files. This test has the following folder
        structure:
        
        css/
            foo.css
            bar.css
            nested/
                baz.css
    
        Each CSS file contains an id selector followed by a class selector.
        This test verifies that all 3 CSS files have been loaded and scanned.
        """
        writefile(join(self.css_test_dir, "foo.css"), "#foo { }\n.foobar { }\n")
        writefile(join(self.css_test_dir, "bar.css"), "#bar { }\n.barfoo { }\n")
        writefile(join(self.css_test_dir, "nested", "baz.css"), "#baz { }\n.bazfoo { }\n")
        import_handler = self.mgr.citadel.import_handler_from_lang("CSS")
        importables = import_handler.find_importables_in_dir(self.css_test_dir)
        self.failUnless(len(importables.keys()) == 3)
        for name in ("foo.css", "bar.css", join("nested", "baz.css")):
            buf = self.mgr.buf_from_path(join(self.css_test_dir, name), lang="CSS")
            self.failUnless(buf)
            blob = buf.blob_from_lang["CSS"]
            self.failUnless(len(blob) == 2)
            self.failUnless(blob.getchildren()[0].get("ilk") == "id")
            self.failUnless(blob.getchildren()[1].get("ilk") == "class")
            
    def test_less_import_handler(self):
        """
        Identical to the above CSS test case, but with a mixture of CSS and
        Less files.
        """
        writefile(join(self.less_test_dir, "foo.less"), "#foo(@c) when (iscolor(@c)) { }\n.foobar { }\n")
        writefile(join(self.less_test_dir, "bar.css"), "#bar { }\n.barfoo { }\n")
        writefile(join(self.less_test_dir, "nested", "baz.less"), "#baz:extend(.a, .b) { }\n.bazfoo { }\n")
        import_handler = self.mgr.citadel.import_handler_from_lang("CSS")
        importables = import_handler.find_importables_in_dir(self.less_test_dir)
        self.failUnless(len(importables.keys()) == 3)
        
        buf = self.mgr.buf_from_path(join(self.less_test_dir, "foo.less"), lang="Less")
        self.failUnless(buf)
        blob = buf.blob_from_lang["Less"]
        self.failUnless(len(blob) == 2)
        self.failUnless(blob.getchildren()[0].get("ilk") == "id")
        self.failUnless(blob.getchildren()[1].get("ilk") == "class")
        
        buf = self.mgr.buf_from_path(join(self.less_test_dir, "bar.css"), lang="CSS")
        self.failUnless(buf)
        blob = buf.blob_from_lang["CSS"]
        self.failUnless(len(blob) == 2)
        self.failUnless(blob.getchildren()[0].get("ilk") == "id")
        self.failUnless(blob.getchildren()[1].get("ilk") == "class")

        buf = self.mgr.buf_from_path(join(self.less_test_dir, join("nested", "baz.less")), lang="Less")
        self.failUnless(buf)
        blob = buf.blob_from_lang["Less"]
        self.failUnless(len(blob) == 2)
        self.failUnless(blob.getchildren()[0].get("ilk") == "id")
        self.failUnless(blob.getchildren()[1].get("ilk") == "class")
            
    def test_scss_import_handler(self):
        """
        Identical to the above CSS test case, but with SCSS files.
        """
        writefile(join(self.scss_test_dir, "foo.scss"), "#foo { }\n.foobar { }\n")
        writefile(join(self.scss_test_dir, "bar.scss"), "#bar { }\n.barfoo { }\n")
        writefile(join(self.scss_test_dir, "nested", "baz.css.scss"), "#baz { }\n.bazfoo { }\n")
        import_handler = self.mgr.citadel.import_handler_from_lang("CSS")
        importables = import_handler.find_importables_in_dir(self.scss_test_dir)
        self.failUnless(len(importables.keys()) == 3)
        
        buf = self.mgr.buf_from_path(join(self.scss_test_dir, "foo.scss"), lang="SCSS")
        self.failUnless(buf)
        blob = buf.blob_from_lang["SCSS"]
        self.failUnless(len(blob) == 2)
        self.failUnless(blob.getchildren()[0].get("ilk") == "id")
        self.failUnless(blob.getchildren()[1].get("ilk") == "class")
        
        buf = self.mgr.buf_from_path(join(self.scss_test_dir, "bar.scss"), lang="SCSS")
        self.failUnless(buf)
        blob = buf.blob_from_lang["SCSS"]
        self.failUnless(len(blob) == 2)
        self.failUnless(blob.getchildren()[0].get("ilk") == "id")
        self.failUnless(blob.getchildren()[1].get("ilk") == "class")

        buf = self.mgr.buf_from_path(join(self.scss_test_dir, join("nested", "baz.css.scss")), lang="SCSS")
        self.failUnless(buf)
        blob = buf.blob_from_lang["SCSS"]
        self.failUnless(len(blob) == 2)
        self.failUnless(blob.getchildren()[0].get("ilk") == "id")
        self.failUnless(blob.getchildren()[1].get("ilk") == "class")



#---- internal support stuff



#---- mainline

if __name__ == "__main__":
    unittest.main()


