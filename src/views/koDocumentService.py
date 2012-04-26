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

# Services for working with documents in Komodo.

import os
import sys
import re
import logging
import threading
import re
from pprint import pprint
import difflib

from xpcom import components, nsError, ServerException, COMException
from xpcom.server import WrapObject, UnwrapObject
from xpcom.client import WeakReference

import eollib
import difflibex


#---- globals and support routines

log = logging.getLogger('koDocumentService')
#log.setLevel(logging.DEBUG)

if sys.platform.startswith("win"):
    def fequal(a, b):
        """Return true iff the two file paths are equal."""
        return a.lower() == b.lower()
else:
    def fequal(a, b):
        """Return true iff the two file paths are equal."""
        return a == b


#---- Component implementations

class KoDocumentService:
    _com_interfaces_ = [components.interfaces.koIDocumentService,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Document Service Component"
    _reg_contractid_ = "@activestate.com/koDocumentService;1"
    _reg_clsid_ = "{D65E6673-8DA2-40DE-8B50-18FFCC07F659}"
    
    def __init__(self):
        self._docCounters = {}
        self._documents = {}
        self._fileSvc = components.classes["@activestate.com/koFileService;1"]\
            .getService(components.interfaces.koIFileService)
        self._globalPrefsvc = components.classes["@activestate.com/koPrefService;1"]\
            .getService(components.interfaces.koIPrefService)

        obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                       getService(components.interfaces.nsIObserverService)
        obsSvc.addObserver(self, 'xpcom-shutdown', 1)
        
        # set up the background thread
        self.shutdown = 0
        self._thread = None
        self._cv = threading.Condition()
        self._cDoc = threading.Lock()
        
        self._thread = threading.Thread(target = KoDocumentService._autoSave,
                                        name = "Document Service - autosave",
                                        args = (self,))
        self._thread.start()

    def observe(self, subject, topic, data):
        if topic == "xpcom-shutdown":
            self.shutdownAutoSave()
            obsSvc = components.classes["@mozilla.org/observer-service;1"].\
                           getService(components.interfaces.nsIObserverService)
            obsSvc.removeObserver(self, 'xpcom-shutdown')

    def getAutoSaveDocuments(self):
        # this does about the same as getAllDocuments, but doesn't
        # remove documents from the list.  This is important as a
        # document does not have a refcount until after it is loaded,
        # but the autoSave thread may get to the document before it
        # is loaded.  So this now only returns dirty documents and does
        # not care about the refcount
        self._cDoc.acquire()
        try:
            docs = []
            # clear out all of the objects w/ no references to them
            for displayPath, wrappedDocRef in self._documents.items():
                wrappedDoc = wrappedDocRef()
                if not wrappedDoc:
                    del self._documents[displayPath]
                    continue
                doc = UnwrapObject(wrappedDoc)
                if doc._isDirty:
                    docs.append(doc)
            return docs
        finally:
            self._cDoc.release()

    def _autoSave(self):
        log.info("starting autosave thread")
        try:
          autosave_seconds = 30
          prefs = self._globalPrefsvc.prefs
          while not self.shutdown:
            try:
                self._cv.acquire()
                # Attempt autosave every N seconds.
                # NOTE: changing this to 1 second has the benefit of making the
                #       autosave behaviour extreme enough to point out issues we
                #       might not otherwise see.
                self._cv.wait(autosave_seconds)
                self._cv.release()

                if self.shutdown:
                    return

                # Reset the autosave period from the prefs (in case it changed).
                autosave_seconds = prefs.getLongPref("autoSaveSeconds")
                if autosave_seconds <= 0:
                    # Disabled, wait 30 seconds and then check again.
                    autosave_seconds = 30
                    log.debug("autoSave disabled by pref, skipping")
                    continue

                docs = self.getAutoSaveDocuments()
                log.debug("autosaving documents %s", len(docs))
                for doc in docs:
                    if self.shutdown: return
                    doc.doAutoSave()
                docs = doc = None
                
                # XXX projects and other files?
                
            except Exception, e:
                # never die
                log.exception(e)
                pass
        finally:
            log.info("exiting autosave thread")

    def shutdownAutoSave(self):
        if not self.shutdown:
            self.shutdown = 1
            # notify the autosave thread to quit
            self._cv.acquire()
            self._cv.notify()
            self._cv.release()
            # here we wait for the thread to terminate
            log.debug("waiting for thread to terminate")
            # Wait for a maximum of 3 seconds before returning
            self._thread.join(3)
            log.debug("thread has terminated")

    #koIDocument createNewDocumentFromURI(in wstring uri);
    def createNewDocumentFromURI(self, uri):
        log.info("creating document with URI: %s", uri)
        file = self._fileSvc.getFileFromURI(uri)

        # We need to know the latest information about this file, so refresh
        # the file information now. We use the hasChanged property, as this
        # has the side-effect of re-stat'ing. Psychotically, this is the only
        # way to initiate a re-stat. Don't do this for non-local files.
        # Fixes bug:
        # http://bugs.activestate.com/show_bug.cgi?id=68285
        if file.isLocal and not file.isNetworkFile:
            file.hasChanged

        doc = components.classes["@activestate.com/koDocumentBase;1"]\
            .createInstance(components.interfaces.koIDocument)
        doc.initWithFile(file,0)

        self._cDoc.acquire()
        try:
            self._documents[doc.displayPath] = WeakReference(doc)
        finally:
            self._cDoc.release()
        return doc

    #koIDocument createDocumentFromURI(in wstring uri);
    def createDocumentFromURI(self, uri):
        doc = self.findDocumentByURI(uri)
        if doc:
            log.info("found document with existing URI: %s", uri)
            return doc
        return self.createNewDocumentFromURI(uri)

    def _getEncodingFromFilename(self, fname):
        try:
            registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                                getService(components.interfaces.koILanguageRegistryService)
            prefs = self._globalPrefsvc.prefs
            languagesPrefs = prefs.getPref('languages')
            language = registryService.suggestLanguageForFile(fname)
            if not language:
                language = 'Text'
            encoding = 'Default Encoding'
            if languagesPrefs.hasPref('languages/'+language):
                langPref = languagesPrefs.getPref('languages/'+language)
                if langPref.hasStringPref(language+'/newEncoding'):
                    encoding = langPref.getStringPref(language+'/newEncoding')
            if encoding == 'Default Encoding':
                encoding = prefs.getStringPref('encodingDefault')
        except Exception, e:
            log.error("Error getting newEncoding for %s", language, exc_info=1)
            encoding = prefs.getStringPref('encodingDefault')
        return encoding

    def _fixupEOL(self, doc):
        """fixupEOL is used when creating new files from templates in order
           to set the document's EOL"""
        eolPref = self._globalPrefsvc.prefs.getStringPref("endOfLine")
        try:
            eol = eollib.eolPref2eol[eolPref]
        except KeyError:
            # Be paranoid: stay with system default if pref value is bogus.
            log.exception("unexpected 'endOfLine' pref value: %r", eolPref)
            eol = eollib.EOL_PLATFORM
        doc.existing_line_endings = eol
        doc.new_line_endings = eol
        doc.isDirty = 0
    
    def createDocumentFromTemplateURI(self, uri, name, ext):
        log.info("creating document with URI: %s", uri)
        name = name or "Untitled"
        ext = ext or ""
        doc = components.classes["@activestate.com/koDocumentBase;1"]\
            .createInstance(components.interfaces.koIDocument)
        title = "%s-%d%s" % (name, self._docCounterFromPrefix(name), ext)
        doc.initUntitled(title, self._getEncodingFromFilename(title))
        doc.loadFromURI(uri)
        self._fixupEOL(doc)
        self._cDoc.acquire()
        try:
            self._documents[doc.displayPath] = WeakReference(doc)
        finally:
            self._cDoc.release()
        return doc

    def createFileFromTemplateURI(self, uri, saveto, force):
        log.info("creating document with URI: %s", uri)
        doc = self.createDocumentFromURI(saveto)
        doc.loadFromURI(uri)
        self._fixupEOL(doc)
        if force:
            doc.save(1)
        return doc

    def _untitledNameFromLanguage(self, language):
        if not language:
            if self._globalPrefsvc.hasPref('fileDefaultNew'):
                language = self._globalPrefsvc.getStringPref('fileDefaultNew')
            # language registry defaults to Text if no language
        
        # Determine the document base name.
        languageRegistry = components.classes["@activestate.com/koLanguageRegistryService;1"]\
            .getService(components.interfaces.koILanguageRegistryService)
        koLanguage = languageRegistry.getLanguage(language)
        try:
            ext = koLanguage.defaultExtension
        except:
            ext = '.txt'
        return "%s-%d%s" % (language, self._docCounterFromPrefix(language), ext)
        
    def createUntitledDocument(self, language):
        leafName = self._untitledNameFromLanguage(language)
        # Just return the existing document for this name if there is one.
        doc = self.findDocumentByDisplayPath(leafName)
        if doc:
            return doc
        
        # Create a new document.
        encoding = self._getEncodingFromFilename(leafName)
        doc = components.classes["@activestate.com/koDocumentBase;1"]\
            .createInstance(components.interfaces.koIDocument)
        doc.initUntitled(leafName, encoding)
        eolPref = self._globalPrefsvc.prefs.getStringPref("endOfLine")
        try:
            eol = eollib.eolPref2eol[eolPref]
        except KeyError:
            # Be paranoid: stay with system default if pref value is bogus.
            log.exception("unexpected 'endOfLine' pref value: %r", eolPref)
            eol = eollib.EOL_PLATFORM
        doc.new_line_endings = eol

        self._cDoc.acquire()
        try:
            self._documents[doc.displayPath] = WeakReference(doc)
        finally:
            self._cDoc.release()
        return doc
    
    #void getAllDocuments([array, size_is(count)] out koIDocument documents,
    #                 out PRUint32 count);
    def getAllDocuments(self):
        self._cDoc.acquire()
        try:
            strong = []
            # clear out all of the objects w/ no references to them
            for displayPath, wrappedDocRef in self._documents.items():
                wrappedDoc = wrappedDocRef()
                if not wrappedDoc:
                    del self._documents[displayPath]
                    continue
                doc = UnwrapObject(wrappedDoc)
                if doc._refcount == 0:
                    del self._documents[displayPath]
                    continue
                strong.append(doc)
            return strong
        finally:
            self._cDoc.release()

    #koIDocument findDocumentByURI(in string URI);
    def findDocumentByURI(self, uri):
        from URIlib import URIParser
        p = URIParser()
        uri = p.URI = uri # cleanup uri
        self._cDoc.acquire()
        try:
            for displayPath, wrappedDocRef in self._documents.items():
                wrappedDoc = wrappedDocRef()
                if not wrappedDoc:
                    del self._documents[displayPath]
                elif ((wrappedDoc.isUntitled and fequal(wrappedDoc.baseName, uri)) or
                    (not wrappedDoc.isUntitled and fequal(wrappedDoc.file.URI, uri))):
                    doc = UnwrapObject(wrappedDoc)
                    if doc._refcount == 0:
                        log.debug("deleting reference to %s", displayPath)
                        del self._documents[displayPath]
                        return None
                    return wrappedDoc
        finally:
            self._cDoc.release()
        return None

    def findDocumentByDisplayPath(self, displayPath):
        self._cDoc.acquire()
        try:
            if displayPath in self._documents:
                wrappedDoc = self._documents[displayPath]()
                if not wrappedDoc:
                    del self._documents[displayPath]
                    return None
                doc = UnwrapObject(wrappedDoc)
                if doc._refcount == 0:
                    del self._documents[displayPath]
                    return None
                return wrappedDoc
        finally:
            self._cDoc.release()
        return None

    def _docCounterFromPrefix(self, prefix):
        if prefix not in self._docCounters:
            self._docCounters[prefix] = 0
        self._docCounters[prefix] += 1
        return self._docCounters[prefix]

    # List of regex'es that we use to look for filename/line# in the input line
    # These should match all of the styles done by Scintilla in LexOthers.cxx,
    # in the ColouriseErrorListLine function
    _errorHotspotPatterns = [
        # SCE_ERR_PERL, e.g.
        #   ... at D:\trentm\as\Apps\Komodo-devel\foo.pl line 2.
        #   ... at C:\Documents and Settings\clong.ORION\My Documents\My Projects\J1238 Cornerstone\MCT\Perl_App\dvcparms_mod.pl line 3368, at end of line
        re.compile(r'\bat (?P<fname>.*?) line (?P<lineno>\d+)'),

        # SCE_ERR_PHP, e.g.
        #    php -d html_errors=off -l bad.php
        #       Parse error: parse error, unexpected T_PRINT in C:\main\Apps\Komodo-dogfood\bad.php on line 8
        re.compile(r'\bin (?P<fname>.*?) on line (?P<lineno>\d+)'),
        #    PHP stacktraces look like this:
        #PHP Stack trace:
        #PHP   1. {main}() c:\home\ericp\lab\komodo\bugs\bz71236d.php:0
        #PHP   2. f1($a = *uninitialized*, $b = *uninitialized*) c:\home\ericp\lab\komodo\bugs\bz71236d.php:6
        #PHP   3. f2($a = *uninitialized*, $b = *uninitialized*) c:\home\ericp\lab\komodo\bugs\bz71236d.php:9
        #PHP   4. f3($a = *uninitialized*, $b = *uninitialized*) c:\home\ericp\lab\komodo\bugs\bz71236d.php:12
        re.compile(r'^PHP\s+\d+\..+\)\s*(?P<fname>.+?):(?P<lineno>\d+)'),
        
        # Some Ruby stack traces look like this (ignoring the "in ... `method-name`" part)
        re.compile(r'^\s*from\s+(?P<fname>.+?):(?P<lineno>\d+)'),
        
        #  LexOthers.cxx doesn't pick on the HTML encoded ones:
        #   php -l bad.php
        #       <b>Parse error</b>:  parse error, unexpected T_PRINT in <b>C:\main\Apps\Komodo-dogfood\bad.php</b> on line <b>8</b><br />
        #re.compile('in <b>(?P<fname>.*)</b> on line <b>(?P<lineno>\d+)</b>'),

        # SCE_ERR_PYTHON
        re.compile('^  File "(?P<fname>.*?)", line (?P<lineno>\d+)'),

        # SCE_ERR_GCC
        # <filename>:<line>:message
        # \s*<filename>:<line>:message
        # \s*<filename>:<line>\s*$
        # This is also used for Ruby output.  See bug 71238.
        re.compile(r'^\s*(?P<fname>.+?):(?P<lineno>\d+)'),

        # SCE_ERR_MS
        # <filename>(line) :message
        re.compile('^(?P<fname>.*?):\((?P<lineno>\d+)\) :'),
        # <filename>(line,pos)message
        re.compile('^(?P<fname>.*?):\((?P<lineno>\d+),\d+\)'),

        # SCE_ERR_ELF: Essential Lahey Fortran error message
        re.compile('^Line (?P<lineno>\d+?), file (?P<fname>.*?)'),

        # SCE_ERR_NET: a .NET traceback
        re.compile('   at (?P<fname>.*?):line (?P<lineno>\d+)'),

        # SCE_ERR_LUA
        re.compile('at line (?P<lineno>\d+) file (?P<fname>.*?)'),

        # Perl testing error message patterns
        re.compile(r'^#\s+Test\s+\d+\s+got:.*?\((?P<fname>[^\"\'\[\]\(\)\#]+?)\s+at\s+line\s+(?P<lineno>\d+)\)'),
        re.compile(r'^#\s*(?P<fname>[^\"\'\[\]\(\)\#]+?)\s+line\s+(?P<lineno>\d+)\s+is:'),  # extra for context

        # SCE_ERR_CTAG
        #TODO
        # SCE_ERR_BORLAND
        #TODO
        # SCE_ERR_IFC: Intel Fortran Compiler error/warning message
        # I need an example for this to get the regex right.
        #re.compile('^(Error|Warning) ... at \(...\) : ...'),
        # SCE_ERR_CMD
        #TODO
    ]

    def parseHotspotLine(self, line, cwd):
        for pattern in self._errorHotspotPatterns:
            match = pattern.search(line)
            if match:
                break
        else:
            return None
        fname = match.group('fname')
        lineNo = match.group('lineno')
        if fname.startswith('/') or (len(fname) > 3 and fname[1] == ':'):
            fullfname = fname
        elif cwd:
            fullfname = os.path.normpath(os.path.join(cwd, fname))
        else:
            fullfname = fname
        if not os.path.exists(fullfname):
            log.warn("parseHotspotLine(line=%r, ...): filename %r "
                     "does not exist", line, fullfname)
        return [fullfname, lineNo]

class KoDiff:
    _com_interfaces_ = [components.interfaces.koIDiff]
    _reg_desc_ = "Komodo Diff Service Component"
    _reg_contractid_ = "@activestate.com/koDiff;1"
    _reg_clsid_ = "{5faaa9b1-4c2f-41d1-936d-22d2e24768c5}"
    
    def __init__(self):
        self.__docSvc = None
        self._reset()

    def _reset(self):
        self.doc1 = None
        self.doc2 = None
        self.diff = None
        self._diffex = None
        self.warning = None

    def _getDocSvc(self):
        if self.__docSvc is None:
            self.__docSvc = components.classes["@activestate.com/koDocumentService;1"]\
                            .getService(components.interfaces.koIDocumentService)
        return self.__docSvc

    @property
    def diffex(self):
        if self._diffex is None:
            self._diffex = difflibex.Diff(self.diff)
        return self._diffex

    def initWithDiffContent(self, diff):
        self._reset()
        self.diff = diff

    def initByDiffingFiles(self, fname1, fname2):
        # XXX upgrade to deal with remote files someday?
        docSvc = self._getDocSvc()
        doc1 = docSvc.createDocumentFromURI(fname1)
        doc1.load()
        doc2 = docSvc.createDocumentFromURI(fname2)
        doc2.load()
        self.initByDiffingDocuments(doc1, doc2)

    def initByDiffingDocuments(self, doc1, doc2):
        """Get a unified diff of the given koIDocument's."""
        self._reset()

        self.doc1 = doc1
        self.doc2 = doc2
        
        native_eol = eollib.eol2eolStr[eollib.EOL_PLATFORM]
        try:
            # difflib takes forever to work if newlines do not match
            content1_eol_clean = re.sub("\r\n|\r|\n", native_eol, doc1.buffer)
            content2_eol_clean = re.sub("\r\n|\r|\n", native_eol, doc2.buffer)
        except IOError, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))

        if doc1.existing_line_endings != doc2.existing_line_endings:
            self.warning = "ignoring end-of-line differences"
        else:
            self.warning = ""

        if (content1_eol_clean == content2_eol_clean):
            self.diff = ""
        else:
            difflines = difflibex.unified_diff(
                content1_eol_clean.splitlines(1),
                content2_eol_clean.splitlines(1),
                doc1.displayPath,
                doc2.displayPath,
                lineterm=native_eol)
            self.diff = ''.join(difflines)

    def filePosFromDiffPos(self, line, column):
        try:
            return self.diffex.file_pos_from_diff_pos(line, column)
        except difflibex.DiffLibExError, ex:
            lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
                           .getService(components.interfaces.koILastErrorService)
            lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))

    def inferCwdAndStripFromPath(self, pathInDiff, actualPath):
        try:
            return difflibex.infer_cwd_and_strip_from_path(pathInDiff,
                                                           actualPath)
        except difflibex.DiffLibExError, ex:
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))
