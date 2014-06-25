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

from zope.cachedescriptors.property import LazyClassAttribute

from xpcom import components, COMException
from xpcom.server import UnwrapObject
from xpcom.client import WeakReference

import eollib


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

    # Lazily loaded class variables.
    @LazyClassAttribute
    def obsSvc(self):
        return components.classes["@mozilla.org/observer-service;1"].\
                    getService(components.interfaces.nsIObserverService)
    @LazyClassAttribute
    def langRegistrySvc(self):
        return components.classes['@activestate.com/koLanguageRegistryService;1'].\
                    getService(components.interfaces.koILanguageRegistryService)
    @LazyClassAttribute
    def lastErrorSvc(self):
        return components.classes["@activestate.com/koLastErrorService;1"].\
                    getService(components.interfaces.koILastErrorService)
    @LazyClassAttribute
    def _fileSvc(self):
        return components.classes["@activestate.com/koFileService;1"].\
                    getService(components.interfaces.koIFileService)
    @LazyClassAttribute
    def _globalPrefs(self):
        return components.classes["@activestate.com/koPrefService;1"].\
                    getService(components.interfaces.koIPrefService).\
                    prefs

    def __init__(self):
        self._docCounters = {}
        self._documents = {}

        self.obsSvc.addObserver(self, 'komodo-post-startup', False)
        self.obsSvc.addObserver(self, 'xpcom-shutdown', False)
        self.obsSvc.addObserver(self, 'current_project_changed', False)
        
        # set up the background thread
        self.shutdown = 0
        self._thread = None
        self._cv = threading.Condition()
        self._cDoc = threading.Lock()
        
    def observe(self, subject, topic, data):
        if topic == 'komodo-post-startup':
            self.obsSvc.removeObserver(self, 'komodo-post-startup')
            self._thread = threading.Thread(target = KoDocumentService._autoSave,
                                            name = "Document Service - autosave",
                                            args = (self,))
            # Set the autosave thread as a daemon thread so it won't prevent
            # shutdown; see bug 101357.  This is only safe because the actual
            # writing happens on the main thread via ProxyToMainThread; see
            # koDocumentBase._doAutoSave in koDocument.py.
            self._thread.daemon = True
            self._thread.start()
        elif topic == "xpcom-shutdown":
            self.shutdownAutoSave()
            self.obsSvc.removeObserver(self, 'current_project_changed')
            self.obsSvc.removeObserver(self, 'xpcom-shutdown')
        elif topic == "current_project_changed":
            # Reset koDoc preferences.
            for doc in self.getAllDocuments():
                doc.resetPreferenceChain()

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
                try:
                    wrappedDoc = wrappedDocRef()
                except COMException:
                    wrappedDoc = None  # dead object
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
                autosave_seconds = self._globalPrefs.getLongPref("autoSaveSeconds")
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
            if self._thread:
                # here we wait for the thread to terminate
                log.debug("waiting for thread to terminate")
                # Wait for a maximum of 3 seconds before returning
                self._thread.join(3)
                log.debug("thread has terminated")
                self._thread = None

    #koIDocument createNewDocumentFromURI(in wstring uri);
    def createNewDocumentFromURI(self, uri):
        log.info("creating document with URI: %s", uri)
        file = self._fileSvc.getFileFromURI(uri)

        # We need to know the latest information about this file, so refresh
        # the file information. Don't do this for non-local files - bug 68285.
        if file.isLocal and not file.isNetworkFile:
            file.updateStats()

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
            language = self.langRegistrySvc.suggestLanguageForFile(fname)
            if not language:
                language = 'Text'
            encodingPref = 'languages/' + language + '/newEncoding'
            encoding = self._globalPrefs.getString(encodingPref,
                                                   'Default Encoding')
            if encoding == 'Default Encoding':
                encoding = self._globalPrefs.getString('encodingDefault')
        except Exception, e:
            log.error("Error getting newEncoding for %s", language, exc_info=1)
            encoding = self._globalPrefs.getString('encodingDefault')
        return encoding

    def _fixupEOL(self, doc):
        """fixupEOL is used when creating new files from templates in order
           to set the document's EOL"""
        eolPref = self._globalPrefs.getStringPref("endOfLine")
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
        koLanguage = self.langRegistrySvc.getLanguage(language)
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
        eolPref = self._globalPrefs.getStringPref("endOfLine")
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
                try:
                    wrappedDoc = wrappedDocRef()
                except COMException:
                    wrappedDoc = None  # dead object
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
                try:
                    wrappedDoc = wrappedDocRef()
                except COMException:
                    wrappedDoc = None  # dead object
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
    @LazyClassAttribute
    def _errorHotspotPatterns(self):
        return [
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
