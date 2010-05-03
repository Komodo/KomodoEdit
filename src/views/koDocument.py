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

# An implementation of a file object for Mozilla/xpcom.

from xpcom import components, nsError, ServerException, COMException, _xpcom
from xpcom.server import WrapObject, UnwrapObject
import xpcom
import logging
from hashlib import md5
import re
import sys
import cStringIO
import timeline
import stat, os, time

import eollib
import difflibex
import langinfo
from koLanguageServiceBase import getActualStyle
from koUDLLanguageBase import udl_family_from_style
import koUnicodeEncoding, codecs, types

log = logging.getLogger('koDocument')
#log.setLevel(logging.DEBUG)

class koDocumentBase:
    _com_interfaces_ = [components.interfaces.koIDocument,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Document"
    _reg_contractid_ = "@activestate.com/koDocumentBase;1"
    _reg_clsid_ = "{A9F51FD2-CF82-4290-87B8-BD07CEBD1CD1}"

    re_firstline = re.compile(ur'(.*?)(?:\r|\n|$)')
    _indentWidth = None
    _tabWidth = None
    _useTabs = None

    _DOCUMENT_SIZE_NOT_LARGE = 0
    _DOCUMENT_SIZE_UDL_LARGE = 1
    _DOCUMENT_SIZE_ANY_LARGE = 2

    def __init__(self):
        timeline.enter('koDocumentBase.__init__')
        # Grab a reference to the global preference service.
        self._globalPrefSvc = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService)
        self._globalPrefs = self._globalPrefSvc.prefs

        self._buffer = None # string The contents of the document
        self._codePage = 65001 # Komodo always uses 65001 (i.e. scintilla UTF-8 mode)
        self.encoding = None # string The name of the Unicode encoding -- undefined if codepage is not 65001
        self._language = None # string what language is this document in?
        self._languageObj = None
        self.prefs = None # set after initWith() call
        self.file = None
        self._isDirty = 0     # boolean
        self.isUntitled = 1  # boolean
        self._views = [] # scintilla widget instances
        self._docPointer = None # scimoz.docPointer
        #XXX should get eol from prefs and/or from document content
        self._eol = eollib.EOL_PLATFORM
        
        # lastmd5 is always the md5 of the contents of the file on disk
        # it is updated on load, save, revert, and when we call
        # differentOnDisk.  It DOES NOT reflect the current contents of
        # the buffer in memory
        self._lastmd5 = None
        
        self._refcount = 0
        self.ciBuf = None
        self.docSettingsMgr = None

        self._tabstopInsertionNodes = None

        self.encodingServices = components.classes['@activestate.com/koEncodingServices;1'].\
                         getService(components.interfaces.koIEncodingServices);

        # yes, createInstance.  We want to provide our own observer services
        # for documents
        self.observerService = components.classes['@activestate.com/koObserverService;1'].\
                                createInstance(components.interfaces.nsIObserverService)

        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"].\
                                getService(components.interfaces.koILastErrorService)
        
        self._obsSvc = components.classes['@mozilla.org/observer-service;1'].\
                                getService(components.interfaces.nsIObserverService);
        self._obsSvcProxy = _xpcom.getProxyForObject(1, components.interfaces.nsIObserverService,
                                          self._obsSvc, _xpcom.PROXY_SYNC | _xpcom.PROXY_ALWAYS)
        self.docSettingsMgr = components.classes['@activestate.com/koDocumentSettingsManager;1'].\
            createInstance(components.interfaces.koIDocumentSettingsManager);
        self._historySvc = components.classes["@activestate.com/koHistoryService;1"].\
                           getService(components.interfaces.koIHistoryService)


        self._wrapSelf = None
        
        self.lidb = langinfo.get_default_database()

        self.init()
        self.isLargeDocument = False
        self._documentSizeFactor = self._DOCUMENT_SIZE_NOT_LARGE

        # This field can be used to override the default lexer set in the
        # document's language service.  Useful for using a different colorizer,
        # usually text for a large document.
        self.lexer = None

        timeline.leave('koDocumentBase.__init__')
    
    #TODO: refactor so `init` and `_dereference` actually sound like they relate (which they do)
    #      also make `init` internal
    def init(self):
        # when we reference count upwards, we might need to recreate some components
        # this could happen if anyone keeps a reference to the document, and the document
        # is reloaded

        # if we're the current view, we cannot get the text from
        # scintilla in a thread, and must proxy.  since this shouldn't
        # get hit often, we'll just always proxy to be on the safe
        # side of things
        if not self._wrapSelf:
            wrapSelf = xpcom.server.WrapObject(self, components.interfaces.koIDocument)
            self._wrapSelf = _xpcom.getProxyForObject(1, components.interfaces.koIDocument,
                                              wrapSelf, _xpcom.PROXY_SYNC | _xpcom.PROXY_ALWAYS)
        if not self.docSettingsMgr:
            self.docSettingsMgr = components.classes['@activestate.com/koDocumentSettingsManager;1'].\
                createInstance(components.interfaces.koIDocumentSettingsManager);

    def _dereference(self):
        # prevent any chance of a circular reference
        self.docSettingsMgr = None
        self.prefs.removeObserver(self)
        self._wrapSelf = None
        self.ciBuf = None

    def _initCIBuf(self):
        codeIntelSvc = components.classes['@activestate.com/koCodeIntelService;1'] \
                        .getService(components.interfaces.koICodeIntelService)
        self.ciBuf = codeIntelSvc.buf_from_koIDocument(self)

    def initWithFile(self, file, untitled):
        timeline.enter('koDocumentBase.initWithFile')
        log.info("initWithFile(file=%s, ...)", file.URI)
        self.isUntitled = untitled
        self.file = file
        self._setupPrefs()
        if self._language is None:
            self._guessLanguage()

        # This gets called again unnecessarily in self.load(). Can't
        # follow the koDocument spaghetti to be assured this
        # self._initCIBuf() can be removed for all cases.
        self._initCIBuf()

        timeline.leave('koDocumentBase.initWithFile')

    def initUntitled(self, name, encoding):
        timeline.enter('koDocumentBase.initUntitled')
        log.info("initUntitled(name=%r, ...)", name)
        self.isUntitled = 1
        self._untitledName = name
        self._setupPrefs(encoding)
        self.set_buffer("", 0)  # make sure new buffer is not dirty
        if self._language is None:
            self._guessLanguage()
        self._initCIBuf()
        timeline.leave('koDocumentBase.initUntitled')

    def addReference(self):
        self._refcount += 1
        if self._refcount == 1:
            self.init()
        log.debug('refcount = %d', self._refcount)

    def releaseReference(self):
        if self._refcount <= 0:
            log.error("Trying to release a reference with a refcount < 1! for displayPath: %s",
                      self.get_displayPath())
        else:
            self._refcount -= 1
        if self._refcount < 1:
            self._dereference()
        log.debug('refcount = %d', self._refcount)
        
    def _setupPrefs(self, encoding_name=None):
        """ We can only setup the prefs on the document once we have a URI for it
        So after __init__, self.prefs is None, until we get an "initWith....()" call.
        Note that some things like encoding derive from prefs.
        """
        timeline.enter('koDocumentBase._setupPrefs')
        # Create a preference set to hold doc preferences
        docStateMRU = self._globalPrefSvc.getPrefs("docStateMRU");
        if not self.isUntitled and docStateMRU.hasPref(self.file.URI):
            url = self.file.URI
            docState = docStateMRU.getPref(url)
            self.prefs = docState
        else:
            self.prefs = components.classes['@activestate.com/koPreferenceSet;1'].\
                                     createInstance(components.interfaces.koIPreferenceSet)
            if self.isUntitled:
                self.prefs.id = self._untitledName
            else:
                self.prefs.id = self.file.encodedURI
            docStateMRU.setPref(self.prefs)
        self.prefs.parent = self._globalPrefs

        # Set the default encoding for the file
        self.encoding = components.classes['@activestate.com/koEncoding;1'].\
                                 createInstance(components.interfaces.koIEncoding)
        if not encoding_name:
            encoding_name = self._getStringPref('encodingDefault')
        self.encoding.python_encoding_name = self.encodingServices.get_canonical_python_encoding_name(
            self.encodingServices.get_encoding_info(encoding_name).python_encoding_name)

        if self.prefs.hasPref('language'):
            #print "found language in prefs: ", self.prefs.getStringPref('language')
            self.set_language(self.prefs.getStringPref('language'))

        # setup an observer on our own prefs since we provide access to some
        # through getters because e.g. indentWidth is computed on some cases, and
        # yet not stored in prefs except if set explicitely.
        log.debug("adding prefs observer")
        self.prefs.addObserver(self)
        timeline.leave('koDocumentBase._setupPrefs')

    def getEffectivePrefs(self):
        # this returns either a prefset from a project, or my own prefset
        if self.file and self.file.URI:
            _partSvc = components.classes["@activestate.com/koPartService;1"]\
                .getService(components.interfaces.koIPartService)
            prefset = _partSvc.getEffectivePrefsForURL(self.file.URI)
            if prefset:
                return prefset
        return self.prefs
    
    def _setLangPrefs(self):
        lprefs = self._globalPrefs.getPref("languages")
        if lprefs.hasPref("languages/"+self._language):
            prefs = lprefs.getPref("languages/"+self._language)
        else:
            prefs = components.classes["@activestate.com/koPreferenceSet;1"].createInstance();
            prefs.id = 'languages/'+self._language;
            lprefs.setPref(prefs.id, prefs);
            
        self.prefs.parent = prefs
        prefs.parent = self._globalPrefs

    def _isUDLLanguage(self, langRegistrySvc, languageName):
        return UnwrapObject(langRegistrySvc.getLanguage(languageName)).isUDL()

    def _isConsideredLargeDocument(self, langRegistrySvc, languageName):
        if self._documentSizeFactor == self._DOCUMENT_SIZE_NOT_LARGE:
            return False
        elif self._documentSizeFactor == self._DOCUMENT_SIZE_ANY_LARGE:
            return True
        else:
            return self._isUDLLanguage(langRegistrySvc, languageName)

    def _setAsLargeDocument(self, languageName):
        self.prefs.setStringPref("originalLanguage", languageName)
        self.isLargeDocument = True
        self.prefs.setStringPref('language', "Text")

    def _guessLanguage(self):
        """Guess and set this document's language."""
        timeline.enter('koDocumentBase._guessLanguage')

        # If a preferred language was specifically set for this document
        # then just use that, unless it's too large for Komodo.

        langRegistrySvc = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                          getService(components.interfaces.koILanguageRegistryService)

        if self.prefs.hasPrefHere('language'):
            language = self.prefs.getStringPref('language')
            if language != "Text" \
               and self._isConsideredLargeDocument(langRegistrySvc, language):
                self._setAsLargeDocument(language)
                language = "Text"
            self._language = language
            self._setLangPrefs()
            log.info("_guessLanguage: use set preference: '%s'",
                     self._language)
            return

        # Determine the probable language from the file basename.
        baseName = self.get_baseName()
        fileNameLanguage = None
        if baseName:
            # some uri's will not have a baseName, eg. http://www.google.com
            fileNameLanguage = langRegistrySvc.suggestLanguageForFile(baseName)
            log.info("_guessLanguage: probable language from basename '%s': '%s'",
                     baseName, fileNameLanguage)
        
        # Determine an ordered list (preferred first) of possible languages
        # from the file content.
        # - Optimization: Don't send whole document because all required
        #   file-type information is required to be either at the front or
        #   end of the document. [Is this a necessary opt? --TM]
        contentLanguages = []
        buffer = self.get_buffer()
        if buffer:
            if fileNameLanguage == "Python":
                contentLanguages = self._distinguishPythonVersion(buffer)
            else:
                contentLanguages = langRegistrySvc.guessLanguageFromContents(
                    buffer[:1000], buffer[-1000:])
            log.info("_guessLanguage: possible languages from content: %s",
                     contentLanguages)

        #XXX:TODO: test that this refactoring still properly has new
        #          files follow the "new file language" pref.

        #print "we got file [%s] content [%r]" % (fileNameLanguage,contentLanguages)
        # Select the appropriate language from the above guesses.
        if not contentLanguages and not fileNameLanguage:
            language = "Text"
            log.info("_guessLanguage: '%s' (fallback)", language)
        elif not contentLanguages:
            language = fileNameLanguage
            log.info("_guessLanguage: '%s' (filename)", language)
        else:
            language = contentLanguages[0]
            # always defer to the extension match if our primary content match
            # is a generic markup language.  If it is more specific (eg. XBL)
            # then we want to maintain that instead of the filename match
            if fileNameLanguage and language in ["XML", "HTML", "XHTML"]:
                language = fileNameLanguage
            log.info("_guessLanguage: '%s' (content)", language)
        if self._isConsideredLargeDocument(langRegistrySvc, language):
            self._setAsLargeDocument(language)
            language = "Text"
        self._language = language
        self._setLangPrefs()
        timeline.leave('koDocumentBase._guessLanguage')

    def loadFromURI(self, uri):
        filesvc = components.classes["@activestate.com/koFileService;1"] \
                        .createInstance(components.interfaces.koIFileService)
        file = filesvc.getFileFromURI(uri)
        self._loadFromFile(file)
        
    def load(self):
        if self.isUntitled or self.file.URI.startswith('chrome://'):
            return
        self._loadFromFile(self.file)
        
    def _loadFromFile(self, file):
        timeline.enter('koDocumentBase._loadFromFile')
        if self.get_numScintillas() > 0:
            # The file is already loaded, in another window.
            # If we don't return here, two things can happen:
            # 1. A dirty buffer in another window will be reverted
            #    to the contents on disk.
            # 2. Any markers in the document will be cleared.
            timeline.leave('koDocumentBase._loadFromFile')
            return
        self._loadfile(file)
        self._guessLanguage()
        self._initCIBuf() # need a new codeintel Buffer for this lang
        eolpref = self.prefs.getStringPref('endOfLine')
        if self.prefs.hasPrefHere('endOfLine'):
            current_eol = eollib.eolPref2eol[eolpref]
        else:
            current_eol = self.get_existing_line_endings()
            if current_eol in (eollib.EOL_MIXED, eollib.EOL_NOEOL):
                current_eol = eollib.eolPref2eol[eolpref]
        self.set_new_line_endings(current_eol)
            
        timeline.leave('koDocumentBase._loadFromFile')
        
    def _classifyDocumentBySize(self, data):
        """ Return 0 if it's short, 1 if it's long for a UDL-based
            file, 2 if it's long by any means.
        """
        returnFactor = self._DOCUMENT_SIZE_NOT_LARGE
        documentByteCountThreshold = self.prefs.getLongPref("documentByteCountThreshold")
        if len(data) > documentByteCountThreshold:
            return self._DOCUMENT_SIZE_ANY_LARGE
        elif len(data) > documentByteCountThreshold/2:
            returnFactor = self._DOCUMENT_SIZE_UDL_LARGE
            
        documentLineCountThreshold = self.prefs.getLongPref("documentLineCountThreshold")
        line_lengths = [len(line) for line in data.splitlines()]
        num_lines = len(line_lengths)
        if num_lines > documentLineCountThreshold:
            return self._DOCUMENT_SIZE_ANY_LARGE
        elif num_lines > documentLineCountThreshold / 2:
            returnFactor = self._DOCUMENT_SIZE_UDL_LARGE

        
        documentLineLengthThreshold = self.prefs.getLongPref("documentLineLengthThreshold")
        documentLineLengthThreshold_Halved = documentLineLengthThreshold / 2
        if any([line_length >= documentLineLengthThreshold for line_length in line_lengths]):
            return self._DOCUMENT_SIZE_ANY_LARGE
        elif any([line_length >= documentLineLengthThreshold/2 for line_length in line_lengths]):
            return self._DOCUMENT_SIZE_UDL_LARGE

        return returnFactor

    def _loadfile(self, file):
        timeline.enter('koDocumentBase._loadfile')
        if file:
            data = self._get_buffer_from_file(file)
            self._documentSizeFactor = self._classifyDocumentBySize(data)
            # We don't know if the document is large until we know
            # whether it's a UDL-based document or has a C++ lexer.
        else:
            data = ''
        self._lastmd5 = md5(data).digest()
        self.set_buffer(data,0)
        self.setSavePoint()
        # if a file is in a project, then we have to check
        # and see if we need to update it's information
        if file.hasChanged:
            try:
                self._obsSvc.notifyObservers(self,'file_changed',self.file.URI)
            except:
                # ignore, noone listening
                pass
        self.set_isDirty(0)
        timeline.leave('koDocumentBase._loadfile')
        
    def _get_buffer_from_file(self, file):
        timeline.enter('koDocumentBase._get_buffer_from_file')
        try:
            file.open('rb')
            data = file.read(-1)
            file.close()
        except COMException, ex:
            # koFileEx.open(), .read(), and .close() will already
            # setLastError on failure so don't need to do it again. The
            # only reason we catch it to just re-raise it is because
            # PyXPCOM complains on stderr if a COMException passes out
            # of the Python run-time.
            raise ServerException(ex.errno, str(ex))
        timeline.leave('koDocumentBase._get_buffer_from_file')
        return data

    def get_isDirty(self):
        return self._isDirty
    
    def set_isDirty(self,isDirty):
        timeline.enter('koDocumentBase.set_isDirty')
        self._isDirty = isDirty
        try:
            self.observerService.notifyObservers(self,'buffer_dirty',str(isDirty))
        except COMException, e:
            pass # no one is listening!
        if not self._isDirty:
            self.removeAutoSaveFile()
        timeline.leave('koDocumentBase.set_isDirty')

    def differentOnDisk(self):
        if self.isUntitled or \
            not self.file.isLocal or \
            self.file.isNetworkFile or \
            not self.file.exists or \
            self.file.URI.startswith('chrome://'):
            return 0
        # compare the md5 from the last examination of the disk file with
        # an md5 of the current contents of the disk file.  This does not
        # compare what is in the buffer in memory
        try:
            newmd5 = None
            try:
                self.file.open('rb')
            except:
                # the file is gone.
                newmd5 = None
                return newmd5 != self._lastmd5
            try:
                try:
                    ondisk = self.file.read(-1)
                    newmd5 = md5(ondisk).digest()
                except Exception, ex:
                    errmsg = "File differentOnDisk check failed: %s" % ex
                    log.error(errmsg)
                    self.lastErrorSvc.setLastError(nsError.NS_ERROR_FAILURE, errmsg)
                    raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
            finally:
                self.file.close()
            return newmd5 != self._lastmd5
        finally:
            self._lastmd5 = newmd5

    def get_baseName(self):
        if self.isUntitled:
            return self._untitledName
        else:
            return self.file.baseName

    def set_baseName(self, val):
        # Note: AFAICT this is never called. Not much use in it anyway. --TM (2010).
        if self.isUntitled:
            self._untitledName = val
        else:
            self.file.baseName = val

    def get_displayPath(self):
        if self.isUntitled:
            return self._untitledName
        else:
            return self.file.displayPath

    def get_language(self):
        return self._language
    
    def set_language(self,language):
        timeline.enter('koDocumentBase.set_language')
        log.info("setting language to " + language);
        self._language = language
        
        if language == '':
            if self.prefs.hasPrefHere('language'):
                self.prefs.deletePref('language')
            self._guessLanguage()
        else:
            self.prefs.setStringPref('language', language)
        self._setLangPrefs()

        self._initCIBuf() # need a new codeintel Buffer for this lang

        self._languageObj = None
        try:
            self.observerService.notifyObservers(self,'language_changed',language)
        except COMException, e:
            pass # no one is listening!
        timeline.leave('koDocumentBase.set_language')

    def get_languageObj(self):
        if self._language is None:
            log.error('Asked to get language Object with no language')
        if self._languageObj == None:
            registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                getService(components.interfaces.koILanguageRegistryService)
            self._languageObj = registryService.getLanguage(self._language)
        return self._languageObj

    # Note: The "get_subLanguage" and "languageForPosition" methods could also
    #       use the koIDocument.ciBuf.lang_from_pos() code, instead of their
    #       own implementation. To be kept in mind for re-factoring work.

    def get_subLanguage(self):
        if not self._language or not self._docPointer:
            return None
        languages = self.get_languageObj().getSubLanguages()
        if len(languages) < 2:
            return self._language
        # get the current position, and query the languageObj for what lang this is
        scimoz = self._views[0].scimoz
        pos = scimoz.currentPos
        if pos >= scimoz.length and pos > 0:
            pos = scimoz.positionBefore(scimoz.length)
        style = getActualStyle(scimoz, pos)
        family = udl_family_from_style(style)
        return self.get_languageObj().getLanguageForFamily(family)
        
    def languageForPosition(self, pos):
        if not self._language or not self._docPointer:
            return None
        languages = self.get_languageObj().getSubLanguages()
        if len(languages) < 2:
            return self._language
        # get the current position, and query the languageObj for what lang this is
        scimoz = self._views[0].scimoz
        if pos >= scimoz.length and pos > 0:
            pos = scimoz.positionBefore(scimoz.length)
        style = getActualStyle(scimoz, pos)
        family = udl_family_from_style(style)
        return self.get_languageObj().getLanguageForFamily(family)

    def get_codePage(self):
        return self._codePage
    
    def set_codePage(self, codePage):
        # We never allow a code page other than 65001 (aka put scintilla
        # in Unicode/UTF-8 mode).
        log.warn("setting `koDocument.codePage` is DEPRECATED, hardwired "
            "to 65001 (unicode mode): %r ignored", codePage)
        self._codePage = 65001

    def get_buffer(self):
        if self._docPointer:
            return self._views[0].scimoz.text
        return self._buffer
    
    def set_buffer(self, text, makeDirty=1):
        timeline.enter('koDocumentBase.set_buffer')
        # detect encoding and set codePage, buffer
        if text:
            if not isinstance(text, unicode):
                log.info('set_bufer got non unicode buffer, lets guess what it is...')
                encoded_buffer, encoding_name, bom = self._detectEncoding(text)
                self.encoding.python_encoding_name =\
                    self.encodingServices.get_canonical_python_encoding_name(encoding_name)
                self.encoding.use_byte_order_marker = bom
                try:
                    self.observerService.notifyObservers(self,'encoding_changed',self.encoding.python_encoding_name)
                except COMException, e:
                    pass # no one is listening!
            else:
                encoded_buffer = text
            self._set_buffer_encoded(encoded_buffer, makeDirty)
        else:
            self._set_buffer_encoded(text, makeDirty)
        log.info("set_buffer encoding %s codePage %r", self.encoding.python_encoding_name, self._codePage)
        self.prefs.setStringPref("encoding",
                                 self.encoding.python_encoding_name)
        timeline.leave('koDocumentBase.set_buffer')

    def _set_buffer_encoded(self,text,makeDirty=1):
        timeline.enter('koDocumentBase._set_buffer_encoded')
        was_dirty = self.get_isDirty()
        if self._docPointer:
            scimoz = self._views[0].scimoz
            cp = scimoz.currentPos
            an = scimoz.anchor
            fvl = scimoz.firstVisibleLine
            xoffset = scimoz.xOffset
            isReadOnly = scimoz.readOnly
            if isReadOnly:
                # We are setting or reloading the file contents, but this will
                # fail if the buffer is set to readonly. We do want to allow the
                # buffer to be modified in this instance.
                # http://bugs.activestate.com/show_bug.cgi?id=79961
                scimoz.readOnly = False
            scimoz.beginUndoAction()
            scimoz.text = text
            textLength = scimoz.textLength # length in bytes. =(
            scimoz.endUndoAction()
            if isReadOnly:
                scimoz.readOnly = True
            scimoz.currentPos = min(textLength, cp)
            scimoz.anchor = min(textLength, an)
            scimoz.lineScroll(0, min(fvl-scimoz.firstVisibleLine, scimoz.lineCount-scimoz.firstVisibleLine))
            scimoz.xOffset = xoffset
        else:
            self._buffer = text
        self.set_isDirty(was_dirty or makeDirty)
        try:
            self.observerService.notifyObservers(self,'buffer_changed','')
        except COMException, e:
            pass # no one is listening!
        timeline.leave('koDocumentBase._set_buffer_encoded')

    def get_bufferLength(self):
        # XXX as we add more methods, we'll need a better system
        if self._docPointer:
            return self._views[0].scimoz.textLength
        if self._buffer:
            return len(self._buffer)
        return 0

    def set_existing_line_endings(self, le):
        if le not in (eollib.EOL_LF, eollib.EOL_CR, eollib.EOL_CRLF):
            raise ServerException(nsError.NS_ERROR_FAILURE,
                                  "Invalid line ending: %s" % le)

        timeline.enter('koDocumentBase.set_existing_line_endings')
        if self._docPointer:
            scimoz = self._views[0].scimoz            
            scimoz.beginUndoAction()
            try:
                scimoz.convertEOLs(eollib.eol2scimozEOL[le])
            finally:
                scimoz.endUndoAction()
        else:
            self._buffer = eollib.convertToEOLFormat(self.get_buffer(), le)
        self.set_isDirty(1)
        try:
            self.observerService.notifyObservers(self,'buffer_changed','')
        except COMException, e:
            pass # no one is listening!
        timeline.leave('koDocumentBase.set_existing_line_endings')

    def get_existing_line_endings(self):
        endings, recommended = eollib.detectEOLFormat(self.get_buffer())
        if endings == eollib.EOL_NOEOL:
            return self.get_new_line_endings()
        else:
            return endings

    def get_new_line_endings(self):
        return self._eol

    def set_new_line_endings(self, le):
        if le not in (eollib.EOL_LF, eollib.EOL_CR, eollib.EOL_CRLF):
            raise ServerException(nsError.NS_ERROR_FAILURE,
                                  "Invalid new line ending: %s" % le)
        log.info("set_new_line_endings to '%s'", eollib.eol2eolName[le])
        self._eol = le
        for view in self._views:
            if view.scimoz:
                view.scimoz.eOLMode = eollib.eol2scimozEOL[le]

    def cleanLineEndings(self):
        # Two cases -- either there's a selection in which case we
        # want to do the operation only on the selection, or there
        # isn't, in which case we want to do it on the whole document
        scimoz = self._views[0].scimoz;
        if (scimoz.currentPos != scimoz.anchor):
            start = scimoz.selectionStart
            oldText = scimoz.getTextRange(scimoz.selectionStart,
                                          scimoz.selectionEnd);
            newText = eollib.convertToEOLFormat(oldText, self._eol)
            scimoz.replaceSel(newText)
            scimoz.anchor = start
            scimoz.currentPos = start + len(newText) 
        else:
            self.set_existing_line_endings(self._eol)

    
    #---- Encoding
    
    def _getStringPref(self, name, default=None):
        if self.prefs.hasPref(name):
            return self.prefs.getStringPref(name)
        return default

    def _getBooleanPref(self, name, default=0):
        if self.prefs.hasPref(name):
            return self.prefs.getBooleanPref(name)
        return default

    def _getEncodingFromName(self, name):
        try:
            registryService = components.classes['@activestate.com/koLanguageRegistryService;1'].\
                                getService(components.interfaces.koILanguageRegistryService)
            prefs = self._globalPrefs
            languagesPrefs = prefs.getPref('languages')
            language = registryService.suggestLanguageForFile(name)
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

    def _detectEncoding(self, buffer):
        if not isinstance(buffer,str):
            errstr = 'buffer is not a string!'
            log.error(errstr)
            self.lastErrorSvc.setLastError(nsError.NS_ERROR_FAILURE, errstr)
            raise ServerException(nsError.NS_ERROR_FAILURE, errstr)
        
        # returns encoded buffer, encoding name, and bom
        bom = 0
        encoding_name = self._getStringPref('encodingDefault')
        encoding = self.encodingServices.get_encoding_info(encoding_name)\
                       .python_encoding_name
        tryencoding = self._getStringPref('encoding')
        if tryencoding is None or tryencoding == encoding_name:
            tryencoding = self._getEncodingFromName(self.get_baseName())
        tryxmldecl = self._getBooleanPref('encodingXMLDec')
        trymeta = self._getBooleanPref('encodingHTML')
        trymodeline = self._getBooleanPref('encodingModeline')
        autodetect = self._getBooleanPref('encodingAutoDetect')
        # The job of this function is to, given a buffer (and knowing what
        # document we're loading),
        # - 1. Figure out what the encoding of the buffer is.
        # - 2. Convert it to Unicode
        # - 3. Store the encoding of the buffer in the document instance so
        #     that save operations can do the right thing and convert back
        #     if necessary
        
        # Detecting what encoding the buffer is in.  There are many sources
        # of information.
        # First, preferences -- if there is an encoding pref for this document, use it.
        # If there are no prefs, look for unambiguous markers of encoding. These
        # consist of:
        #   - BOM markers or XML declarations
        #   - lines like
        #            -*- coding: <encoding name> -*-
        #    as discussed in http://www.python.org/peps/pep-0263.html
        #    for Python, emacs
        log.info("""_detectEncoding
    encodingDefault: %s
           encoding: %s
        tryencoding: %s
         tryxmldecl: %r
            trymeta: %r
        trymodeline: %r
         autodetect: %r""",
         encoding_name, encoding, tryencoding,
         tryxmldecl, trymeta, trymodeline, autodetect)
        

        #    tryencoding = None
        if autodetect or tryencoding is not None:
            unicodebuffer, encoding, bom =\
                koUnicodeEncoding.autoDetectEncoding(buffer, tryxmldecl,
                                                     trymeta, trymodeline,
                                                     tryencoding,
                                                     encoding)
            log.info("_detectEncoding autoDetected %s", encoding)
            bom = len(bom) > 0
        else:
            try:
                if encoding.startswith('utf'):
                    unicodebuffer = unicode(buffer, encoding)
                    if (len(unicodebuffer) > 0):
                        encodingName, bomLength = koUnicodeEncoding.checkBOM(unicodebuffer)
                        if bomLength:
                            unicodebuffer = unicodebuffer[bomLength:]
                            bom = 1
                else:
                    # It's an unknown 8-bit encoding.  Assume it's the
                    # configured default, and convert to unicode
                    encoding = encoding_name
                    unicodebuffer = unicode(buffer, encoding_name)
            except UnicodeError:
                errstr = 'The file cannot be opened using the encoding "%s". '\
                    'You can change the encoding used to open files in the '\
                    '"File Settings" tab of the "Preferences" dialog.'\
                    % self.encodingServices.get_encoding_info(encoding)\
                          .friendly_encoding_name
                self.lastErrorSvc.setLastError(0, errstr)
                raise ServerException(nsError.NS_ERROR_FAILURE, errstr)
            
        # now we have a unicode buffer.

        if unicodebuffer is None:
            encName = self.encodingServices.get_encoding_info(encoding)\
                          .friendly_encoding_name
            raise ServerException(nsError.NS_ERROR_FAILURE, 'The file encoding "%s" is not supported.' % encName)

        log.info("_detectEncoding encoding is %s", encoding)
        # We've determined that the encoding of the file is whatever 'encoding' is.
        return unicodebuffer, encoding, bom

    def get_isEncodable(self):
        try:
            self._getEncodedBufferText()
            return 1
        except UnicodeError:
            return 0

    def forceEncodingFromEncodingName(self, encoding_name):
        encoding = components.classes['@activestate.com/koEncoding;1'].\
                                 createInstance(components.interfaces.koIEncoding)
        encoding.python_encoding_name = encoding_name
        self.set_encoding(encoding, 'replace')

    def setEncodingFromEncodingName(self, encoding_name):
        encoding = components.classes['@activestate.com/koEncoding;1'].\
                                 createInstance(components.interfaces.koIEncoding)
        encoding.python_encoding_name = encoding_name
        self.set_encoding(encoding)

    def setBufferAndEncoding(self, buffer, encoding_name):
        self._set_buffer_encoded('')
        if encoding_name:
            self.setEncodingFromEncodingName(encoding_name)
        else:
            encoded_buffer, encoding_name, bom = self._detectEncoding(buffer)
            self.encoding.python_encoding_name =\
                self.encodingServices.get_canonical_python_encoding_name(encoding_name)
            self.encoding.use_byte_order_marker = bom
        self._set_buffer_encoded(buffer)

    def set_encoding(self, encoding, errors="strict"):
        """Convert the current buffer to the given encoding.
        
            "encoding" is a koIEncoding to convert to.
            "errors" is identical to the "errors" argument to the Python
                .encode() string method. The Python docs say:
                    The default for errors is 'strict', meaning that
                    encoding errors raise a ValueError. Other possible
                    values are 'ignore' and 'replace'. 

        The python buffer is *always* in unicode format, so we want to
        encode to the new encoding, then get the unicode buffer and reset
        the buffer.
        
        This will raise a ServerException and set an error on
        koLastErrorService if there is an exception in the
        conversion. If the error code is zero then the error is an
        unexpected internal error and should be handled as such.
        """
        log.info("set_encoding(encoding=%r, errors=%r)", encoding.python_encoding_name, errors)
        lastErrorSet = 0 # set iff exception and last error has been set properly
        was_dirty = self.get_isDirty()
        make_dirty = 0
        try:
            if (self.encoding.python_encoding_name == encoding.python_encoding_name and
                self.encoding.use_byte_order_marker == encoding.use_byte_order_marker):
                # no change necessary
                return
    
            # Need to update the styleapplier here so we can set a new
            # encoding to the file.  This will replace fonts, etc.  as a
            # user changes the encoding.  We also have to handle
            # changing back and forth between utf-8 and single byte
            # encodings
            if self._views:
                self._views[0].scimoz.undoCollection = 0
            try:
                updateBuffer = 0
                unicodeBuffer = None
                if self.encoding.python_encoding_name != encoding.python_encoding_name:
                    buffer = self.get_buffer()
                    errmsg = None
                    log.info("buffer type is %s", type(buffer))
                    if buffer: # else no need to change anything.
                        
                        # 'buffer' is a unicode object.
                        #
                        # If we started out with UTF-*, then we can encode
                        # directly to the new encoding, and in fact must do it
                        # that way, since we cannot convert between raw utf-*
                        # and 8bit.
                        #
                        # We only need to change the file on disk when the
                        # encoding change would cause the file to contain
                        # different bytes. THis happens when converting between
                        # different utf-* encodings, or between utf-* and an
                        # 8bit encoding. So we do not dirty the buffer if both
                        # encodings are 8bit.
                        #
                        # When converting between utf-* encodings, the ucs2
                        # bytes will not change, so we do not need to update the
                        # buffer in scintilla. Also, when converting to utf-*
                        # from 8bit, our python buffer is already a unicode
                        # object, so no conversion is necessar.
                        
                        oldIsUTF = self.encoding.python_encoding_name.startswith('utf')
                        newIsUTF = encoding.python_encoding_name.startswith('utf')
                        bothUTF = oldIsUTF and newIsUTF
                        both8bit = not oldIsUTF and not newIsUTF
                        make_dirty = not both8bit
                        try:
                            from koUnicodeEncoding import recode_unicode
                            unicodeBuffer = recode_unicode(buffer,
                                                self.encoding.python_encoding_name,
                                                encoding.python_encoding_name,
                                                errors)
                        except (UnicodeError, COMException), ex:
                            errmsg = ("Unable to convert '%s' from '%s' to '%s'.  "
                                      "This encoding cannot represent all "
                                      "characters in the current buffer."
                                      % (self.get_baseName(),
                                         self.encoding.python_encoding_name,
                                         encoding.python_encoding_name))
                            self.lastErrorSvc.setLastError(1, errmsg)
                            lastErrorSet = 1
                            raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
                        updateBuffer = unicodeBuffer != buffer

                make_dirty = make_dirty or self.encoding.use_byte_order_marker != encoding.use_byte_order_marker
                self.encoding = encoding

                self._initCIBuf()

                self.prefs.setStringPref("encoding",
                                         self.encoding.python_encoding_name)

                # set the buffer after the code page is decided so scintilla has the
                # correct code page before we hand it the data
                if updateBuffer:
                    self._set_buffer_encoded(unicodeBuffer, 0)
                
                self.set_isDirty(was_dirty or make_dirty)
                try:
                    self.observerService.notifyObservers(self,
                        'encoding_changed',
                        self.encoding.python_encoding_name)
                except COMException, ex:
                    pass # no one is listening
            finally:
                if self._views:
                    self._views[0].scimoz.undoCollection = 1
        except:
            if not lastErrorSet: # then this is an internal error
                exc_info = sys.exc_info()
                errno = 0
                errmsg = "internal error setting encoding of '%s' to '%s': %s" % \
                         (self.get_baseName(),
                          encoding.python_encoding_name, exc_info[1])
                log.exception(errmsg)
                self.lastErrorSvc.setLastError(errno, errmsg)
            raise
    
    def _getEncodedBufferText(self, mode='strict', encoding_name=None):
        try:
            if not encoding_name:
                encoding_name = self.encoding.python_encoding_name
            bl = self.get_bufferLength()
            decodedText = self.get_buffer().encode(encoding_name,mode)
            if self.encoding.use_byte_order_marker:
                decodedText = self.encoding.encoding_info.byte_order_marker + decodedText
            if bl and not len(decodedText):
                # lengths may be different after encoding
                errmsg = "Unable to encode the buffer to %s" % encoding_name
                self.lastErrorSvc.setLastError(0, errmsg)
                raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
            return decodedText, self.get_codePage()
        except UnicodeError, e:
            log.error("Unable to decode document to '%s' encoding", encoding_name)
            raise

    def removeUnencodeable(self):
        """Remove characters from the buffer that are not encodeable with the
        current encoding.
        """
        try:
            encoding_name = self._getStringPref('encoding')
            if not encoding_name:
                # Bug 65746: This was not reproducable on our systems,
                # but fixes the problem for a user with a Danish locale.
                log.warn("No encoding name is available, defaulting to %s",
                    self.encoding.python_encoding_name)
                encoding_name = self.encoding.python_encoding_name
            decodedText = self.get_buffer().encode(encoding_name, 'replace')
            if self.encoding.use_byte_order_marker:
                encoding_info = self.encodingServices.get_encoding_info(encoding_name)\
                           .python_encoding_name
                self.encoding.use_byte_order_marker = encoding_info.byte_order_marker != ''
            self._set_buffer_encoded(unicode(decodedText, encoding_name))
        except Exception, e:
            log.exception(e)
            raise

    def get_encodedText(self):
        return self._getEncodedBufferText()[0]

    def get_utf8Text(self):
        return self._getEncodedBufferText(encoding_name='utf-8')[0]

    _cleanLineRe = re.compile("(.*?)([ \t]+?)?(\r\n|\n|\r)", re.MULTILINE)
    def _clean(self, ensureFinalEOL, cleanLineEnds):
        """Clean the current document content.
        
            "ensureFinalEOL" is a boolean indicating if "cleaning" should
                ensure the file content ends with an EOL.
            "cleanLineEnds" is a boolean indicating if "cleaning" should
                remove trailing whitespace on all lines.
        
        There is one exception to "cleanLineEnds": trailing whitespace
        before the current cursor position on its line is not removed
        (bug 32702).
        
        This function preserves the current cursor position and selection,
        if any, and should maintain fold points and markers.
        """
        if not self._views:
            return
        scintilla = self._views[0]
        # In the case of any failure at all, we don't change the text.
        try:
            DEBUG = 0
            if DEBUG: print "-"*50 + " _clean:"

            # Protect settings: selection, cursor position, etc.
            scimoz = scintilla.scimoz
            currPos = scimoz.currentPos
            currPosLine = scimoz.lineFromPosition(currPos)
            currPosCol = currPos - scimoz.positionFromLine(currPosLine)
            anchorLine = scimoz.lineFromPosition(scimoz.anchor)
            anchorCol = scimoz.anchor - scimoz.positionFromLine(anchorLine)
            firstVisibleLine = scimoz.firstVisibleLine

            # Clean the document content.
            scimoz.beginUndoAction()
            try:
                import eollib
                eolStr = eollib.eol2eolStr[eollib.scimozEOL2eol[scimoz.eOLMode]] # '\r\n' or '\n'...
                if cleanLineEnds:
                    if DEBUG: print "LINE  POSITION  CONTENT"
                    pattern = re.compile("(.*?)([ \t]+)?(\r\n|\n|\r)?$")
                    index = scimoz.length # scimoz.length in _bytes_??
                    for i in range(scimoz.lineCount-1, -1, -1):
                        length, line = scimoz.getLine(i) # length is in _bytes_
                        if DEBUG:
                            span = "%d-%d" % (index-length, index)
                            print "%3d: %9s: %r" % (i, span, line)
                        match = pattern.match(line)
                        content, trailingWS, eol = match.groups()
                        if eol and eol != eolStr:
                            end = index
                            start = end - len(eol)
                            if DEBUG:
                                print "REPLACE EOL: %d-%d: %r -> %r"\
                                      % (start, end, eol, eolStr)
                            scimoz.targetStart, scimoz.targetEnd = start, end
                            scimoz.replaceTarget(len(eolStr), eolStr)
                        if trailingWS:
                            end = index
                            if eol: end -= len(eol)
                            start = end - len(trailingWS)
                            if i == currPosLine:
                                start = max(start, currPos)
                            if DEBUG:
                                print "REMOVE TRAILING WHITESPACE: %d-%d: %r"\
                                      % (start, end, scimoz.getTextRange(start, end))
                            scimoz.targetStart, scimoz.targetEnd = start, end
                            scimoz.replaceTarget(0, '')
                        index -= length
                if ensureFinalEOL:
                    sciLength = scimoz.length
                    if sciLength >= 2:
                        lastBit = scimoz.getTextRange(sciLength - 2, sciLength)
                    else:
                        lastBit = scimoz.text
                    if not lastBit.endswith(eolStr):
                        if DEBUG:
                            print "INSERT FINAL EOL: %r" % eolStr
                        scimoz.insertText(sciLength, eolStr)
                if cleanLineEnds:
                    
                    # If the buffer ends with > 1 blank line,
                    # Replace all of them with whatever the last line happens
                    # to be -- this keeps us from creating buffers that
                    # don't end with a newline, even if the user chose the
                    # cleanLineEnds option but not the ensureFinalEOL option.

                    # If there's a selection, stop at the line after it.
                    # Same with breakpoints, bookmarks, and the current
                    # position.  The idea is to quietly remove empty lines
                    # at the end of a file, when the user is higher up.

                    firstDeletableLine = scimoz.lineFromPosition(max(currPos, scimoz.selectionEnd)) + 1
                    for i in range(scimoz.lineCount - 1, firstDeletableLine - 1, -1):
                        if scimoz.markerGet(i):
                            firstLineToDelete = i + 1
                            break
                        length, line = scimoz.getLine(i) # length is in _bytes_
                        if re.search(r'\S', line):
                            firstLineToDelete = i + 1
                            break
                    else:
                        firstLineToDelete = firstDeletableLine

                    if firstLineToDelete < scimoz.lineCount - 1:
                        # Delete all lines from pos(line[i][0]) to
                        # pos(line[count - 1][0]) - 1 unless the
                        # selection/cursor is in that range
                        startPos = scimoz.positionFromLine(firstLineToDelete)
                        endPos = scimoz.positionFromLine(scimoz.lineCount - 1)
                        if endPos > startPos:
                            scimoz.targetStart, scimoz.targetEnd = startPos, endPos
                            scimoz.replaceTarget(0, '')
                            
            finally:
                scimoz.endUndoAction()

            # Restore settings: selection, cursor position, etc.
            scimoz.currentPos = scimoz.positionFromLine(currPosLine) + currPosCol
            scimoz.anchor = scimoz.positionFromLine(anchorLine) + anchorCol
            scimoz.lineScroll(0, min(firstVisibleLine-scimoz.firstVisibleLine,
                                     scimoz.lineCount-scimoz.firstVisibleLine))
            if DEBUG: print "-"*60
        except Exception, e:
            #XXX This is poor error handling.
            log.exception(e)
        
    def save(self, forceSave):
        mode = None
        if self.file.exists and not self.file.isWriteable:
            if not forceSave:
                errmsg = "File is not writeable"
                self.lastErrorSvc.setLastError(0, errmsg)
                raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
                
            mode = self.file.permissions
            # if we're not the owner, we shouldn't be able to write anyway
            desired_mode = mode | stat.S_IWUSR
            try:
                os.chmod(self.file.path, desired_mode)
            except EnvironmentError, ex:
                errmsg = "Unable to set the file mode to writeable: %s" % ex
                self.lastErrorSvc.setLastError(0, errmsg)
                raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
                
            # .hasChanged has the side-effect of re-stat'ing, which is
            # required for the subsequent check. Psychotically, this is
            # the only way to initiate a re-stat.
            # Don't do this for non-local files
            if self.file.isLocal:
                self.file.hasChanged 
            if not self.file.isWriteable:
                # reset the mode
                try:
                    os.chmod(self.file.path, mode)
                except EnvironmentError:
                    pass # skip because we are already in an error mode
                
                errmsg = "Unable to set the file mode to writeable: chmod "\
                         "succeeded but a subsequent stat says the file "\
                         "is still not writeable"
                self.lastErrorSvc.setLastError(0, errmsg)
                raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
                
        try:
            ensureFinalEOL = self._globalPrefs.getBooleanPref("ensureFinalEOL")
            cleanLineEnds = self._globalPrefs.getBooleanPref("cleanLineEnds")
            if ensureFinalEOL or cleanLineEnds:
                try:
                    li = self.lidb.langinfo_from_komodo_lang(self.get_language())
                except langinfo.LangInfoError:
                    # Bug 82512: if it's an unknown language, assume
                    # it's safe to remove extra whitespace.
                    cleanWhiteSpace = True
                else:
                    cleanWhiteSpace = not li.has_significant_trailing_ws
                if cleanWhiteSpace:
                    self._clean(ensureFinalEOL, cleanLineEnds)
    
            # translate the buffer before opening the file so if it
            # fails, we haven't truncated the file
            data = self._getEncodedBufferText()[0]

            if not self.file.isLocal:
                self.doAutoSave()

            try:
                self.file.open('wb+')
                try:
                    self.file.write(data)
                finally:
                    self.file.close()
            except COMException, ex:
                # .open(), .write(), and .close() will setLastError on
                # failure so don't set it again. You will just override
                # better data.
                log.exception("save: can't write to file %r",
                              self.get_displayPath())
                raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))

            self._lastmd5 = md5(data).digest()
            self.set_isDirty(0)
            self.setSavePoint()

            try:
                self._obsSvc.notifyObservers(self, "file_changed",
                                             self.file.URI)
            except:
                pass # ignore, noone listening
        finally:
            # fix file mode
            if forceSave and mode:
                try:
                    os.chmod(self.file.path, mode)
                except:
                    errmsg = "Unable to reset the file mode."
                    self.lastErrorSvc.setLastError(0, errmsg)
                    raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
            self.removeAutoSaveFile()

    def revert(self):
        log.info("revert starting...%s", self.encoding.python_encoding_name)
        self._loadfile(self.file)
        self.setSavePoint()
        self.removeAutoSaveFile()
        log.info("revert done...%s", self.encoding.python_encoding_name)

    def setSavePoint(self):
        if self._views:
            # All views share the same doc pointer.
            self._views[0].scimoz.setSavePoint()

    def saveState(self, scintilla):
        try:
            self.docSettingsMgr.applyViewSettingsToDocument(scintilla)
        except Exception, e:
            # this failure will block closing a file if something is wrong,
            # log it and move on
            log.exception(e)

    # The document manages a reference count of the views onto that
    # document. When the last view 
    def addView(self, scintilla):
        timeline.enter('koDocumentBase.AddView')
        self._views.append(scintilla)
        scimoz = scintilla.scimoz
        xpself = WrapObject(self, components.interfaces.koIDocument)
        if not self._docPointer:
            scimoz.docPointer = 0 # create document
            self.docSettingsMgr.register(xpself, scintilla)
            self._buffer = None # clear out any old buffer we may have had
            self._docPointer = scimoz.docPointer
            scimoz.addRefDocument(self._docPointer)
        else:
            scimoz.addRefDocument(self._docPointer)
            scimoz.docPointer = self._docPointer
            self.docSettingsMgr.register(xpself, scintilla)
        scimoz.codePage = self._codePage
        log.info("in AddView")
        timeline.leave('koDocumentBase.AddView')
    
    def releaseView(self, scintilla):
        timeline.enter('koDocumentBase.releaseView')
        try:
            #print "Releasing View"
            if scintilla not in self._views:
                raise ServerException(nsError.NS_ERROR_FAILURE,'SciMoz does not reference.')
            self.docSettingsMgr.unregister(scintilla)
            scimoz = scintilla.scimoz
            scimoz.releaseDocument(self._docPointer);
            if len(self._views) == 1:
                buffer = self.get_buffer()
                self._docPointer = None
                self._set_buffer_encoded(buffer, 0)
                if self.file and self.file.URI:
                    # Don't adjust markers for untitled or diff buffers, etc.
                    self._historySvc.update_marker_handles_on_close(self.file.URI, scimoz)
    
            self._views.remove(scintilla)
            #if not self._views:
            #    self.docSettingsMgr = None
        except Exception, e:
            log.exception(e)
            raise
        timeline.leave('koDocumentBase.releaseView')

    def getView(self):
        try:
            return self._views[0]
        except IndexError, ex:
            raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))

    def get_numScintillas(self):
        return len(self._views)

    # we want to watch for changes in the prefs we derive from
    def observe(self, subject, topic, data):
        #print "observe: subject:%r, topic:%s, data:%r" % (subject, topic, data)
        if data == 'useTabs':
            self._useTabs = self.prefs.getBooleanPref('useTabs')
        elif data == 'indentWidth':
            val = self._indentWidth = self.prefs.getLongPref('indentWidth')
            for view in self._views:
                view.scimoz.indent = val
        elif data == 'tabWidth':
            val = self._tabWidth = self.prefs.getLongPref('tabWidth')
            for view in self._views:
                view.scimoz.tabWidth = val

    #attribute string URI; 
    def get_useTabs(self):
        if self._useTabs is None:
            # first try doc prefs if available
            if self.prefs.hasPrefHere('useTabs'):
                self._useTabs = self.prefs.getBooleanPref('useTabs')
            elif self.prefs.hasPref('useSmartTabs') and \
                self.prefs.getBooleanPref('useSmartTabs'):
                self._guessFileIndentation()
            else:
                # global, not document prefs
                self._useTabs = self.prefs.getBooleanPref('useTabs')
        return self._useTabs
  
    def set_useTabs(self, value):
        self.prefs.setBooleanPref('useTabs', value) # will affect _useTabs through prefs observers

    def get_indentWidth(self):
        
        timeline.enter('koDocumentBase.get_indentWidth')
        try:
            if self._indentWidth is None:
                log.info("_indentWidth is None")
                if self.prefs.hasPrefHere('indentWidth'):
                    # get from document prefs
                    self._indentWidth = self.prefs.getLongPref('indentWidth')
                    log.info('got _indentWidth from prefs: %r' % self._indentWidth)
                elif self.prefs.hasPref('useSmartTabs') and \
                    self.prefs.getBooleanPref('useSmartTabs'):
                    self._guessIndentWidth()
                else:
                    # get from global prefs
                    self._indentWidth = self.prefs.getLongPref('indentWidth')
            else:
                log.info("_indentWidth is not none, it's %s" % self._indentWidth)
        finally:
            timeline.leave('koDocumentBase.get_indentWidth')
        return self._indentWidth

    def set_indentWidth(self, value):
        self._indentWidth = value
        self.prefs.setLongPref('indentWidth', value) # will affect _useTabs through prefs observers

    def get_tabWidth(self):
        if self._tabWidth is None:
            self._tabWidth = self.prefs.getLongPref('tabWidth')
        return self._tabWidth

    def set_tabWidth(self, value):
        self._tabWidth = value
        self.prefs.setLongPref('tabWidth', value) # will affect _useTabs through prefs observers

    def _guessFileIndentation(self):
        timeline.enter('koDocumentBase._guessFileIndentation')
        # Heuristic to determine what file indentation settings the user
        # likely wants for this file.
        log.info("in _guessFileIndentation")
        useTabs = usesSpaces = linesChecked = 0
        buffer = self.get_buffer()
        if self._indentWidth is None:
            self.get_indentWidth() # will be guessed if not in prefs
            log.info("guessed indentWidth to be: %s" % self._indentWidth)

        # In the first 150 lines of the file, search for the non-blank
        # lines with leading white-space.  Searching farther takes too long.
        for line in buffer.splitlines()[:150]:
            if line[:1] == "\t":
                # If first char is a tab, recognize that and move on
                linesChecked += 1
                useTabs = 1
            elif line[:2] == "  ":
                # If first 2 chars are spaces, recognize that and move on
                # Require at least two spaces on the line to count it
                linesChecked += 1
                usesSpaces = 1
            if linesChecked == 25:
                # Only check up to 25 lines with indentation
                break

        if linesChecked:
            log.info("guessed useTabs = %d and usesSpaces = %d",
                     useTabs, usesSpaces)
            # We found some lines with indentation
            if useTabs and usesSpaces:
                # If we found both space and tab indentation, leave the
                # indentWidth setting as default, fall back to prefs
                # to decide which to use
                self._useTabs = self.prefs.getBooleanPref("useTabs")
                for v in self._views:
                    v.scimoz.indent = self._indentWidth
                    v.scimoz.useTabs = self._useTabs
            elif useTabs:
                # If only tab indentation was found, set the indentWidth
                # to the tabWidth, so we essentially always use tabs.
                self._useTabs = 1
                self.set_useTabs(self._useTabs)
                self.set_indentWidth(self.get_tabWidth())
                for v in self._views:
                    v.scimoz.indent = self._indentWidth
                    v.scimoz.useTabs = 1
            else:
                if usesSpaces:
                    self._useTabs = 0
                    self.set_useTabs(self._useTabs)
                else:
                    # indeterminate, so use global prefs to decide
                    self._useTabs = self.prefs.getBooleanPref("useTabs")
                for v in self._views:
                    v.scimoz.useTabs = self._useTabs
        else:
            # Lacking better information, fallback to the pref values.
            if self._useTabs is None:
                self._useTabs = self.prefs.getBooleanPref("useTabs")
            if self._indentWidth is None:
                self._indentWidth = self.prefs.getLongPref("indentWidth")
            if self._tabWidth is None:
                self._tabWidth = self.prefs.getLongPref("tabWidth")
            for v in self._views:
                #XXX This is being a bit paranoid here. I am not sure if
                #    this method need worry about writing self._tabWith
                #    through to scimoz. David? --TM
                v.scimoz.useTabs = self._useTabs
                v.scimoz.indent = self._indentWidth
                v.scimoz.tabWidth = self._tabWidth
        timeline.leave('koDocumentBase._guessFileIndentation')

    # Guess indent-width from text content. (Taken from IDLE.)
    #
    # This should not be believed unless it's in a reasonable range
    # (e.g., it will be 0 if no indented blocks are found).
    def _guessIndentWidth(self):
        text = self.get_buffer()
        if text == '':
            indentWidth = self.prefs.getLongPref('indentWidth')
            self._indentWidth= indentWidth
            return
        # if we don't have a view yet, we can't do anything.
        if not self._views:
            log.error("Was asked to guess indent width before there's a view")
            self._indentWidth = self.prefs.getLongPref('indentWidth')
            return
        if not self._languageObj:
            self.get_languageObj()
        # The strategy for guessing the indentation is delegated to the
        # lexer language service, since different languages have very
        # different rules.
        indentWidth = 0
        useTabs = 0
        defaultUseTabs = self.prefs.getBooleanPref("useTabs")
        try:
            indentWidth, useTabs = \
                self._languageObj.guessIndentation(self._views[0].scimoz,
                                                   self.get_tabWidth(),
                                                   defaultUseTabs)
        except Exception, e:
            log.error("Unable to guess indentation")
            
        if indentWidth == 0:  # still haven't found anything, so go with the prefs.
            indentWidth = self.prefs.getLongPref('indentWidth')
            useTabs = defaultUseTabs

        log.info("_guessIndentWidth: indentWidth=%d, useTabs=%d",
                 indentWidth, useTabs)
        self.set_indentWidth(indentWidth)
        self._useTabs = useTabs
        self.set_useTabs(useTabs)

    def _statusBarMessage(self, message):
        sm = components.classes["@activestate.com/koStatusMessage;1"]\
             .createInstance(components.interfaces.koIStatusMessage)
        sm.category = "Document"
        sm.msg = message
        sm.timeout = 5000 # 0 for no timeout, else a number of milliseconds
        sm.highlight = 1  # boolean, whether or not to highlight
        try:
            self._obsSvcProxy.notifyObservers(sm, 'status_message', None)
        except COMException, e:
            # do nothing: Notify sometimes raises an exception if (???)
            # receivers are not registered?
            pass
        
    def getUnsavedChanges(self):
        eolStr = eollib.eol2eolStr[self._eol]
        inmemory = self.get_buffer().splitlines(1)

        # We want a new temporary file to read, so the current file stats
        # information does not get updated (required for remote file saving,
        # which uses stats.mtime for checking if a file has changed or not).
        tmpfile = \
            components.classes["@activestate.com/koFileEx;1"] \
            .createInstance(components.interfaces.koIFileEx)
        tmpfile.URI = self.file.URI
        tmpfile.open('rb')
        try:
            ondisk = tmpfile.read(-1)
            (ondisk, encoding, bom) = self._detectEncoding(ondisk)
            ondisk = ondisk.splitlines(1)
        finally:
            tmpfile.close()        #self.file.open('rb')

        difflines = list(difflibex.unified_diff(
            ondisk, inmemory,
            self.file.displayPath, self.file.displayPath+" (unsaved)",
            lineterm=eolStr))
        # Add index line so diff parsing for "Reveal position in editor"
        # feature can infer the correct path (otherwise gets " (unsaved)"
        # as part of it).
        difflines.insert(0, "Index: "+self.file.displayPath+eolStr)
        return ''.join(difflines)

    def _getAutoSaveFileName(self):
        koDirs = components.classes["@activestate.com/koDirs;1"].\
                 getService(components.interfaces.koIDirs)
        dname = os.path.join(koDirs.userDataDir,  "autosave")
        if not os.path.exists(dname):
            os.mkdir(dname)
        # retain part of the readable name
        autoSaveFilename = "%s-%s" % (self.file.md5name,self.file.baseName)
        return os.path.join(dname, autoSaveFilename)
        
    def _getAutoSaveFile(self):
        autoSaveFile = components.classes["@activestate.com/koFileEx;1"] \
                      .createInstance(components.interfaces.koIFileEx)
        autoSaveFile.URI = self._getAutoSaveFileName()
        return autoSaveFile

    # this should only called when doing a revert or save in this file,
    # or from the viewManager canClose handler.
    def removeAutoSaveFile(self):
        if self.isUntitled: return
        autoSaveFile = self._getAutoSaveFile()
        if not autoSaveFile.exists:
            return
        os.remove(autoSaveFile.path)
        
    def haveAutoSave(self):
        if self.isUntitled: return 0
        # set the autosave file name
        autoSaveFile = self._getAutoSaveFile()
        
        if autoSaveFile.exists:
            if autoSaveFile.lastModifiedTime >= self.file.lastModifiedTime:
                #print "tmpfile is newer than original"
                return 1;
            else:
                # we have an autosave file, but it's old, delete it
                #print "removing old temporary auto save file ", autoSaveFile.path
                os.remove(autoSaveFile.path)
        return 0
    
    def doAutoSave(self):
        timeline.enter('koDocumentBase.doAutoSave')
        try:
            # no point in autosaving if we're not dirty
            if not self._isDirty or self.isUntitled or not self._wrapSelf: return
            
            autoSaveFile = self._getAutoSaveFile()
            log.debug("last save %d now %d", autoSaveFile.lastModifiedTime, time.time())
            
            # translate the buffer before opening the file so if it
            # fails, we haven't truncated the file
            try:
                data = self._wrapSelf.encodedText
            except Exception, e:
                try:
                    # failed to get encoded text, save it using utf-8 to avoid
                    # data loss (bug 40857)
                    data = self._wrapSelf.utf8Text;
                    self._statusBarMessage("Using UTF-8 to autosave '%s'" %
                                  self._wrapSelf.baseName)
                except Exception, e:
                    log.exception(e)
                    self._statusBarMessage("Error getting encoded text for autosave of '%s'" %
                                  self._wrapSelf.baseName)
                    return
   
            try:
                log.debug("autosaving [%s]", autoSaveFile.URI)
                autoSaveFile.open('wb+')
                try:
                    autoSaveFile.write(data)
                finally:
                    autoSaveFile.close()
            except:
                # .open(), .write(), and .close() will setLastError on
                # failure so don't set it again. You will just override
                # better data.
                self._statusBarMessage("Unable to autosave file '%s'" %
                              self._wrapSelf.baseName)
                return
        finally:
            #log.debug("doAutoSave finally")
            timeline.leave('koDocumentBase.doAutoSave')
    
    def restoreAutoSave(self):
        if self.isUntitled: return
        timeline.enter('koDocumentBase.restoreAutoSave')
        try:
            autoSaveFile = self._getAutoSaveFile()
            self._loadfile(autoSaveFile)
            self.set_isDirty(1)
            # fix the file content md5
            data = self._get_buffer_from_file(self.file)
            self._lastmd5 = md5(data).digest()
        finally:
            timeline.leave('koDocumentBase.restoreAutoSave')
            
    # Methods for maintaining the state of tabstop insertion
    # on the document.  When self._tabstopInsertionNodes is
    # null there are no tabstops to process.

    def getTabstopInsertionTable(self):
        return self._tabstopInsertionNodes

    def clearTabstopInsertionTable(self):
        self._tabstopInsertionNodes = None

    def setTabstopInsertionTable(self, tabstopInsertionNodes):
        if len(tabstopInsertionNodes):
            self._tabstopInsertionNodes = tabstopInsertionNodes
        else:
            self._tabstopInsertionNodes = None

    def removeTabstopInsertionNodeAt(self, idx):
        del self._tabstopInsertionNodes[idx]

    def get_hasTabstopInsertionTable(self):
        return self._tabstopInsertionNodes is not None

    def _distinguishPythonVersion(self, buffer):
        """
        Look for python-3 markers first
        """
        import pythonVersionUtils
        isPython3 = pythonVersionUtils.isPython3(buffer)
        if isPython3:
            return ["Python3"]
        else:
            return ["Python"]
