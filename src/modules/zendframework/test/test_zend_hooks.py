#!/usr/bin/env python
# Copyright (c) 2006-2008 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""Test the Zend hooks functionality in codeintel."""

import os
import sys
import re
from os.path import join, dirname, abspath, exists, basename
import unittest
from pprint import pprint
import logging
import shutil

from codeintel2.common import *
from codeintel2.util import indent, dedent, banner, markup_text, unmark_text
from codeintel2.environment import SimplePrefsEnvironment

from testlib import TestError, TestSkipped, TestFailed, tag
from citestsupport import CodeIntelTestCase, writefile



log = logging.getLogger("test.hooks.zend")


class ZendHooksTestCase(CodeIntelTestCase):
    lang = "PHP"
    test_dir = join(os.getcwd(), "tmp")
    _ci_extra_module_dirs_ = [
        join(dirname(dirname(abspath(__file__))),
             "pylib"),
    ]
    _ci_extra_path_dirs_ = [
        join(dirname(abspath(__file__)),
             "bits", "ZendFramework-1.5.2", "library", "Zend"),
    ]
    _onetime_setup_completed = False

    def setUp(self):
        # Ensure the Zend Framework is where we expect it to be, else download
        # it and make it so.
        if not ZendHooksTestCase._onetime_setup_completed:
            import urllib
            import zipfile
            #print "One time setup"
            ZendHooksTestCase._onetime_setup_completed = True
            bits_dir = join(dirname(abspath(__file__)), "bits")
            zend_dir = join(bits_dir, "ZendFramework-1.5.2")
            if not exists(zend_dir):
                zippath = "zend.zip"
                if not exists(zippath):
                    urlOpener = urllib.urlopen("http://framework.zend.com/releases/ZendFramework-1.5.2/ZendFramework-1.5.2.zip")
                    f = file(zippath, "wb")
                    f.write(urlOpener.read())
                    f.close()
                try:
                    zf = zipfile.ZipFile(zippath)
                    for zfile in zf.filelist:
                        dirpath, filename = os.path.split(zfile.filename)
                        absdirpath = join(bits_dir, dirpath)
                        #print "absdirpath: %r" % (absdirpath, )
                        if not exists(absdirpath):
                            os.makedirs(absdirpath)
                        filename = join(absdirpath, filename)
                        if not exists(filename):
                            file(filename, "wb").write(zf.read(zfile.filename))
                finally:
                    #print "Leaving zip file: %s" % (zippath)
                    os.remove(zippath)
        CodeIntelTestCase.setUp(self)

    def test_zend_view_hooks(self):
        test_dir = join(self.test_dir, "test_zend_view_hooks")
        content, positions = unmark_text(dedent("""\
            <?php if($this->values) { ?>
            <h3>You just submitted the following values:</h3>
            <ul>
              <?php foreach ($this->values as $value) :?>
              <li>
                <?= $this-><1>escape(<2>$value); ?>
              </li>
              <?php endforeach; ?>
            </ul>
            <?=
            $this->form; ?>
        """))
        phpExtraPaths = os.pathsep.join(self._ci_extra_path_dirs_)
        env = SimplePrefsEnvironment(phpExtraPaths=phpExtraPaths)

        # Test to make sure the zend hooks are only modifying the files
        # in the /view/scripts/ directories. We should *not* get the completions
        # for the above code.
        path = join(test_dir, "test_zend_view.phtml")
        writefile(path, content)
        buf = self.mgr.buf_from_path(path, lang=self.lang, env=env)
        buf.scan_if_necessary()
        self.assertCompletionsDoNotInclude2(buf, positions[1],
            [("function", "escape"),
             ("function", "render")
             ])

        # Test to make sure the zend hooks are only modifying the ".phtml" files
        # in the /view/scripts/ directories. We should *not* get the completions
        # for the above code.
        path = join(test_dir, "test_zend_view.php")
        writefile(path, content)
        buf = self.mgr.buf_from_path(path, lang=self.lang, env=env)
        buf.scan_if_necessary()
        self.assertCompletionsDoNotInclude2(buf, positions[1],
            [("function", "escape"),
             ("function", "render")
             ])

        # Now make sure we do get the completions on /view/scripts/ directories.
        path = join(test_dir, "views", "scripts", "test_zend_view.phtml")
        writefile(path, content)
        buf = self.mgr.buf_from_path(path, lang=self.lang, env=env)
        buf.scan_if_necessary()
        self.assertCompletionsInclude2(buf, positions[1],
            [("function", "escape"),
             ("function", "render")
             ])
        # Make sure we do not get completions on the added "(render)" function.
        self.assertCompletionsDoNotInclude2(buf, positions[1],
            [("function", "(render)"),
             ])

#---- mainline

if __name__ == "__main__":
    unittest.main()


