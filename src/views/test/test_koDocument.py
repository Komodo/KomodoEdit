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

import os
import sys
from hashlib import md5
import unittest
import tempfile
from os.path import abspath, dirname, join

from zope.cachedescriptors.property import Lazy as LazyProperty

import eollib
from xpcom import components, nsError, ServerException, COMException
from xpcom.server import WrapObject, UnwrapObject


class _FakeScintillaView(object):
    _com_interfaces_ = [components.interfaces.koIScintillaView]
    def __init__(self):
        self.scimoz = components.classes['@activestate.com/ISciMozHeadless;1']. \
                      createInstance(components.interfaces.ISciMoz)
    def setFoldStyle(self, val):
        pass

class _KoDocTestCase(unittest.TestCase):
    """Base class for koIDocument test cases."""
    _fileSvcCache = None
    @property
    def _fileSvc(self):
        if self._fileSvcCache is None:
            self._fileSvcCache = components.classes["@activestate.com/koFileService;1"] \
                .getService(components.interfaces.koIFileService)
        return self._fileSvcCache

    def _koDocFromPath(self, path, load=True):
        """Return an intialized `KoDocument` instance for the given path."""
        import uriparse
        uri = uriparse.localPathToURI(path)
        return self._koDocFromURI(uri, load=load)
    
    def _koDocFromURI(self, uri, load=True):
        koFile = self._fileSvc.getFileFromURI(uri)
        koDoc = components.classes["@activestate.com/koDocumentBase;1"] \
            .createInstance(components.interfaces.koIDocument)
        koDoc.initWithFile(koFile, False)
        if load:
            koDoc.load()
        view = _FakeScintillaView()
        koDoc.addView(view)
        return koDoc

    def _koDocUntitled(self):
        koDoc = components.classes["@activestate.com/koDocumentBase;1"] \
            .createInstance(components.interfaces.koIDocument)
        koDoc.initUntitled("blatz", "ASCII");
        return koDoc


class KoDocInfoDetectionTestCase(_KoDocTestCase):
    __tags__ = ["detection"]
    
    @property
    def data_dir(self):
        return join(dirname(abspath(__file__)), "detection_data")
    
    def test_basic(self):
        for name in ("exists.py", "does not exist.py"):
            koDoc = self._koDocFromPath(join(self.data_dir, name), load=False)
            self.assertEqual(koDoc.language, "Python")

    def test_recognize_perl_file(self):
        manifest = [
            (tempfile.mktemp(".pl"), "\n".join(["#!/usr/bin/env perl",
                                     "",
                                     "use strict;",
                                     "use warnings;",
                                     "",
                                     r'print "no more\n";'])),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path, load=False)
            self.assertEqual(koDoc.language, "Perl")

    def test_recognize_xbl_file(self):
        manifest = [
            (tempfile.mktemp(".xml"), r"""\
<?xml version="1.0"?>
<!-- Copyright (c) 2000-2006 ActiveState Software Inc. -->
<!-- See the file LICENSE.txt for licensing information. -->

<!DOCTYPE bindings PUBLIC "-//MOZILLA//DTD XBL V1.0//EN" "http://www.mozilla.org/xbl">

<!--
TODO:
look at mozilla\xpfe\global\resources\content\bindings\button.xml
and see if we really need *ANY* of this stuff.  I think we can
use moz bindings with CSS to acheive everything we have here.
-->

<bindings
    xmlns="http://www.mozilla.org/xbl"
    xmlns:xbl="http://www.mozilla.org/xbl"
    xmlns:html="http://www.w3.org/1999/xhtml"
    xmlns:xul="http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul">

    <!-- include our css, but inherit from mozilla's button base
         which includes access controls -->
    <binding id="button-base" extends="chrome://global/content/bindings/button.xml#button-base">
        <resources>
            <stylesheet src="chrome://komodo/skin/bindings/buttons.css"/>
        </resources>
    </binding>
  <!-- XUL <button>s -->
  <!-- used for button menus in several places
    style class: rightarrow-button -->
  <binding id="rightarrow-button" display="xul:menu"
    extends="chrome://komodo/content/bindings/buttons.xml#button-base">
    <content>
      <xul:box class="button-internal-box" align="center" pack="center" flex="1">
        <xul:image class="button-icon" xbl:inherits="src=image"/>
      </xul:box>
      <children includes="menupopup"/>
    </content>
  </binding>""")
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "XBL")

    def test_recognize_html_file(self):
        manifest = [
            (tempfile.mktemp(".html"), """\
<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01//EN" "http://www.w3.org/TR/html4/strict.dtd" [
<!ENTITY % fizz SYSTEM "/no/such/file1">
%fizz;
<!ENTITY % fizz2 SYSTEM "/no/such/file2">
&fizz2;
<!ENTITY fizz2 
]>
<html lang="en">
<head>
    <title><!-- Insert your title here --></title>
</head>
<frameset>
    <frame src="http:/blipfds/f1.html" />
</frameset>
"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "HTML")

    def test_recognize_html5_file(self):
        manifest = [
            (tempfile.mktemp(".html"), """\
<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" type="text/css" href="css/screen.css" />
  <link rel="icon" href="favicon.ico" type="image/x-icon" />
  <link rel="shortcut icon" href="favicon.ico" type= "image/x-icon" />

  <title>Abbreviations</title>
</head>
<body>
<div id="content">
  
  <h1><a name="abbrev_top" id="abbrev_top">Abbreviations</a></h1>
  
  <p>The Abbreviations function lets you quickly insert code <a
  href="snippets.html">snippets</a> by entering their name in the editor
  buffer followed by <strong>Ctrl+T</strong>. Several useful default
  snippets are included in Komodo. Additional ones can be added
  easily.</p>
   
  <p>Komodo looks for abbreviations in a special folder in projects and
  toolboxes called Abbreviations. Within the Abbreviations folder are
  language specific sub-folders, and a General sub-folder for global
  snippets.</p>
</div>""")
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "HTML5")

    def test_recognize_django_file(self):
        manifest = [
            (tempfile.mktemp(".django.html"), """\
{% extends 'layouts/base.html' %}
{%block title %} Dashboard {% endblock %}
{%block extrahead %}
<script type="text/javascript">
</script>
{% endblock %}

{% block header %}
    <div id="focus_on" class="boxshadow">
        <ul>
            <li class="title">Focus on</li>
            <li>
                <a href="." class="all{% if not status %} active{% endif %}">
                    <span class="icon"><i> </i></span>
                    <span>All</span>
                </a>
            </li>
            <li>
                <a href="?status=1" class="thing{% if status == '1' %} active{% endif %}">
                    <span class="icon"><i> </i></span>
                    <span>Things</span>
                </a>
            </li>"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "Django")

    def test_recognize_smarty_file_01(self):
        manifest = [
            (tempfile.mktemp(".tpl"), """\
<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
                      "http://www.w3.org/TR/html4/loose.dtd">
<html>
  <head>
    <title>Access Denied - ActiveState Bugs</title>
    <meta name="title" content="ActiveState Bugs - Access Denied">


<link rel="Top" href="http://bugs.activestate.com/">



    
    
    <link href="skins/standard/global.css"
          rel="alternate stylesheet" 
          title="Classic"><link href="skins/standard/global.css" rel="stylesheet"
        type="text/css" ><!--[if lte IE 7]>
      



  <link href="skins/standard/IE-fixes.css" rel="stylesheet"
        type="text/css" >
<![endif]-->
"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "Smarty")

    def test_recognize_smarty_file_02(self):
        manifest = [
            (tempfile.mktemp(".smarty.tpl"), """\
{{ hello }}
{% import 'macro/std.macro.twig' as macro_std %}"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "Smarty")

    # bug 98264
    def test_recognize_php_file_01(self):
        manifest = [
            (tempfile.mktemp(".tpl.php"), """\
{{ hello }}
{% import 'macro/std.macro.twig' as macro_std %}"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "PHP")

    def test_recognize_twig_file(self):
        manifest = [
            (tempfile.mktemp(".twig"), """\
{{ hello }}
{% import 'macro/std.macro.twig' as macro_std %}"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "Twig")

    def test_recognize_python_file(self):
        manifest = [
            (tempfile.mktemp(".py"), """\
#!/usr/bin/env python
print('should be py2')
"""),
            (tempfile.mktemp(".py"), """\
#  -*- python -*-
print('should be py2')
"""),
            (tempfile.mktemp(".py"), """\
try:
    print('should be py2')
except AttributeError, x:
    print("exception: %s", x)
"""),
            (tempfile.mktemp(".py"), """\
# no specific markers here, default to py
"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "Python")

    def test_recognize_python3_file(self):
        manifest = [
            (tempfile.mktemp(".py"), """\
#!/usr/bin/env python3
print('should be py3')
"""),
            (tempfile.mktemp(".py"), """\
#  -*- python3 -*-
print('should be py3')
"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "Python3",
                             "%r found, expected 'Python3', content %r" % (koDoc.language, content))

    def test_recognize_javascript_file(self):
        manifest = [
            (tempfile.mktemp(".js"), """\
#  -*- javascript -*-
alert('should be js')
"""),
            (tempfile.mktemp(".js"), """\
document.getElementById("should be js");
"""),
            (tempfile.mktemp(".js"), """\
alert("should be js");
"""),
            (tempfile.mktemp(".js"), """\
var x = 'no markers, default js';
"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "JavaScript")

    def test_recognize_nodejs_file(self):
        manifest = [
            (tempfile.mktemp(".js"), """\
#  -*- mode: Node.js -*-
console.log('should be node')
"""),
            (tempfile.mktemp(".js"), """\
#!/usr/bin/env node
console.log('should be node')
"""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, "Node.js",
                             "%r found, expected 'Node.js', content %r" % (koDoc.language, content))

    def test_recognize_nodejs_file_with_interpreter(self):
        # If we have a node interpreter on our path, then these will be seen as
        # Node.js files, otherwise they are seen as JavaScript files.
        manifest = [
            (tempfile.mktemp(".js"), """\
require('console');
"""),
            (tempfile.mktemp(".js"), """\
module.exports = {};
"""),
            (tempfile.mktemp(".js"), """\
foo.on('something', function(event) {
console.log(event.name);
});
"""),
        ]
        import which
        try:
            which.which("node")
            lang = "Node.js"
        except which.WhichError:
            # Could not find node interpreter.
            import logging
            log = logging.getLogger("test")
            log.warn("No node interpreter was found on the path")
            lang = "JavaScript"
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, lang,
                             "%r found, expected %r, content %r" % (koDoc.language, lang, content))

    def _mk_eol_test_files(self):
        """Create the EOL test files. Relying on SCC systems to result in
        the specific EOLs we want is brittle.
        """
        manifest = [
            ("eol_lf.py", "\n".join("one two three".split())),
            ("eol_cr.py", "\r".join("one two three".split())),
            ("eol_crlf.py", "\r\n".join("one two three".split())),
            ("eol_mixed.py", "endswith cr\rendswith crlf\r\nendswith lf\n"),
            ("eol_empty.py", ""),
        ]
        for name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
    
    def test_eol(self):
        """Test EOL detection."""
        self._mk_eol_test_files()
        EOL_LF = components.interfaces.koIDocument.EOL_LF
        EOL_CR = components.interfaces.koIDocument.EOL_CR
        EOL_CRLF = components.interfaces.koIDocument.EOL_CRLF
        EOL_MIXED = components.interfaces.koIDocument.EOL_MIXED
        EOL_NOEOL = components.interfaces.koIDocument.EOL_NOEOL
        data = [
            ("eol_lf.py", EOL_LF, EOL_LF),
            ("eol_cr.py", EOL_CR, EOL_CR),
            ("eol_crlf.py", EOL_CRLF, EOL_CRLF),
            ("eol_mixed.py", EOL_MIXED, eollib.EOL_PLATFORM),
            # `koIDocument.existing_line_endings` current impl. doesn't
            # return EOL_NOEOL. Instead it traps that value and returns
            # `new_line_endings`.
            ("eol_empty.py", eollib.EOL_PLATFORM, eollib.EOL_PLATFORM),
        ]
        for name, existing_line_endings, new_line_endings in data:
            koDoc = self._koDocFromPath(join(self.data_dir, name))
            self.assertEqual(koDoc.existing_line_endings, existing_line_endings,
                "unexpected `koDoc.existing_line_endings` value for %r: "
                "expected %r, got %r" % (
                    name, existing_line_endings, koDoc.existing_line_endings))
            self.assertEqual(koDoc.new_line_endings, new_line_endings,
                "unexpected `koDoc.new_line_endings` value for %r: "
                "expected %r, got %r" % (
                    name, new_line_endings, koDoc.new_line_endings))
    
    def test_language_reset(self):
        manifest = [
            ("Python", tempfile.mktemp(".py"), """\
#!/usr/bin/env python
print 'should be py'
"""),
            ("Python3", tempfile.mktemp(".py"), """\
#  -*- python3 -*-
print('should be py3')
"""),
            ("JavaScript", tempfile.mktemp(".js"), """\
alert('should be js')
"""),
        ]
        for lang, name, content in manifest:
            path = join(self.data_dir, name)
            _writefile(path, content)
            koDoc = self._koDocFromPath(path)
            self.assertEqual(koDoc.language, lang)
            koDoc.language = "Perl"
            self.assertEqual(koDoc.language, "Perl")
            koDoc.language = ""
            self.assertEqual(koDoc.language, lang)
            # Validate the documents preference chain - bug 97728.
            doc = UnwrapObject(koDoc)
            doc._walkPrefChain(doc.prefs, doPrint=False)


class TestKoDocumentBase(_KoDocTestCase):
    def test_createFile(self):
        text = "This is a test!"
        path = tempfile.mktemp()
        try:
            koDoc = self._koDocFromPath(path, load=False)
            koDoc.buffer = text
            koDoc.save(0)
            del koDoc
            
            koDoc2 = self._koDocFromPath(path)
            assert koDoc2.buffer == text
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up
        
    def test_revertFile(self):
        path = tempfile.mktemp()
        try:
            # Init the test file with some content.
            _writefile(path, "blah\nblah\nblah")

            koDoc = self._koDocFromPath(path)
            oldtext = koDoc.buffer
            koDoc.buffer = None
            assert not koDoc.buffer
            koDoc.revert()
            assert oldtext == koDoc.buffer
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    def test_readFile(self):
        path = tempfile.mktemp()
        try:
            # Init the test file with some content.
            _writefile(path, "blah\nblah\nblah")

            koDoc = self._koDocFromPath(path)
            assert koDoc.buffer
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    def test_readURI(self):
        url = 'http://downloads.activestate.com/'
        koDoc = self._koDocFromURI(url)
        assert koDoc.buffer

    def test_differentOnDisk(self):
        path = tempfile.mktemp()
        try:
            # Init the test file with some content.
            _writefile(path, "blah\nblah\nblah\n")

            koDoc = self._koDocFromPath(path)
            oldtext = koDoc.buffer

            _writefile(path, "blah\nblah\nblah\nblah\n")

            self.assertEqual(oldtext, koDoc.buffer)
            self.assertTrue(koDoc.differentOnDisk())
            # Next time we call it - it should be already using the latest info.
            self.assertFalse(koDoc.differentOnDisk(), "File change detected when it shouldn't be")
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    def test_changeLineEndings(self):
        path = tempfile.mktemp()
        try:
            # Init the test file with some content.
            if sys.platform.startswith('win'):
                eol = "\r\n"
            else:
                eol = "\n"
            _writefile(path, eol.join(["blah", "blah", "blah"]))

            koDoc = self._koDocFromPath(path)
            # Does the document match our platform endings?
            assert koDoc.existing_line_endings == eollib.EOL_PLATFORM
            # test converting to each of our endings
            for le in eollib.eolMappings.keys():
                koDoc.existing_line_endings = le
                assert koDoc.existing_line_endings == le
            # test converting to an invalid ending, should raise exception
            try:
                koDoc.existing_line_endings = 10
            except COMException, e:
                pass
            assert koDoc.existing_line_endings != 10
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    def test_loadUTF8File(self):
        # expects the path to be in Komodo-devel
        p = join(dirname(                             # komodo-devel
                  dirname(                            # src
                   dirname(                           # views
                    dirname((abspath(__file__)))))),  # tests
                 "test", "stuff", "charsets", "utf-8_1.html")
        utf_path = os.path.abspath(p)
        assert os.path.isfile(utf_path)
        koDoc = self._koDocFromPath(utf_path, load=False)
        koDoc.prefs.setBooleanPref('encodingAutoDetect', 1)
        koDoc.load()
        # is utf8 identified?
        assert koDoc.encoding.python_encoding_name == 'utf-8'
        assert koDoc.codePage == 65001

    def test_forceEncoding(self):
        # expects the path to be in Komodo-devel
        p = join(dirname(                             # komodo-devel
                  dirname(                            # src
                   dirname(                           # views
                    dirname((abspath(__file__)))))),  # tests
                 "test", "stuff", "charsets", "utf-8_1.html")
        utf_path = os.path.abspath(p)
        assert os.path.isfile(utf_path)
        koDoc = self._koDocFromPath(utf_path, load=False)
        koDoc.prefs.setBooleanPref('encodingAutoDetect',1)
        koDoc.load()
        koDoc.forceEncodingFromEncodingName('latin-1')
        assert koDoc.encoding.python_encoding_name == 'latin-1'
        # this is not true any longer
        #assert koDoc.codePage == 0

    def test_autoSaveFile(self):
        path = tempfile.mktemp()
        buffer = "blah\nblah\nblah"
        try:
            # Init the test file with some content.
            _writefile(path, buffer)

            koDoc = self._koDocFromPath(path)
            assert not koDoc.haveAutoSave()
            
            # test the autosave path
            doc_asfn = os.path.basename(UnwrapObject(koDoc)._getAutoSaveFileName())
            my_asfn = "%s-%s" % (md5(koDoc.file.URI).hexdigest(),koDoc.file.baseName)
            assert doc_asfn == my_asfn
            
            # document is not dirty yet
            koDoc.doAutoSave()
            assert not koDoc.haveAutoSave()
            
            # make the document dirty then save
            koDoc.isDirty = 1
            koDoc.doAutoSave()
            assert koDoc.haveAutoSave()
            
            koDoc.buffer = "tada"
            koDoc.restoreAutoSave()
            assert koDoc.buffer == buffer
            koDoc.removeAutoSaveFile()
            assert not koDoc.haveAutoSave()
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    def test_saveUntitledFile(self):
        text = "This is a test!"
        koDoc = self._koDocUntitled()
        koDoc.buffer = text
        prefs = components.classes["@activestate.com/koPrefService;1"] \
            .createInstance(components.interfaces.koIPrefService).prefs
        cleanLineEnds = prefs.getBooleanPref("cleanLineEnds")
        cleanLineEnds_CleanCurrentLine = prefs.getBooleanPref("cleanLineEnds_CleanCurrentLine")
        cleanLineEnds_ChangedLinesOnly = prefs.getBooleanPref("cleanLineEnds_ChangedLinesOnly")
        ensureFinalEOL = prefs.getBooleanPref("ensureFinalEOL")
        prefs.setBooleanPref("cleanLineEnds", True)
        prefs.setBooleanPref("cleanLineEnds_CleanCurrentLine", True)
        prefs.setBooleanPref("cleanLineEnds_ChangedLinesOnly", True)
        prefs.setBooleanPref("ensureFinalEOL", True)

        try:
            path = tempfile.mktemp()
            import uriparse
            uri = uriparse.localPathToURI(path)
            newdocument = self._koDocFromPath(path, load=False)
            newdocument.setBufferAndEncoding(koDoc.buffer, koDoc.encoding.python_encoding_name)
            newdocument.language = koDoc.language
            newdocument.save(True)
            assert os.path.exists(path)
            f = open(path)
            t = f.read()
            f.close()
            assert t == text
            os.unlink(path) # clean up
        finally:
            prefs.setBooleanPref("cleanLineEnds",
                                 cleanLineEnds)
            prefs.setBooleanPref("cleanLineEnds_CleanCurrentLine",
                                 cleanLineEnds_CleanCurrentLine)
            prefs.setBooleanPref("cleanLineEnds_ChangedLinesOnly",
                                 cleanLineEnds_ChangedLinesOnly)
            prefs.setBooleanPref("ensureFinalEOL",
                                 ensureFinalEOL)
    

class KoDocIndentationDetection(_KoDocTestCase):
    __tags__ = ["indentation"]
    
    @property
    def data_dir(self):
        return join(dirname(abspath(__file__)), "indentation_data")
    
    def test_basics(self):
        """Note that this tests code path in koDocument._guessFileIndentation"""

        globalprefs = components.classes["@activestate.com/koPrefService;1"].\
                      getService(components.interfaces.koIPrefService).prefs
        defaultUseTabs = globalprefs.getBoolean("useTabs")
        defaultIndentWidth = globalprefs.getLong("indentWidth")
        defaultTabWidth = globalprefs.getLong("tabWidth")
        manifest = [
            {
                "name": "empty text",
                "content": "",
                "encoding": "utf-8",
                "useTabs": defaultUseTabs,
                "indentWidth": defaultIndentWidth,
                "tabWidth": defaultTabWidth,
            },
            # Tab indents == space indents (choose default)
            {
                "name": "Tabs equals spaces",
                "content": "\n\tfoo\n    \n\tbar\n    \n",
                "encoding": "utf-8",
                "useTabs": False,
                "indentWidth": 4,
                "tabWidth": defaultTabWidth,
            },
            # Tab indents > space indents (choose tabs)
            {
                "name": "More tabs than spaces",
                "content": "\n\tfoo\n    \n\tbar\n    \n\t\n",
                "encoding": "utf-8",
                "useTabs": True,
                "indentWidth": defaultTabWidth,
                "tabWidth": defaultTabWidth,
            },
            # Tab indents < space indents (choose spaces)
            {
                "name": "Less tabs than spaces",
                "content": "\n\tfoo\n    bar\n\tbaz\n    meat\n    popsicle\n",
                "encoding": "utf-8",
                "useTabs": False,
                "indentWidth": 4,
                "tabWidth": defaultTabWidth,
            },
            # No tab indents, but space indents (choose spaces)
            {
                "name": "Spaces not tabs",
                "content": "\nokay\n  foo\n  \n  bar\n  baz\n",
                "encoding": "utf-8",
                "useTabs": False,
                "indentWidth": defaultIndentWidth,
                "tabWidth": defaultTabWidth,
            },
        ]
        for entry in manifest:
            koDoc = self._koDocUntitled()
            koDoc.setBufferAndEncoding(entry["content"], entry["encoding"])
            self.assertEquals(koDoc.useTabs, entry["useTabs"],
                              "Failed useTabs test for %r" % (entry["name"]))
            self.assertEquals(koDoc.indentWidth, entry["indentWidth"],
                              "Failed indentWidth test for %r" % (entry["name"]))
            self.assertEquals(koDoc.tabWidth, entry["tabWidth"],
                              "Failed tabWidth test for %r" % (entry["name"]))

    def test_koGoLanguage(self):
        """Note that this tests code path in koLanguageBase.guessIndentation"""
        name = "koGoLanguage.py"
        koDoc = self._koDocFromPath(join(self.data_dir, name))
        self.assertEquals(koDoc.useTabs, False)

class TestKoDocumentRemote(_KoDocTestCase):
    def test_differentOnDisk(self):
        path = tempfile.mktemp()
        try:
            # Init the test file with some content.
            _writefile(path, "blah\nblah\nblah\n")

            koDoc = self._koDocFromPath(path, load=False)
            # Make it look like a remote file.
            rawFile = UnwrapObject(koDoc.file)
            rawFile.isLocal = 0
            rawFile.isRemoteFile = 1
            koDoc.load()

            # Wait one second, so we generate a different mtime.
            import time
            time.sleep(1.1)
            _writefile(path, "blah\nblah\nblah\nblah\n")

            self.assertTrue(koDoc.differentOnDisk(), "Remote file change was not detected")
            # Next time we call it - it should still detect the file as being changed - bug 95690.
            self.assertTrue(koDoc.differentOnDisk(), "Remote file change was not detected a second time")
            # Because we are using a fake koIFileEx (or really a local file),
            # this test can fail if the timestamp between the save and the
            # differentOnDisk calls has changed. To work around that, we run
            # multiple checks and only accept one failure.
            success_count = 0
            for tries in range(3):
                koDoc.save(True)
                if not koDoc.differentOnDisk():
                    success_count += 1
            self.assertTrue(success_count >= 2, "Remote file change detected after saving the file")
        finally:
            if os.path.exists(path):
                os.unlink(path) # clean up

    #def test_differentOnDisk_real(self):
    #    import random
    #    #path = "test_%06d.txt" % (random.randint(1, 1000000), )
    #    path = "/home/test/tmp/remote_files/test_%06d.txt" % (random.randint(1, 1000000), )
    #    try:
    #        # Init the test file with some content.
    #        content = "blah\nblah\nblah\n"
    #        _writefile(path, content)
    #
    #        uri = "sftp://test:pass@localhost" + path
    #        koDoc = self._koDocFromPath(path)
    #        koDoc.load()
    #
    #        # Wait one second, so we generate a different mtime.
    #        import time
    #        time.sleep(1.1)
    #        _writefile(path, "blah\nblah\nblah\nblah\n")
    #
    #        self.assertTrue(koDoc.differentOnDisk(), "Remote file change was not detected")
    #        # Next time we call it - it should be already using the latest info.
    #        self.assertFalse(koDoc.differentOnDisk(), "Remote file change detected when it shouldn't be")
    #    finally:
    #        if os.path.exists(path):
    #            os.unlink(path) # clean up

#---- internal support stuff

def _writefile(path, content, mode='wb'):
    from os.path import dirname, exists
    if not exists(dirname(path)):
        os.makedirs(dirname(path))
    fout = open(path, mode)
    try:
        fout.write(content)
    finally:
        fout.close()


#---- mainline

def suite():
    return unittest.makeSuite(TestKoDocumentBase)

def test_main():
    runner = unittest.TextTestRunner(verbosity=2)
    runner.run(suite())

if __name__ == "__main__":
    __file__ = os.path.abspath(sys.argv[0]) # won't be necessary in Python 2.3
    test_main()


