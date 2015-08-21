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
import stat, os, time

import eollib
import difflibex
import langinfo
from zope.cachedescriptors.property import Lazy as LazyProperty
from zope.cachedescriptors.property import LazyClassAttribute
from koUDLLanguageBase import udl_family_from_style
import koUnicodeEncoding, codecs, types

log = logging.getLogger('koDocument')
#log.setLevel(logging.DEBUG)


################################################################################
# Note that koDocument's scintilla/scimoz attribute is thread-protected, all
# calls that koDocument makes using scintilla/scimoz will be proxied to the main
# thread, as scintilla/scimoz can only be used on the main thread.
#
# If you obtain scimoz from a koDocument, you must ensure you proxy calls to it
# using the main thread.
################################################################################

class DontDeleteEndLines(Exception):
    """ Used as an intra-method return """
    pass

class koDocumentBase(object):
    _com_interfaces_ = [components.interfaces.koIDocument,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Document"
    _reg_contractid_ = "@activestate.com/koDocumentBase;1"
    _reg_clsid_ = "{A9F51FD2-CF82-4290-87B8-BD07CEBD1CD1}"

    re_firstline = re.compile(ur'(.*?)(?:\r|\n|$)')
    _lang_prefs = None
    _indentWidth = None
    _tabWidth = None
    _useTabs = None

    # The original unicode (decoded) on-disk file lines.
    ondisk_lines = None

    _DOCUMENT_SIZE_NOT_LARGE = 0
    _DOCUMENT_SIZE_UDL_LARGE = 1
    _DOCUMENT_SIZE_ANY_LARGE = 2

    # Cached services - saved on the class.
    _globalPrefSvc = None
    _globalPrefs = None
    _partSvc = None

    # Lazily loaded class variables.
    @LazyClassAttribute
    def lidb(self):
        return langinfo.get_default_database()
    @LazyClassAttribute
    def _globalPrefSvc(self):
        return components.classes["@activestate.com/koPrefService;1"].\
                    getService(components.interfaces.koIPrefService)
    @LazyClassAttribute
    def _globalPrefs(self):
        return self._globalPrefSvc.prefs
    @LazyClassAttribute
    def _partSvc(self):
        return components.classes["@activestate.com/koPartService;1"].\
                    getService(components.interfaces.koIPartService)
    @LazyClassAttribute
    def encodingServices(self):
        return components.classes['@activestate.com/koEncodingServices;1'].\
                    getService(components.interfaces.koIEncodingServices)
    @LazyClassAttribute
    def lastErrorSvc(self):
        return components.classes["@activestate.com/koLastErrorService;1"].\
                    getService(components.interfaces.koILastErrorService)
    @LazyClassAttribute
    def _obsSvc(self):
        return components.classes['@mozilla.org/observer-service;1'].\
                    getService(components.interfaces.nsIObserverService)
    @LazyClassAttribute
    def _historySvc(self):
        return components.classes["@activestate.com/koHistoryService;1"].\
                    getService(components.interfaces.koIHistoryService)
    @LazyClassAttribute
    def codeIntelSvc(self):
        return components.classes['@activestate.com/koCodeIntelService;1'].\
                    getService(components.interfaces.koICodeIntelService)
    @LazyClassAttribute
    def langRegistrySvc(self):
        return components.classes['@activestate.com/koLanguageRegistryService;1'].\
                    getService(components.interfaces.koILanguageRegistryService)
    @LazyClassAttribute
    def fileSvc(self):
        return components.classes["@activestate.com/koFileService;1"].\
                    getService(components.interfaces.koIFileService)
    @LazyClassAttribute
    def autoSaveDirectory(self):
        """Where koDocument auto-save is stored."""
        koDirs = components.classes["@activestate.com/koDirs;1"].\
                 getService(components.interfaces.koIDirs)
        dname = os.path.join(koDirs.userDataDir,  "autosave")
        # Ensure the directory exists.
        if not os.path.exists(dname):
            os.mkdir(dname)
        return dname

    # Lazily loaded instance variables.
    @LazyProperty
    def observerService(self):
        # yes, createInstance.  We want to provide our own observer services
        # for documents
        return components.classes['@activestate.com/koObserverService;1'].\
                    createInstance(components.interfaces.nsIObserverService)
    @LazyProperty
    def docSettingsMgr(self):
        return components.classes['@activestate.com/koDocumentSettingsManager;1'].\
            createInstance(components.interfaces.koIDocumentSettingsManager)

    def __init__(self):
        self._buffer = None # string The contents of the document
        self._codePage = 65001 # Komodo always uses 65001 (i.e. scintilla UTF-8 mode)
        self.encoding = None # string The name of the Unicode encoding
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
        # _lastModifiedTime is the last time the file was modified, which is
        # used for remote files in the differentOnDisk() check.
        self._lastModifiedTime = None

        self._refcount = 0
        self._ciBuf = None

        self._tabstopInsertionNodes = None

        self.isLargeDocument = False
        self._documentSizeFactor = self._DOCUMENT_SIZE_NOT_LARGE

        # This field can be used to override the default lexer set in the
        # document's language service.  Useful for using a different colorizer,
        # usually text for a large document.
        self.lexer = None

    def _dereference(self):
        prefObserver = self.prefs.prefObserverService
        prefObserver.removeObserverForTopics(self, ['useTabs', 'indentWidth', 'tabWidth'])
        self._ciBuf = None

    @property
    def ciBuf(self):
        if self._ciBuf is None:
            self._ciBuf = self.codeIntelSvc.buf_from_koIDocument(self)
        return self._ciBuf

    def initWithFile(self, file, untitled):
        log.info("initWithFile(file=%s, ...)", file.URI)
        self.isUntitled = untitled
        self.file = file
        self._setupPrefs()
        if self._language is None:
            self._guessLanguage()

        self.prefs.setLongPref('kodoc_file_last_opened', time.time())
        self.setFileAccessed()

        # This gets called again unnecessarily in self.load(). Can't
        # follow the koDocument spaghetti to be assured that
        # self._ciBuf is reset for all cases.
        self._ciBuf = None

    def initUntitled(self, name, encoding):
        log.info("initUntitled(name=%r, ...)", name)
        self.isUntitled = 1
        self._untitledName = name
        self._setupPrefs(encoding)
        self.set_buffer("", 0)  # make sure new buffer is not dirty
        if self._language is None:
            self._guessLanguage()
        self._ciBuf = None

    def addReference(self):
        self._refcount += 1
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

    #def resetPrefs(self):
    #    docStateMRU = self._globalPrefSvc.getPrefs("docStateMRU");
    #    if not self.isUntitled and docStateMRU.hasPref(self.file.URI):
    #        docStateMRU.deletePref(self.file.URI)
    #    if self.prefs:
    #        prefObserver = self.prefs.prefObserverService
    #        prefObserver.removeObserver(self, 'useTabs')
    #        prefObserver.removeObserver(self, 'indentWidth')
    #        prefObserver.removeObserver(self, 'tabWidth')
    #    try:
    #        encoding_name = self.encoding.python_encoding_name
    #    except:
    #        encoding_name = None
    #    self._setupPrefs(encoding_name)
        
    def _getEncodingNameForNewFile(self, language):
        if not language:
            language = self.langRegistrySvc.suggestLanguageForFile(self.get_displayPath())
            if not language:
                language = 'Text'
        prefName = "languages/%s/newEncoding" % (language,)
        encoding = self.prefs.getString(prefName, "Default Encoding")
        if encoding != "Default Encoding":
            return encoding
        # Try again on the global prefs
        encoding = self._globalPrefs.getString(prefName, "Default Encoding")
        if encoding != "Default Encoding":
            return encoding
        
        # Attempt to work around issue with file prefs that we have not yet been
        # able to isolate: https://github.com/Komodo/KomodoEdit/issues/217
        try:
            return self.prefs.getString('encodingDefault')
        except nsError.NS_ERROR_UNEXPECTED:
            return self._globalPrefs.getString('encodingDefault')
    
    def _setupPrefs(self, encoding_name=None):
        """ We can only setup the prefs on the document once we have a URI for it
        So after __init__, self.prefs is None, until we get an "initWith....()" call.
        Note that some things like encoding derive from prefs.
        """
        # Create a preference set to hold doc preferences
        docStateMRU = UnwrapObject(self._globalPrefSvc.getPrefs("docStateMRU"))
        if not self.isUntitled and docStateMRU.hasPref(self.file.URI):
            url = self.file.URI
            self.prefs = docStateMRU.getPref(url)
        else:
            self.prefs = components.classes['@activestate.com/koFilePreferenceSet;1'].\
                                     createInstance(components.interfaces.koIFilePreferenceSet)
            if self.isUntitled:
                self.prefs.id = self._untitledName
            else:
                self.prefs.id = self.file.URI
            docStateMRU.setPref(self.prefs)
            # _hasNoCurrentPref: Private field to be used by
            # self.load => self._loadfile later on.
            self._hasNoCurrentPref = True

        self._upgradePrefs()

        # Hook up the preference chain.
        self._setupPreferenceChain()

        # Set the default encoding for the file
        self.encoding = components.classes['@activestate.com/koEncoding;1'].\
                                 createInstance(components.interfaces.koIEncoding)
        if not encoding_name:
            if self._language:
                language = self._language
            elif self.prefs.hasPrefHere('language'):
                language = self.prefs.getStringPref('language')
            else:
                language = None
            encoding_name = self._getEncodingNameForNewFile(language)
        self.encoding.python_encoding_name = self.encodingServices.get_canonical_python_encoding_name(
            self.encodingServices.get_encoding_info(encoding_name).python_encoding_name)

        if self.prefs.hasPrefHere('language'):
            #print "found language in prefs: ", self.prefs.getStringPref('language')
            self.set_language(self.prefs.getStringPref('language'))

        # setup an observer on our own prefs since we provide access to some
        # through getters because e.g. indentWidth is computed on some cases, and
        # yet not stored in prefs except if set explicitely.
        log.debug("adding prefs observer")
        prefObserver = self.prefs.prefObserverService
        prefObserver.addObserverForTopics(self, ['useTabs', 'indentWidth', 'tabWidth'], True)

    def _upgradePrefs(self):
        if self.prefs.hasPrefHere("prefs_version"):
            version = self.prefs.getLong("prefs_version", 0)
        else:
            version = 0

        if version < 1:
            initSvc = UnwrapObject(components.classes["@activestate.com/koInitService;1"]
                                             .getService())
            initSvc._flattenLanguagePrefs(self.prefs)

        if not version > 1:
            version = 1
            self.prefs.setLong("prefs_version", version)

    def _walkPrefChain(self, prefs, doPrint=True):
        """Debug method to help validate and show the preference chain."""
        depth = 1
        seen = set()
        while prefs:
            uprefs = UnwrapObject(prefs)
            if id(uprefs) in seen:
                raise ValueError("already seen prefs %r" % (uprefs, ))
            seen.add(id(uprefs))
            if doPrint:
                print "%s%r" % (" " * depth, uprefs)
            prefs = prefs.parent
            depth += 1

    def _setupPreferenceChain(self):
        """Set the preference chain for this document.
        
        Takes into account project preferences and whether they should apply for
        this document.
        
        Should be called once at initialization, and whenever:
          * the current project changes
          * the file path changes
        """
        prefs = self.prefs
        if not prefs:
            return

        #print "\nBefore:"
        #self._walkPrefChain(prefs)

        # Walk up until we find project or global preferences.
        parent = prefs.parent
        child = prefs
        oldprojectprefs = None
        while parent:
            try:
                oldprojectprefs = parent.QueryInterface(components.interfaces.koIProjectPreferenceSet)
                break
            except COMException:
                # It's not a project preference set - look higher.
                if parent.id in ('global', 'default'):
                    # No need to look any higher.
                    break
                child = parent
                parent = parent.parent

        assert child is not None

        newprojectprefs = None
        if not self.isUntitled:
            newprojectprefs = self._partSvc.getEffectivePrefsForURL(self.file.URI)

        # Replace existing project prefs with the new one. Child is either a
        # descendent of the global prefs, or a descendent of the old project
        # prefs.
        if newprojectprefs:
            child.parent = newprojectprefs
        else:
            child.parent = self._globalPrefs

        # TODO: If the preference chain is different - we should compare
        #       observed pref values to see if any have changed - and send
        #       appropriate notifications.

        #print "After:"
        #self._walkPrefChain(prefs)

    def resetPreferenceChain(self):
        self._setupPreferenceChain()

    def getEffectivePrefs(self):
        # this returns either a prefset from a project, or my own prefset
        return self.prefs
    
    def getEffectivePrefsByName(self, prefName):
        # this returns either a prefset from a project, or the document's own prefset
        # Differs from getEffectivePrefs because it queries each prefSet to see
        # if it directly contains the supplied pref. Otherwise a project that
        # doesn't set a pref can hide a file's setting, because the file happens
        # to be a member of the project. Use with discretion
        docPrefset = self.prefs
        if docPrefset.hasPrefHere(prefName):
            return docPrefset
        if self.file and self.file.URI:
            projPrefset = self._partSvc.getEffectivePrefsForURL(self.file.URI)
            if projPrefset:
                return projPrefset
        return docPrefset
    
    def _setLangPrefs(self):
        # Reset indentation settings - bug 95329.
        self._indentWidth = None
        self._tabWidth = None
        self._useTabs = None

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
        # If a preferred language was specifically set for this document
        # then just use that, unless it's too large for Komodo.

        if self.prefs.hasPrefHere('language'):
            language = self.prefs.getStringPref('language')
            if language != "Text" \
               and self._isConsideredLargeDocument(self.langRegistrySvc, language):
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
            fileNameLanguage = self.langRegistrySvc.suggestLanguageForFile(baseName)
            log.info("_guessLanguage: probable language from basename '%s': '%s'",
                     baseName, fileNameLanguage)
        
        # Determine an ordered list (preferred first) of possible languages
        # from the file content.
        # - Optimization: Don't send whole document because all required
        #   file-type information is required to be either at the front or
        #   end of the document. [Is this a necessary opt? --TM]
        contentLanguages = []
        buffer = self.get_buffer()
        # Unwrap so there's no need to marshal a long string
        if buffer:
            contentLanguages = UnwrapObject(self.langRegistrySvc).\
                guessLanguageFromFullContents(fileNameLanguage, buffer, self)
            log.info("_guessLanguage: possible languages from content: %s",
                     contentLanguages)

        #XXX:TODO: test that this refactoring still properly has new
        #          files follow the "new file language" pref.

        #print "we got file [%s] content [%r]" % (fileNameLanguage,contentLanguages)
        # Select the appropriate language from the above guesses.
        common_markup_formats = ("XML", "HTML", "HTML5", "XHTML")
        if (contentLanguages
            and fileNameLanguage in contentLanguages
            # bug 95308: failed to detect XBL
            and (fileNameLanguage not in common_markup_formats
                 or fileNameLanguage == contentLanguages[0])):
            # Both agree, so use the file-name language
            language = fileNameLanguage
            # bug 94775: set pref here
            self.prefs.setStringPref('language', language)
        elif not contentLanguages:
            # bugs 94335 and 94775: do not set language pref here,
            # because if there's no buffer, guessLanguage will be
            # called again after a buffer has been assigned to the koDoc
            language = fileNameLanguage or "Text"
        else:
            language = contentLanguages[0]
            # always defer to the extension match if our primary content match
            # is a generic markup language.  If it is more specific (eg. XBL)
            # then we want to maintain that instead of the filename match
            if (fileNameLanguage
                and language in common_markup_formats
                and fileNameLanguage not in common_markup_formats):
                language = fileNameLanguage
            elif fileNameLanguage and fileNameLanguage != language:
                log.warn("For file %s, favoring contents language %s over filename language %s",
                         baseName, language, fileNameLanguage)
            # bugs 94335 and 94775: set pref here
            self.prefs.setStringPref('language', language)
        log.info("_guessLanguage: '%s' (content)", language)
        if self._isConsideredLargeDocument(self.langRegistrySvc, language):
            self._setAsLargeDocument(language)
            language = "Text"
        self._language = language
        self._setLangPrefs()

    def loadFromURI(self, uri):
        self._loadFromFile(self.fileSvc.getFileFromURI(uri))
        
    def load(self):
        if self.isUntitled or self.file.URI.startswith('chrome://'):
            return
        self._loadFromFile(self.file)
        
    def _loadFromFile(self, file):
        if self.get_numScintillas() > 0:
            # The file is already loaded, in another window.
            # If we don't return here, two things can happen:
            # 1. A dirty buffer in another window will be reverted
            #    to the contents on disk.
            # 2. Any markers in the document will be cleared.
            return
        self._loadfile(file)
        self._guessLanguage()
        self._ciBuf = None # need a new codeintel Buffer for this lang
        eolpref = self.prefs.getStringPref('endOfLine')
        if self.prefs.hasPrefHere('endOfLine'):
            current_eol = eollib.eolPref2eol[eolpref]
        else:
            current_eol = self.get_existing_line_endings()
            if current_eol in (eollib.EOL_MIXED, eollib.EOL_NOEOL):
                current_eol = eollib.eolPref2eol[eolpref]
        self.set_new_line_endings(current_eol)

    def _classifyDocumentBySize(self, data):
        """ Return two values: the first classifies the document,
            the second states whether there are any lines > 2000chars
            The first value is one of the following:
            _DOCUMENT_SIZE_NOT_LARGE: (open with specified lang)
            _DOCUMENT_SIZE_UDL_LARGE: (open with specified lang if not UDL-based)
            _DOCUMENT_SIZE_ANY_LARGE: (open as Text, avoid colorizing)
        """
        returnFactor = self._DOCUMENT_SIZE_NOT_LARGE
        hasLongLine = None
        documentByteCountThreshold = self.prefs.getLongPref("documentByteCountThreshold")
        if documentByteCountThreshold <= 0:
            # Ignore this metric
            pass
        elif len(data) > documentByteCountThreshold:
            return self._DOCUMENT_SIZE_ANY_LARGE, hasLongLine
        elif len(data) > documentByteCountThreshold/2:
            returnFactor = self._DOCUMENT_SIZE_UDL_LARGE
            
        documentLineCountThreshold = self.prefs.getLongPref("documentLineCountThreshold")
        line_lengths = [len(line) for line in data.splitlines()]
        num_lines = len(line_lengths)
        if documentLineCountThreshold <= 0:
            # Ignore this metric
            pass
        elif num_lines > documentLineCountThreshold:
            return self._DOCUMENT_SIZE_ANY_LARGE, hasLongLine
        elif num_lines > documentLineCountThreshold / 2:
            returnFactor = self._DOCUMENT_SIZE_UDL_LARGE

        # Bug 93790: This value is used for opening existing files without
        # Komodo prefs with word-wrap on.  But only do it for files that
        # are new to Komodo
        if hasattr(self, "_hasNoCurrentPref"):
            if self._hasNoCurrentPref:
                hasLongLine = any(line_length > 2000 for line_length in line_lengths)
            del self._hasNoCurrentPref # No longer needed
            
        documentLineLengthThreshold = self.prefs.getLongPref("documentLineLengthThreshold")
        if documentLineLengthThreshold <= 0:
            # Ignore this metric
            return returnFactor, hasLongLine
        documentLineLengthThreshold_Halved = documentLineLengthThreshold / 2
        if any(line_length >= documentLineLengthThreshold for line_length in line_lengths):
            return self._DOCUMENT_SIZE_ANY_LARGE, True
        elif any(line_length >= documentLineLengthThreshold/2 for line_length in line_lengths):
            return self._DOCUMENT_SIZE_UDL_LARGE, True

        return returnFactor, hasLongLine

    def _loadfile(self, file):
        if file:
            data = self._get_buffer_from_file(file)
            self._documentSizeFactor, hasLongLine = self._classifyDocumentBySize(data)
            # We don't know if the document is large until we know
            # whether it's a UDL-based document or has a C++ lexer.
            if file.isRemoteFile:
                file.updateStats()
            self._lastModifiedTime = file.lastModifiedTime
        else:
            data = ''
            self._lastModifiedTime = None
        self._lastmd5 = md5(data).digest()
        buffer = self.set_buffer(data,0)
        self.ondisk_lines = buffer.splitlines(True)
        self.setSavePoint()

        # Bug 93790: If the file is new to Komodo, and has any long lines,
        # where long > 2000 chars, turn word-wrap on
        if hasLongLine:
            self.prefs.setLongPref('editWrapType', True)
            for view in self._views:
                view.scimoz.wrapMode = view.scimoz.SC_WRAP_WORD
                
        # if a file is in a project, then we have to check
        # and see if we need to update it's information
        if file.isLocal and file.updateStats():
            try:
                self._obsSvc.notifyObservers(self,'file_changed',self.file.URI)
            except:
                # ignore, noone listening
                pass
        if self.get_bufferLength() == 0:
            try:
                if self._globalPrefs.getBooleanPref('assignEmptyFilesSpecifiedEOL'):
                    try:
                        eolPref = self._globalPrefs.getStringPref("endOfLine")
                        eol = eollib.eolPref2eol[eolPref]
                    except KeyError:
                        # Be paranoid: stay with system default if pref value is bogus.
                        log.exception("unexpected 'endOfLine' pref value: %r", eolPref)
                        eol = eollib.EOL_PLATFORM
                    self.set_new_line_endings(eol)
            except:
                path = getattr(file, 'path', 'path:?')
                log.exception("_loadfile: failed to set eol on file %s", path)
        self.set_isDirty(0)
        
    def _get_buffer_from_file(self, file):
        try:
            file.open('rb')
            try:
                data = file.read(-1)
            finally:
                file.close()
        except COMException, ex:
            # koFileEx.open(), .read(), and .close() will already
            # setLastError on failure so don't need to do it again. The
            # only reason we catch it to just re-raise it is because
            # PyXPCOM complains on stderr if a COMException passes out
            # of the Python run-time.
            raise ServerException(ex.errno, str(ex))
        return data

    def get_isDirty(self):
        return self._isDirty
    
    def set_isDirty(self,isDirty):
        dirtyStateChanged = (self._isDirty != isDirty)
        self._isDirty = isDirty
        if dirtyStateChanged:
            try:
                self.observerService.notifyObservers(self,'buffer_dirty',str(isDirty))
            except COMException, e:
                pass # no one is listening!
        if not self._isDirty:
            self.removeAutoSaveFile()

    def differentOnDisk(self):
        if self.isUntitled or \
            self.file.isNetworkFile or \
            not self.file.exists or \
            self.file.URI.startswith('chrome://'):
            return 0
        if self.file.isLocal:
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
        elif self.file.isRemoteFile:
            if self.file.lastModifiedTime != self._lastModifiedTime:
                # We know the file has already changed on disk.
                return 1
            self.file.updateStats()
            newModifiedTime = self.file.lastModifiedTime
            if newModifiedTime == self._lastModifiedTime:
                # File has the same mtime - unchanged.
                return 0
            # File has recently changed.
            return 1
        else:
            # For anything else we do not detect changes.
            return 0

    def get_baseName(self):
        if self.isUntitled:
            return self._untitledName
        else:
            return self.file.baseName
    # Make self.baseName work for Python (non-xpcom) code.
    baseName = property(get_baseName)

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
        log.info("setting language to " + language);
        self._language = language
        
        if language == '':
            if self.prefs.hasPrefHere('language'):
                self.prefs.deletePref('language')
            # _guessLanguage always calls _setLangPrefs()
            self._guessLanguage()
        else:
            self.prefs.setStringPref('language', language)
            self._setLangPrefs()

        self._ciBuf = None # need a new codeintel Buffer for this lang

        self._languageObj = None
        try:
            self.observerService.notifyObservers(self,'language_changed',language)
        except COMException, e:
            pass # no one is listening!

    def get_languageObj(self):
        if self._language is None:
            log.error('Asked to get language Object with no language')
        if self._languageObj == None:
            self._languageObj = self.langRegistrySvc.getLanguage(self._language)
        return self._languageObj

    def setFileAccessed(self):
        accessNo = self.prefs.getLong('kodoc_file_access_no', 0) + 1
        self.prefs.setLongPref('kodoc_file_access_no', accessNo)
        self.prefs.setLongPref('kodoc_file_last_accessed', time.time())

    def get_fileLastOpened(self):
        return self.prefs.getLong('kodoc_file_last_opened', 0);

    def get_fileAccessNo(self):
        return self.prefs.getLong('kodoc_file_access_no', 0);

    def get_fileLastAccessed(self):
        return self.prefs.getLong('kodoc_file_last_accessed', 0);

    # Note: The "get_subLanguage" and "languageForPosition" methods could also
    #       use the koIDocument.ciBuf.lang_from_pos() code, instead of their
    #       own implementation. To be kept in mind for re-factoring work.

    @components.ProxyToMainThread
    def familyForPosition(self, pos=None):
        """Return the UDL family name for the given position.

            pos - scintilla position, or currentPos if pos is None

        Example UDL family names returned are "M", "CSS", "TPL".
        """
        if not self._language or not self._docPointer:
            return None
        languages = self.get_languageObj().getSubLanguages()
        if len(languages) < 2:
            return self._language
        # get the current position, and query the languageObj for what lang this is
        scimoz = self._views[0].scimoz
        if pos is None:
            pos = scimoz.currentPos
        elif pos >= scimoz.length and pos > 0:
            pos = scimoz.positionBefore(scimoz.length)
        style = scimoz.getStyleAt(pos)
        return udl_family_from_style(style)

    def languageForPosition(self, pos):
        family = self.familyForPosition(pos)
        return self.get_languageObj().getLanguageForFamily(family)

    def get_subLanguage(self):
        return self.languageForPosition(pos=None)

    DECORATOR_UDL_FAMILY_TRANSITION = components.interfaces.koILintResult.DECORATOR_UDL_FAMILY_TRANSITION

    @components.ProxyToMainThread
    def getLanguageTransitionPoints(self, start_pos, end_pos):
        if not self._language or not self._docPointer:
            return [0, 0]
        scimoz = self._views[0].scimoz
        languages = self.get_languageObj().getSubLanguages()
        if len(languages) < 2:
            return [0, scimoz.length]
        # Check the region for UDL transition markers. LexUDL sets indicator 18
        # on the start char (or set of chars) beginning a new UDL family
        # section.
        transition_points = []
        pos = start_pos
        length = scimoz.length
        end_pos = min(end_pos, length)
        while pos <= end_pos:
            indic_start = scimoz.indicatorStart(self.DECORATOR_UDL_FAMILY_TRANSITION, pos)
            indic_end = scimoz.indicatorEnd(self.DECORATOR_UDL_FAMILY_TRANSITION, indic_start+1)
            if indic_start == indic_end == 0: # No indicators found.
                break
            if not transition_points:
                transition_points.append(indic_start)
            # Sanity check: scintilla collapses a run of
            # single-char indicators to one indicator, and we would lose
            # boundary info for all but the first indicator in this run.
            current_run_pos = indic_start
            family_next = udl_family_from_style(scimoz.getStyleAt(current_run_pos))
            while current_run_pos < indic_end - 1:
                family_start = family_next
                family_next = udl_family_from_style(scimoz.getStyleAt(current_run_pos + 1))
                if family_start != family_next:
                    transition_points.append(current_run_pos + 1)
                    current_run_pos += 1
                else:
                    break
            transition_points.append(indic_end)
            if indic_end >= end_pos:  # Past the end of the region specified.
                break
            pos = indic_end
            if indic_end == end_pos:
                # In case the last indicator ends on the last char, not at the
                # posn after the last character
                pos += 1
        if len(transition_points) < 2:
            return [0, length]
        transition_points.append(length)
        return transition_points

    def get_codePage(self):
        return self._codePage
    
    def set_codePage(self, codePage):
        # We never allow a code page other than 65001 (aka put scintilla
        # in Unicode/UTF-8 mode).
        if codePage != "65001":
            log.warn("setting `koDocument.codePage` is DEPRECATED, hardwired "
                "to 65001 (unicode mode): %r ignored", codePage)

    @components.ProxyToMainThread
    def get_buffer(self):
        if self._docPointer:
            return self._views[0].scimoz.text
        return self._buffer
    
    def set_buffer(self, text, makeDirty=1):
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
        else:
            encoded_buffer = text

        self._set_buffer_encoded(encoded_buffer, makeDirty)
        log.info("set_buffer encoding %s codePage %r", self.encoding.python_encoding_name, self._codePage)
        self.prefs.setStringPref("encoding",
                                 self.encoding.python_encoding_name)
        return encoded_buffer

    @property
    def buffer(self):
        return self.get_buffer()
    @buffer.setter
    def buffer(self, text):
        return self.set_buffer(text)

    @components.ProxyToMainThread
    def _set_buffer_encoded(self,text,makeDirty=1):
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

    @components.ProxyToMainThread
    def get_bufferLength(self):
        # XXX as we add more methods, we'll need a better system
        if self._docPointer:
            return self._views[0].scimoz.textLength
        if self._buffer:
            return len(self._buffer)
        return 0

    @components.ProxyToMainThread
    def set_existing_line_endings(self, le):
        if le not in (eollib.EOL_LF, eollib.EOL_CR, eollib.EOL_CRLF):
            raise ServerException(nsError.NS_ERROR_FAILURE,
                                  "Invalid line ending: %s" % le)

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

    def get_existing_line_endings(self):
        endings, recommended = eollib.detectEOLFormat(self.get_buffer())
        if endings == eollib.EOL_NOEOL:
            return self.get_new_line_endings()
        else:
            return endings

    def get_new_line_endings(self):
        return self._eol

    @components.ProxyToMainThread
    def set_new_line_endings(self, le):
        if le not in (eollib.EOL_LF, eollib.EOL_CR, eollib.EOL_CRLF):
            raise ServerException(nsError.NS_ERROR_FAILURE,
                                  "Invalid new line ending: %s" % le)
        log.info("set_new_line_endings to '%s'", eollib.eol2eolName[le])
        self._eol = le
        for view in self._views:
            if view.scimoz:
                view.scimoz.eOLMode = eollib.eol2scimozEOL[le]

    @components.ProxyToMainThread
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
    
    def _getEncodingPrefFromBaseName(self, baseName):
        language = self.langRegistrySvc.suggestLanguageForFile(baseName)
        if not language:
            language = 'Text'
        try:
            encoding_name = self._getEncodingNameForNewFile(language=language)
        except Exception, e:
            log.error("Error getting newEncoding for %s", language, exc_info=1)
            encoding_name = prefs.getStringPref('encodingDefault')
        return encoding_name

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
            tryencoding = self._getEncodingPrefFromBaseName(self.get_baseName())
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

    @components.ProxyToMainThread
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
                    self.encoding.use_byte_order_marker == encoding.use_byte_order_marker and
                    self.prefs.getString("encoding", "") == self.encoding.python_encoding_name):
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
                            # _encodeBuffer created lastErrorMessage
                            lastErrorSet = 1
                            errmsg = self.lastErrorSvc.getLastErrorMessage()
                            raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
                        updateBuffer = unicodeBuffer != buffer

                make_dirty = make_dirty or self.encoding.use_byte_order_marker != encoding.use_byte_order_marker
                self.encoding = encoding

                self._ciBuf = None

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

    def canBeEncodedWithEncoding(self, encoding):
        """See if the current buffer can be converted with the given encoding.
        
           @param {koIEncoding} encoding

           @returns True if it can be encoded, False if not.  And if it returns
            False, it also sets the last error code:
               nsError.NS_ERROR_FAILURE if the value can't be encoded
               nsError.NS_ERROR_UNEXPECTED on an unexpected exception
        """
        try:
            self._encodeBuffer(encoding)
            return True
        except (UnicodeError, COMException):
            # Error message has been created, return False
            pass
        except Exception, e:
            self.lastErrorSvc.setLastError(nsError.NS_ERROR_UNEXPECTED, e.message)
        return False

    def _encodeBuffer(self, encoding, errors="strict"):
        """ Apply the proposed encoding to the current buffer's text,
            and return the result.

            On failure, catch UnicodeError and COMException exceptions,
            and create an error message clients can access to explain
            what went wrong.
        
           @param {koIEncoding} encoding
           @param {string} errors

           @returns {string}
               sets the last error message to nsError.NS_ERROR_FAILURE if the value can't be encoded
               and rethrows the exception.

               Other exceptions are uncaught, and need to be caught by callers.
        """
        from koUnicodeEncoding import recode_unicode
        try:
            return recode_unicode(self.get_buffer(),
                                  self.encoding.python_encoding_name,
                                  encoding.python_encoding_name,
                                  errors)
        except (UnicodeError, COMException), e:
            # The caller might need an explanation of why this method failed
            errmsg = ("Unable to convert '%s' from '%s' to '%s'.  "
                      "This encoding cannot represent all "
                      "characters in the current buffer."
                      % (self.get_baseName(),
                         self.encoding.python_encoding_name,
                         encoding.python_encoding_name))
            self.lastErrorSvc.setLastError(nsError.NS_ERROR_FAILURE, errmsg)
            raise
        
    def _getEncodedBufferText(self, encoding_name=None, mode='strict', buffer=None):
        """Get the buffer text encoded in a particular encoding, by
        default the current configured encoding.
        """
        if not encoding_name:
            encoding_name = self.encoding.python_encoding_name
        if buffer is None:
            buffer = self.get_buffer()
        encodedText = buffer.encode(encoding_name, mode)
        if self.encoding.use_byte_order_marker:
            encodedText = self.encoding.encoding_info.byte_order_marker + encodedText
        if self.get_bufferLength() and not len(encodedText):
            # Looks like we zero'd out the buffer. That's not good.
            errmsg = "Unable to encode the buffer to %s" % encoding_name
            self.lastErrorSvc.setLastError(0, errmsg)
            raise ServerException(nsError.NS_ERROR_FAILURE, errmsg)
        return encodedText

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
            encodedText = self.get_buffer().encode(encoding_name, 'replace')
            if self.encoding.use_byte_order_marker:
                encoding_info = self.encodingServices.get_encoding_info(encoding_name)\
                           .python_encoding_name
                self.encoding.use_byte_order_marker = encoding_info.byte_order_marker != ''
            self._set_buffer_encoded(unicode(encodedText, encoding_name))
        except Exception, e:
            log.exception(e)
            raise

    @property
    def encodedText(self):
        try:
            return self._getEncodedBufferText()
        except UnicodeError, ex:
            log.error("unable to encode document as %r: %s",
                self.encoding.python_encoding_name, ex)
            raise

    @property
    def utf8Text(self):
        try:
            return self._getEncodedBufferText("utf-8")
        except UnicodeError, ex:
            log.error("unable to encode document as 'utf-8': %s",
                self.encoding.python_encoding_name, ex)
            raise
        
    def getChangedLinesWithTrailingWhitespace(self):
        """Generate a diff and return the changed lines."""
        diff_content = self.getUnsavedChanges()
        diff = difflibex.Diff(diff_content)
        changes = diff.get_changed_line_numbers_by_filepath().values()
        if changes:
            return changes[0]
        return []

    def _getCleanChangedLinesOnly(self):
        if not self._globalPrefs.getBooleanPref("cleanLineEnds_ChangedLinesOnly"):
            return False
        try:
            # If there's no actual backing file, we can't tell which
            # lines are changed.
            return self.file.exists
        except AttributeError:
            return False
            

    _cleanLineRe = re.compile("(.*?)([ \t]+?)?(\r\n|\n|\r)", re.MULTILINE)
    @components.ProxyToMainThread
    def _clean(self, ensureFinalEOL, cleanLineEnds):
        """Clean the current document content.
        
            "ensureFinalEOL" is a boolean indicating if "cleaning" should
                ensure the file content ends with an EOL.
            "cleanLineEnds" is a boolean indicating if "cleaning" should
                remove trailing whitespace on all lines.
        
        There is one exception to "cleanLineEnds": trailing whitespace
        before the current cursor position on its line is not removed
        (bug 32702), but only if the pref cleanLineEnds_CleanCurrentLine
        is false (bug 86476).  By default both prefs are off.
        
        This function preserves the current cursor position and selection,
        if any, and should maintain fold points and markers.
        """
        if not self._views:
            return
        cleanLineCurrentLineEnd = self._globalPrefs.getBooleanPref("cleanLineEnds_CleanCurrentLine")
        if cleanLineEnds:
            cleanChangedLinesOnly = self._getCleanChangedLinesOnly()
            if cleanChangedLinesOnly:
                wsLinesToStrip = self.getChangedLinesWithTrailingWhitespace()
            else:
                wsLinesToStrip = None
        else:
            cleanChangedLinesOnly = False
        scintilla = self._views[0]
        try:
            DEBUG = 0
            if DEBUG: print "-"*50 + " _clean:"

            # Protect settings: selection, cursor position, etc.
            scimoz = scintilla.scimoz
            currPos = scimoz.currentPos
            currPosLine = scimoz.lineFromPosition(currPos)
            currPosCol = currPos - scimoz.positionFromLine(currPosLine)
            anchorPos = scimoz.anchor
            anchorLine = scimoz.lineFromPosition(anchorPos)
            anchorCol = scimoz.anchor - scimoz.positionFromLine(anchorLine)
            firstVisibleLine = scimoz.firstVisibleLine
            firstDocLine = scimoz.docLineFromVisible(firstVisibleLine)
            haveNoSelection = currPos == anchorPos

            # Clean the document content.
            text = scimoz.text
            lines = text.splitlines(True)
            eolStr = eollib.eol2eolStr[eollib.scimozEOL2eol[scimoz.eOLMode]] # '\r\n' or '\n'...
            if text.endswith(eolStr):
                # Model Scintilla: when a document ends with an EOL, Scintilla
                # actually acts as if it has one more line.
                lines.append("")
            numLines = len(lines)
            sciLength = scimoz.length # scimoz.length in _bytes_
            scimoz.beginUndoAction()
            try:
                if ensureFinalEOL and not text.endswith(eolStr):
                    if DEBUG:
                        print "INSERT FINAL EOL: %r" % eolStr
                    scimoz.insertText(sciLength, eolStr)

                if cleanLineEnds:
                    if DEBUG: print "LINE  POSITION  CONTENT"
                    pattern = re.compile(".*?([ \t]*)(\r\n|\n|\r)?$")
                    for i in range(numLines - 1, -1, -1):
                        line = lines[i]
                        match = pattern.match(line)
                        trailingWS, eol = match.groups()
                        if trailingWS and (not cleanChangedLinesOnly or i in wsLinesToStrip):
                            wsLen = len(trailingWS)
                        else:
                            wsLen = 0
                        if eol and eol != eolStr:
                            eolLen = len(eol)
                        else:
                            eolLen = 0
                        if not wsLen and not eolLen:
                            # No need to change anything on this line
                            continue
                        # Point startPos and endPos to the range of whitespace
                        # to be replaced (by either the correct EOL, or nothing)
                        lineEndPos = scimoz.getLineEndPosition(i)
                        startPos = lineEndPos - wsLen
                        endPos = lineEndPos + eolLen
                        if eolLen:
                            newText = eolStr
                        else:
                            # Drop the white-space, keep the EOL
                            newText = ""

                        if (not cleanLineCurrentLineEnd
                            and i == currPosLine
                            and startPos < currPos):
                            # If the cursor is in the trailing whitespace
                            # and cleanLineCurrentLineEnd is false,
                            # just remove the spaces to the right of the cursor
                            startPos = currPos
                            
                        if DEBUG:
                            span = "%d-%d" % (startPos, endPos)
                            print "%3d: %9s: %r" % (i, span, line)
                        scimoz.targetStart = startPos
                        scimoz.targetEnd = endPos
                        scimoz.replaceTarget(len(newText), newText)
                
                    # If the buffer ends with > 1 blank line,
                    # Replace all of them with whatever the last line happens
                    # to be -- this keeps us from creating buffers that
                    # don't end with a newline, even if the user chose the
                    # cleanLineEnds option but not the ensureFinalEOL option.

                    # If there's a selection, stop at the line after it.
                    # Same with breakpoints, bookmarks, and the current
                    # position.  The idea is to quietly remove empty lines
                    # at the end of a file, when the user is higher up.
                    
                    if cleanLineCurrentLineEnd:
                        firstDeletableLine = 0
                    else:
                        firstDeletableLine = scimoz.lineFromPosition(max(currPos, scimoz.selectionEnd)) + 1
                    try:
                        # Don't go by scimoz.linecount, which doesn't distinguish
                        # buffers that end with an EOL from those that don't
                        lastDeletableLine = len(lines) - 1
                        if cleanChangedLinesOnly:
                            # Now we'll only delete lines that are changed
                            for i in range(lastDeletableLine, firstDeletableLine - 1, -1):
                                if i not in wsLinesToStrip:
                                    if i == lastDeletableLine:
                                        raise DontDeleteEndLines()
                                    firstDeletableLine = i + 1
                                    break
                        for i in range(lastDeletableLine, firstDeletableLine - 1, -1):
                            if scimoz.markerGet(i):
                                firstLineToDelete = i + 1
                                break
                            try:
                                if re.search(r'\S', lines[i]):
                                    firstLineToDelete = i + 1
                                    break
                            except IndexError:
                                log.exception("Error indexing lines[i=%d], lastDeletableLine:%d, firstDeletableLine:%d, numLines:%d",
                                              i, lastDeletableLine,
                                              firstDeletableLine,
                                              numLines)
                        else:
                            firstLineToDelete = firstDeletableLine
    
                        if firstLineToDelete < lastDeletableLine:
                            # Delete all lines from pos(line[i][0]) to
                            # pos(line[count - 1][0]) - 1 unless the
                            # selection/cursor is in that range
                            startPos = scimoz.positionFromLine(firstLineToDelete)
                            endPos = scimoz.positionFromLine(lastDeletableLine)
                            if endPos > startPos:
                                scimoz.targetStart, scimoz.targetEnd = startPos, endPos
                                scimoz.replaceTarget(0, '')

                    except DontDeleteEndLines:
                        pass
            finally:
                scimoz.endUndoAction()

            # Restore settings: selection, cursor position, etc.
            currLineCount = scimoz.lineCount
            if currPosLine >= currLineCount:
                #log.debug("Pull currPosLine back from %d to %d", currPosLine, currLineCount)
                currPosLine = currLineCount
                currPosCol = 0
            if anchorLine >= currLineCount:
                #log.debug("Pull anchorLine back from %d to %d", anchorLine, currLineCount)
                anchorLine = currLineCount
                anchorCol = 0
            newPos = scimoz.positionFromLine(currPosLine) + currPosCol
            lineEndPos = scimoz.getLineEndPosition(currPosLine)
            if newPos > lineEndPos:
                #log.debug("Pull new currentPos from %d to %d", newPos, lineEndPos)
                newPos = lineEndPos
            # And on cr/lf documents, verify that the position isn't stuck
            # between the two
            if (scimoz.getCharAt(newPos - 1) == 13
                    and scimoz.getCharAt(newPos) == 10):
                newPos -= 1
            scimoz.currentPos = newPos
            if haveNoSelection:
                scimoz.anchor = scimoz.currentPos
            else:
                #log.debug("Recalc new selection")
                newPos = scimoz.positionFromLine(anchorLine) + anchorCol
                lineEndPos = scimoz.getLineEndPosition(anchorLine)
                if newPos > lineEndPos:
                    #log.debug("Pull new anchor from %d to %d", newPos, lineEndPos)
                    newPos = lineEndPos
                    if (scimoz.getCharAt(newPos - 1) == 13
                            and scimoz.getCharAt(newPos) == 10):
                        newPos -= 1
                scimoz.anchor = newPos

            if firstDocLine >= scimoz.lineCount - scimoz.linesOnScreen:
                firstVisibleLine = (scimoz.visibleFromDocLine(scimoz.lineCount)
                                    - scimoz.linesOnScreen)
            else:
                firstVisibleLine = scimoz.visibleFromDocLine(firstDocLine)
            #scimoz.lineScroll(0, min(firstVisibleLine-scimoz.firstVisibleLine,
            #                         scimoz.lineCount-scimoz.firstVisibleLine))
                    
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
                
            if self.file.isLocal and not self.file.isNetworkFile:
                # Must update stats for remote files.
                self.file.updateStats()
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
    
            # Translate the buffer before opening the file so if it
            # fails, we haven't truncated the file.
            buffer = self.get_buffer()
            try:
                data = self._getEncodedBufferText(buffer=buffer)
            except UnicodeError, ex:
                log.error("unable to encode document as %r: %s",
                    self.encoding.python_encoding_name, ex)
                raise

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
            self._lastModifiedTime = self.file.lastModifiedTime
            self.set_isDirty(0)
            self.setSavePoint()

            try:
                self._obsSvc.notifyObservers(self, "document_saved", self.file.URI)
            except:
                pass # ignore, noone listening

            try:
                self._obsSvc.notifyObservers(self, "file_changed",
                                             self.file.URI)
            except:
                pass # ignore, no one listening
            
            self.ondisk_lines = buffer.splitlines(True)
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

    @components.ProxyToMainThread
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
    # document. When the last view is released we can clear the _docPointer
    @components.ProxyToMainThread
    def addView(self, scintilla):
        self._views.append(scintilla)
        scimoz = scintilla.scimoz
        xpself = WrapObject(self, components.interfaces.koIDocument)
        if not self._docPointer:
            # Use the existing document/docPointer created by Scintilla.
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
    
    def addScimoz(self, scimoz):
        #TODO: Pull out commented-out code
        #xpself = WrapObject(self, components.interfaces.koIDocument)
        scimoz.addRefDocument(self._docPointer)
        scimoz.docPointer = self._docPointer
        #self.docSettingsMgr.register(xpself, scintilla)
    
    def releaseScimoz(self, scimoz):
        #xpself = WrapObject(self, components.interfaces.koIDocument)
        # We could have done this in JavaScript, but it makes more sense
        # to do it here.
        try:
            scimoz.releaseDocument(scimoz.docPointer);
        except:
            log.exception("releaseScimoz failed")

    @components.ProxyToMainThread
    def releaseView(self, scintilla):
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

    def getView(self):
        try:
            return self._views[0]
        except IndexError, ex:
            raise ServerException(nsError.NS_ERROR_FAILURE, str(ex))

    def get_numScintillas(self):
        return len(self._views)

    # we want to watch for changes in the prefs we derive from
    @components.ProxyToMainThread
    def observe(self, subject, topic, data):
        #print "observe: subject:%r, topic:%s, data:%r" % (subject, topic, data)
        if topic == 'useTabs':
            self._useTabs = self.prefs.getBooleanPref('useTabs')
        elif topic == 'indentWidth':
            val = self._indentWidth = self.prefs.getLongPref('indentWidth')
            for view in self._views:
                view.scimoz.indent = val
        elif topic == 'tabWidth':
            val = self._tabWidth = self.prefs.getLongPref('tabWidth')
            for view in self._views:
                view.scimoz.tabWidth = val

    def _getLangPref(self, *prefInfos):
        """Get a pref that might fallback to language-specific values.
        This will, at each level, check for each given pref name, and return the
        first pref value gotten.
        @param prefInfos {iterable} list of prefs to look up; each item should
            be itself an iterable of (pref name, pref getter)
        @returns a tuple of (found pref name, value); if no given prefs can be
            found, return (None, None)
        @note If any pref name starts with "%lang/" that prefix will be replaced
            with the name of the current language pref.
        """
        prefset = self.prefs

        while prefset is not None:
            for key, getter in prefInfos:
                if key.startswith("%lang/"):
                    key = "languages/%s/%s" % (self._language,
                                               key[len("%lang/"):])
                if prefset.hasPrefHere(key):
                    return key, getattr(prefset, getter)(key)
            prefset = prefset.inheritFrom

        # Prefs not found at any level?
        return None, None

    @property
    def useTabs(self):
        if self._useTabs is None:
            pref, value = self._getLangPref(('useSmartTabs', 'getBoolean'),
                                            ('%lang/useTabs', 'getBoolean'),
                                            ('useTabs', 'getBoolean'))
            assert pref is not None, "Should have default useTabs pref"
            if pref == 'useSmartTabs':
                self._guessFileIndentation()
            else:
                self._useTabs = value
        return self._useTabs

    @useTabs.setter
    def useTabs(self, value):
        # will affect _useTabs through prefs observers
        self.prefs.setBoolean('useTabs', value)

    @property
    def indentWidth(self):
        if self._indentWidth is None:
            pref, value = self._getLangPref(('useSmartTabs', 'getBoolean'),
                                            ('%lang/indentWidth', 'getLong'),
                                            ('indentWidth', 'getLong'))
            if pref == 'useSmartTabs':
                self._guessIndentWidth()
            else:
                self._indentWidth = value
        else:
            log.info("_indentWidth is not none, it's %s" % self._indentWidth)
        return self._indentWidth

    @indentWidth.setter
    def indentWidth(self, value):
        self._indentWidth = value
        # will affect _indentWidth through prefs observers
        self.prefs.setLong('indentWidth', value)

    @property
    def tabWidth(self):
        if self._tabWidth is None:
            self._tabWidth = self.prefs.getLong('tabWidth')
        return self._tabWidth

    @tabWidth.setter
    def tabWidth(self, value):
        self._tabWidth = value
        # will affect _tabWidth through prefs observers
        self.prefs.setLong('tabWidth', value)

    @components.ProxyToMainThread
    def _guessFileIndentation(self):
        # Heuristic to determine what file indentation settings the user
        # likely wants for this file.
        log.info("in _guessFileIndentation")
        useTabs = False
        linesChecked = 0
        buffer = self.get_buffer()

        # In the first 150 lines of the file, search for the non-blank
        # lines with leading white-space.  Searching farther takes too long.
        tabcount = 0
        spacecount = 0
        for line in buffer.splitlines()[:150]:
            if line.startswith("\t"):
                # If first char is a tab, recognize that and move on
                linesChecked += 1
                tabcount += 1
            elif line.startswith("  "):
                # If first 2 chars are spaces, recognize that and move on
                # Require at least two spaces on the line to count it
                linesChecked += 1
                spacecount += 1
            if linesChecked == 25:
                # Only check up to 25 lines with indentation
                break

        if linesChecked:
            # We found some lines with indentation
            if tabcount > spacecount:
                # If only tab indentation was found, set the indentWidth
                # to the tabWidth, so we essentially always use tabs.
                useTabs = True
            elif spacecount and not tabcount:
                useTabs = False
            else:
                # indeterminate, so use global prefs to decide
                useTabs = self.prefs.getBoolean("useTabs")
            if useTabs:
                self._indentWidth = self.tabWidth
            elif self._indentWidth is None:
                # Make sure we have a default value here (from prefs)
                _, value = self._getLangPref(('%lang/indentWidth', 'getLong'),
                                             ('indentWidth', 'getLong'))
                self._indentWidth = value
                
            log.info("guessed useTabs = %r, tabcount %d, spacecount %d",
                     useTabs, tabcount, spacecount)
                
            for v in self._views:
                self._useTabs = useTabs
                v.scimoz.useTabs = useTabs
                v.scimoz.indent = self._indentWidth

        else:
            # Lacking better information, fallback to the pref values.
            if self._useTabs is None:
                _, self._useTabs = self._getLangPref(('%lang/useTabs', 'getBoolean'),
                                                     ('useTabs', 'getBoolean'))
            if self._indentWidth is None:
                _, self._indentWidth = self._getLangPref(('%lang/indentWidth', 'getLong'),
                                                         ('indentWidth', 'getLong'))
            if self._tabWidth is None:
                _, self._tabWidth = self._getLangPref(('%lang/tabWidth', 'getLong'),
                                                      ('tabWidth', 'getLong'))
            for v in self._views:
                v.scimoz.useTabs = self._useTabs
                v.scimoz.indent = self._indentWidth
                v.scimoz.tabWidth = self._tabWidth

    # Guess indent-width from text content. (Taken from IDLE.)
    #
    # This should not be believed unless it's in a reasonable range
    # (e.g., it will be 0 if no indented blocks are found).
    @components.ProxyToMainThread
    def _guessIndentWidth(self):
        text = self.get_buffer()

        _, defaultIndentWidth = self._getLangPref(('%lang/indentWidth', 'getLong'),
                                                  ('indentWidth', 'getLong'))
        if text == '':
            self._indentWidth = defaultIndentWidth
            return
        # if we don't have a view yet, we can't do anything.
        if not self._views:
            log.error("Was asked to guess indent width before there's a view")
            self._indentWidth = defaultIndentWidth
            return
        if not self._languageObj:
            self.get_languageObj()
        # The strategy for guessing the indentation is delegated to the
        # lexer language service, since different languages have very
        # different rules.
        indentWidth = 0
        useTabs = 0
        _, defaultUseTabs = self._getLangPref(('%lang/useTabs', 'getBoolean'),
                                              ('useTabs', 'getBoolean'))
        try:
            indentWidth, useTabs = \
                self._languageObj.guessIndentation(self._views[0].scimoz,
                                                   self.tabWidth,
                                                   defaultUseTabs)
        except Exception, e:
            log.error("Unable to guess indentation")
            
        if indentWidth == 0:  # still haven't found anything, so go with the prefs.
            indentWidth = defaultIndentWidth
            useTabs = defaultUseTabs

        log.info("_guessIndentWidth: indentWidth=%d, useTabs=%d",
                 indentWidth, useTabs)
        
        self._indentWidth = indentWidth
        self._useTabs = useTabs
        
        for v in self._views:
            v.scimoz.useTabs = self._useTabs
            v.scimoz.indent = self._indentWidth

    @components.ProxyToMainThreadAsync
    def _statusBarMessage(self, message):
        sm = components.classes["@activestate.com/koStatusMessage;1"]\
             .createInstance(components.interfaces.koIStatusMessage)
        sm.category = "Document"
        sm.msg = message
        sm.timeout = 5000 # 0 for no timeout, else a number of milliseconds
        sm.highlight = 1  # boolean, whether or not to highlight
        try:
            self._obsSvc.notifyObservers(sm, 'status_message', None)
        except COMException, e:
            # do nothing: Notify sometimes raises an exception if (???)
            # receivers are not registered?
            pass

    _re_ending_eol = re.compile('\r?\n$')
    def getUnsavedChanges(self, joinLines=True):
        eolStr = eollib.eol2eolStr[self._eol]
        ondisk = self.ondisk_lines
        inmemory = self.get_buffer().splitlines(True)
        difflines = list(difflibex.unified_diff(
            ondisk, inmemory,
            self.file.displayPath, self.file.displayPath+" (unsaved)",
            lineterm=eolStr))
        # Add index line so diff parsing for "Reveal position in editor"
        # feature can infer the correct path (otherwise gets " (unsaved)"
        # as part of it).
        difflines.insert(0, "Index: "+self.file.displayPath+eolStr)
        if joinLines:
            return ''.join(difflines)
        else:
            return [self._re_ending_eol.sub('', x) for x in difflines]

    def _getAutoSaveFileName(self):
        # retain part of the readable name
        autoSaveFilename = "%s-%s" % (self.file.md5name,self.file.baseName)
        return os.path.join(self.autoSaveDirectory, autoSaveFilename)

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
        # no point in autosaving if we're not dirty
        if self._isDirty and not self.isUntitled:
            self._doAutoSave()

    # We cannot get the text from scintilla in a thread, and must proxy.
    # This also means we won't attempt to actually do writes on the autosave
    # thread, which means _that_ thread can be marked as daemon (since we won't
    # kill that thread in the middle of a write).
    @components.ProxyToMainThread
    def _doAutoSave(self):
        autoSaveFile = self._getAutoSaveFile()
        log.debug("last save %d now %d", autoSaveFile.lastModifiedTime, time.time())
        
        # translate the buffer before opening the file so if it
        # fails, we haven't truncated the file
        try:
            data = self.encodedText
        except Exception, e:
            try:
                # failed to get encoded text, save it using utf-8 to avoid
                # data loss (bug 40857)
                data = self.utf8Text;
                self._statusBarMessage("Using UTF-8 to autosave '%s'" %
                              self.baseName)
            except Exception, e:
                log.exception(e)
                self._statusBarMessage("Error getting encoded text for autosave of '%s'" %
                              self.baseName)
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
                          self.baseName)
            return
    
    def restoreAutoSave(self):
        if self.isUntitled: return
        autoSaveFile = self._getAutoSaveFile()
        self._loadfile(autoSaveFile)
        self.set_isDirty(1)
        # fix the file content md5
        data = self._get_buffer_from_file(self.file)
        self._lastmd5 = md5(data).digest()
        self._lastModifiedTime = self.file.lastModifiedTime

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

    #---- internal general support methods
    
    def _getStringPref(self, name, default=None):
        effectivePrefs = self.getEffectivePrefs()
        if effectivePrefs.hasPref(name):
            return self.prefs.getStringPref(name)
        return default

    def _getBooleanPref(self, name, default=0):
        effectivePrefs = self.getEffectivePrefs()
        if effectivePrefs.hasPref(name):
            return effectivePrefs.getBooleanPref(name)
        return default

    def md5Hash(self):
        return md5(self.buffer.encode("utf-8")).hexdigest()

