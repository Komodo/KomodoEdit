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

from xpcom import components, COMException, ServerException
import logging
import timeline
import eollib

log = logging.getLogger('koDocumentSettingsManager')

def RGB(r,g,b): return r+g*256+b*256*256

# Must keep this marker constants in sync with markers.js MARKNUM_*
#XXX Should create a module for that because koScintillaSchemeService.py
#    has the same issue.
MARKNUM_BOOKMARK = 6

class koDocumentSettingsManager:
    _com_interfaces_ = [components.interfaces.koIDocumentSettingsManager,
                        components.interfaces.nsIObserver]
    _reg_desc_ = "Komodo Document Settings Manager"
    _reg_contractid_ = "@activestate.com/koDocumentSettingsManager;1"
    _reg_clsid_ = "{5ECD8F3B-4118-43F4-82AA-DB7AC60F9A6D}"

    # A list of view-related preferences.
    _viewPrefList = ['showWhitespace', 'showIndentationGuides', 'showEOL',
                     'editUseAlternateFaceType', 'showLineNumbers',
                     'editWrapType', 'editAutoWrapColumn', 'editUseEdge',
                     'encoding', 'editFoldStyle', 'anchor', 'currentPos',
                     'editFoldLines', 'indentWidth', 'caretStyle', 'caretWidth',
                     # Code Intelligence stuff:
                     'codeintel_completion_triggering_enabled',
                     'codeintel_rescan_while_typing_enabled',
                ]

    def __init__(self):
        timeline.enter('koDocumentSettingsManager.__init__')
        
        # get services we'll use
        timeline.mark("getting language registry")
        self._languageRegistry = components.classes["@activestate.com/koLanguageRegistryService;1"].\
                            getService(components.interfaces.koILanguageRegistryService) 
        timeline.mark("getting global prefs")
        self._globalPrefs = components.classes["@activestate.com/koPrefService;1"].\
                            getService(components.interfaces.koIPrefService).prefs
        self.document = None
        self._observing = 0
        self._supportsFolding = 0
        self._scintillas = []
        self._useAlternateFaceType = None
        timeline.leave('koDocumentSettingsManager.__init__')
    
    def register(self, document, scintilla):
        timeline.enter("koDocumentSettingsManager.register")
        self.document = document
        if scintilla in self._scintillas:
            log.error("Already have scimoz %r for document %s",scintilla, document)
            raise ServerException
        self._scintillas.append(scintilla)
        # Two cases-- either this is the first scintilla
        # for this document, or it's not.  In the first
        # case, then the buffer needs to be gotten from
        # the document.  In the other it's just a matter of
        # sharing docpointers
        timeline.enter("scimoz mods")
        scimoz = scintilla.scimoz
        if len(self._scintillas) == 1:
            scimoz.undoCollection = 0
            scimoz.emptyUndoBuffer()
            scimoz.readOnly = 0
            buffer = document.buffer
            scimoz.codePage = document.codePage
            scimoz.text = buffer
            scimoz.undoCollection = 1
            scimoz.setSavePoint()
            scimoz.eOLMode = eollib.eol2scimozEOL[document.new_line_endings]
            scimoz.emptyUndoBuffer()
        else:
            scimoz.docPointer = self._scintillas[0].scimoz.docPointer
            
        timeline.leave("scimoz mods")
        self.applyDocumentSettingsToView(scintilla)
        # Watch for preference set changes from these pref sets.
        if not self._observing:
            self._globalPrefs.addObserver(self)
            self.document.prefs.addObserver(self)
            self._observing = 1
        timeline.leave("koDocumentSettingsManager.register")
        
    def unregister(self, scintilla):
        if scintilla not in self._scintillas:
            log.error("can't unregister unknown scimoz: %r", scintilla)
            raise ServerException
        self._scintillas.remove(scintilla)
        if not self._scintillas:
            # We just got rid of the last view for this document
            # We should save the state of that last view
            self.applyViewSettingsToDocument(scintilla)
            if self._observing:
                # remove observers
                # XXX these cause exceptions regarding weakref/null pointer, but
                # NOT doing this we continue to leak editor wrappers.
                self.document.prefs.removeObserver(self)
                self._globalPrefs.removeObserver(self)
                self._observing = 0
            self.document = None
        
    def applyDocumentSettingsToView(self, scintilla):
        timeline.enter("koDocumentSettingsManager.applyDocumentSettingsToView")
        scimoz = scintilla.scimoz
        # assumption: we are given a 'virgin' view, and a fully
        # capable document -- if it doesn't know something, it can figure it out.
        languageOb = self.document.languageObj
        document = self.document
        lexer = languageOb.getLanguageService(components.interfaces.koILexerLanguageService)
        lexer.setCurrent(scimoz)
        self._setIndicators(languageOb, scimoz)
        self._applyPrefs(document.prefs, scimoz)
        
        prefs = self.document.prefs

        if prefs.hasLongPref('anchor'):
            scimoz.currentPos = scimoz.anchor = prefs.getLongPref('anchor')

        if prefs.hasLongPref('currentPos'):
            scimoz.currentPos = prefs.getLongPref('currentPos')

        if prefs.hasPrefHere('indentWidth'):
            scimoz.indent = prefs.getLongPref('indentWidth')
        else:
            scimoz.indent = document.indentWidth

        if prefs.hasPrefHere('editUseAlternateFaceType'):
            useAlternate = prefs.getBooleanPref('editUseAlternateFaceType')
        else:
            useAlternate = 0
        scintilla.alternateFaceType = useAlternate
        self._updateEdge(prefs)
            
        if prefs.hasPrefHere('useTabs'):
            scimoz.useTabs = prefs.getBooleanPref('useTabs')
        else:
            scimoz.useTabs = document.useTabs

        if prefs.hasPrefHere('tabWidth'):
            scimoz.tabWidth = prefs.getLongPref('tabWidth')
        else:
            scimoz.tabWidth = document.tabWidth

        slop = prefs.getLongPref('ySlop')
        scimoz.setYCaretPolicy(scimoz.CARET_SLOP | scimoz.CARET_STRICT | scimoz.CARET_EVEN, slop)
        scimoz.setVisiblePolicy(scimoz.VISIBLE_SLOP | scimoz.VISIBLE_STRICT, slop)

        if prefs.hasLongPref('firstVisibleLine'):
            scimoz.lineScroll(0, prefs.getLongPref('firstVisibleLine'))

        if prefs.hasLongPref('scrollWidth'):
            scimoz.scrollWidth = prefs.getLongPref("scrollWidth")
        else:
            log.warn('should set default scroll width?')

        if prefs.hasLongPref('xOffset'):
            scimoz.xOffset = prefs.getLongPref('xOffset')
        else:
            scimoz.xOffset = 0
        
        # restore fold points if the user has checked that pref off.
        # We don't do it by default because the colourise(.., -1) call below
        # can be quite slow.
        if prefs.getBooleanPref("editRestoreFoldPoints") and \
           prefs.hasPref('foldPoints'):
            foldPoints = prefs.getPref("foldPoints")
            if foldPoints.length:
                # ensure the whole document is styled, we start at the last known
                # styled character and style to the end
                if scimoz.endStyled < scimoz.length:
                    scimoz.colourise(scimoz.endStyled, -1) # this is too bad...
                for i in range(foldPoints.length):
                    scimoz.toggleFold(foldPoints.getLongPref(i));

        # restore the bookmarks
        if prefs.hasPref("bookmarks"):
            bookmarks = prefs.getPref("bookmarks")
            for i in range(bookmarks.length):
                scimoz.markerAdd(bookmarks.getLongPref(i), MARKNUM_BOOKMARK)
        timeline.leave("koDocumentSettingsManager.applyDocumentSettingsToView")

    def setLongPrefIfDifferent(self, name, value):
        if self._globalPrefs.getLongPref(name) != value:
            self.document.prefs.setLongPref(name, value)

    def setBooleanPrefIfDifferent(self, name, value):
        if self.document.prefs.getBooleanPref(name) != value:
            self.document.prefs.setBooleanPref(name, value)

    def applyViewSettingsToDocument(self, scintilla):
        prefs = self.document.prefs
        # these should all be conditional on not being the
        # default prefs.
        scimoz = scintilla.scimoz
        prefs.setLongPref('anchor', scimoz.anchor)
        prefs.setLongPref('currentPos', scimoz.currentPos)
        prefs.setLongPref("scrollWidth", scimoz.scrollWidth)
        prefs.setLongPref('xOffset', scimoz.xOffset)
        prefs.setLongPref('firstVisibleLine', scimoz.firstVisibleLine)
        self.setBooleanPrefIfDifferent('showWhitespace', scimoz.viewWS)
        self.setBooleanPrefIfDifferent('showLineNumbers', scimoz.getMarginWidthN(0) != 0)
        self.setBooleanPrefIfDifferent('showIndentationGuides', scimoz.indentationGuides)
        self.setBooleanPrefIfDifferent('showEOL', scimoz.viewEOL)
        self.setBooleanPrefIfDifferent('editFoldLines', self._foldFlags) # XXX is this going to be a problem?
        #prefs.setStringPref('editFoldStyle', ... )
        #prefs.setStringPref('editUseFixedFont', ... )
        self.setLongPrefIfDifferent('editWrapType', scimoz.wrapMode)

        # these should be saved only if they were explicitely
        # set, not if they were just computed
        if prefs.hasPrefHere('useTabs'):
            prefs.setBooleanPref('useTabs', scimoz.useTabs)
        if prefs.hasPrefHere('indentWidth'):
            prefs.setLongPref('indentWidth', scimoz.indent)
        if prefs.hasPrefHere('tabWidth'):
            prefs.setLongPref('tabWidth', scimoz.tabWidth)

        foldPoints = components.classes[
            '@activestate.com/koOrderedPreference;1'].createInstance()
        foldPoints.id = "foldPoints"
        foldPoints.reset();
        lineLength = scimoz.lineCount;
        i = 0
        haveThem = {}
        for i in range(lineLength):
            if not scimoz.getLineVisible(i):
                foldParent = scimoz.getFoldParent(i)
                if (not scimoz.getFoldExpanded(foldParent) and 
                    foldParent not in haveThem):
                    foldPoints.appendLongPref(foldParent)
                    haveThem[foldParent] = 1
        if haveThem:
            prefs.setPref("foldPoints", foldPoints)
        else:
            # we don't want to store foldpoints if there are none
            # reloading them is expensive.
            if prefs.hasPref('foldPoints'):
                prefs.deletePref('foldPoints')

        # Get the bookmarks.
        bookmarks = components.classes[
            '@activestate.com/koOrderedPreference;1'].createInstance()
        bookmarks.id = "bookmarks"
        prefs.setPref("bookmarks", bookmarks)
        marker_mask = 1 << MARKNUM_BOOKMARK
        lineNo = -1
        while 1:
            lineNo = scimoz.markerNext(lineNo+1, marker_mask)
            if lineNo < 0:
                break
            bookmarks.appendLongPref(lineNo)

        #XXX Breakpoint restoring is now done elsewhere. Note that taking this
        #    out of the view prefs here breaks the transfer of breakpoints
        #    via a "Save As..." operation. See:
        #       views-editor.xml::saveAsURI(), line 609

    def _setIndicators(self, languageOb, scimoz):
        styleBits = languageOb.styleBits
        scimoz.styleBits = styleBits
        # Determine how many indicators we can have.
        indicBits = languageOb.indicatorBits

        #XXX Scintilla renames the indicators depending on the number of style bits :-(.
        #XXX Compensate.
        indicOffset = 8 - styleBits - indicBits
        if indicBits == 2:
            scimoz.indicSetStyle(indicOffset + 1, scimoz.INDIC_SQUIGGLE);
            scimoz.indicSetFore(indicOffset + 1, RGB(0xff,0,0));
            scimoz.indicSetStyle(indicOffset, scimoz.INDIC_SQUIGGLE);
            scimoz.indicSetFore(indicOffset, RGB(0,0x80,0));
        else:
            scimoz.indicSetStyle(indicOffset, scimoz.INDIC_SQUIGGLE);
            scimoz.indicSetFore(indicOffset, RGB(0xff,0,0));
        DECORATOR_ERROR = components.interfaces.koILintResult.DECORATOR_ERROR
        DECORATOR_WARNING = components.interfaces.koILintResult.DECORATOR_WARNING
        for i in [DECORATOR_ERROR, DECORATOR_WARNING]:
            scimoz.indicSetUnder(i, True) # draw under
            scimoz.indicSetStyle(i, scimoz.INDIC_SQUIGGLE)
        scimoz.indicSetFore(DECORATOR_ERROR, RGB(0xff,0,0))
        scimoz.indicSetFore(DECORATOR_WARNING, RGB(0x00, 0x80,0))
        
        DECORATOR_UDL_FAMILY_TRANSITION = components.interfaces.koILintResult.DECORATOR_UDL_FAMILY_TRANSITION
        scimoz.indicSetStyle(DECORATOR_UDL_FAMILY_TRANSITION, scimoz.INDIC_HIDDEN)
        ## For debugging, to show the UDL family transitions:
        #scimoz.indicSetStyle(components.interfaces.koILintResult.DECORATOR_UDL_FAMILY_TRANSITION,
        #                     scimoz.INDIC_ROUNDBOX)
        #scimoz.indicSetFore(DECORATOR_UDL_FAMILY_TRANSITION, RGB(0,0x80,0))
        
    def _updateLineNumberMargin(self):
        for scintilla in self._scintillas:
            scintilla.scimoz.setMarginWidthN(0,
                scintilla.scimoz.textWidth(0,
                    str(max(1000,scintilla.scimoz.lineCount*2)))+5)

    # nsIObserver interface
    def observe(self, prefSet, topic, data):
        if (self.document and topic == self.document.prefs.id) or \
           topic == self._globalPrefs.id:
            # Dispatch a preference change...
            self._dispatchPrefChange(prefSet, data)
        else:
            log.warn("Unexpected Observe() topic %s" % data)

    # Probably should make this function table-based to reduce
    # duplication of effort.
    def _dispatchPrefChange(self, prefSet, prefName):
        if hasattr(self, "_apply_" + prefName):
            getattr(self, "_apply_" + prefName)(prefSet)

    def _apply_ySlop(self, prefSet):
        for scintilla in self._scintillas:
            scimoz = scintilla.scimoz
            scimoz.setYCaretPolicy(scimoz.CARET_SLOP | scimoz.CARET_STRICT | scimoz.CARET_EVEN,
                                   prefSet.getLongPref('ySlop'))

    def _apply_useTabs(self, prefSet):
        for scintilla in self._scintillas:
            scintilla.scimoz.useTabs = prefSet.getBooleanPref('useTabs')

    def _apply_indentWidth(self, prefSet):
        #print 'setting indentWidth = ', prefSet.getLongPref('indentWidth')
        for scintilla in self._scintillas:
            scintilla.scimoz.indent = prefSet.getLongPref('indentWidth')

    def _apply_tabWidth(self, prefSet):
        for scintilla in self._scintillas:
            scintilla.scimoz.tabWidth = prefSet.getLongPref('tabWidth')

    def _apply_showWhitespace(self, prefSet):
        for scintilla in self._scintillas:
            scintilla.scimoz.viewWS = prefSet.getBooleanPref('showWhitespace')

    def _apply_editWrapType(self, prefSet):
        editWrapType= prefSet.getLongPref('editWrapType')
        if editWrapType:
            for scintilla in self._scintillas:
                scimoz = scintilla.scimoz
                scimoz.wrapMode = editWrapType
                scimoz.layoutCache = scimoz.SC_CACHE_PAGE
        else:
            for scintilla in self._scintillas:
                scimoz = scintilla.scimoz
                scimoz.wrapMode = scimoz.SC_WRAP_NONE
                scimoz.layoutCache = scimoz.SC_CACHE_NONE

    def _apply_editWordWrapMarker(self, prefSet):
        editWordWrapMarker= prefSet.getLongPref('editWordWrapMarker')
        for scintilla in self._scintillas:
            scintilla.scimoz.wrapVisualFlags = editWordWrapMarker

    def _apply_editUseEdge(self, prefSet):
        self._updateEdge(prefSet)

    def _updateEdge(self, prefSet):
        if prefSet.getBooleanPref('editUseEdge'):
            for scintilla in self._scintillas:
                scintilla.scimoz.edgeColumn = prefSet.getLongPref('editAutoWrapColumn')
                if scintilla.scheme.preferFixed and not scintilla.alternateFaceType:
                    scintilla.scimoz.edgeMode = scintilla.scimoz.EDGE_LINE
                else:
                    scintilla.scimoz.edgeMode = scintilla.scimoz.EDGE_BACKGROUND
        else:
            for scintilla in self._scintillas:
                scintilla.scimoz.edgeMode = scintilla.scimoz.EDGE_NONE
            
    def _apply_editAutoWrapColumn(self, prefSet):
        self._updateEdge(prefSet)

    def _apply_editUseAlternateFaceType(self, prefSet):
        self._updateEdge(prefSet)

    def _apply_showIndentationGuides(self, prefSet):
        for scintilla in self._scintillas:
            scintilla.scimoz.indentationGuides = prefSet.getBooleanPref('showIndentationGuides')

    def _apply_showEOL(self, prefSet):
        for scintilla in self._scintillas:
            scintilla.scimoz.viewEOL = prefSet.getBooleanPref('showEOL')

    def _apply_showLineNumbers(self, prefSet):
        if prefSet.getBooleanPref('showLineNumbers'):
            self._updateLineNumberMargin()
        else:
            for scintilla in self._scintillas:
                scintilla.scimoz.setMarginWidthN(0, 0)

    def _apply_caretStyle(self, prefSet):
        caretStyle = prefSet.getLongPref('caretStyle')
        for scintilla in self._scintillas:
            scintilla.scimoz.caretStyle = caretStyle

    def _apply_caretWidth(self, prefSet):
        caretWidth = prefSet.getLongPref('caretWidth')
        for scintilla in self._scintillas:
            scintilla.scimoz.caretWidth = caretWidth

    def _apply_editFoldLines(self, prefSet):
        on = prefSet.getBooleanPref('editFoldLines')
        # scintilla doesn't provide an accessor for fold flags
        if on and self._scintillas:
            self._foldFlags = self._scintillas[0].scimoz.SC_FOLDFLAG_LINEAFTER_CONTRACTED
        else:
            self._foldFlags = 0
        for scintilla in self._scintillas:
            scintilla.scimoz.setFoldFlags(self._foldFlags)

    def _apply_editFoldStyle(self, prefSet):
        # use margin 1 for folding
        if not self.document.languageObj.foldable:
            for scintilla in self._scintillas:
                scintilla.scimoz.setProperty("fold", "0")
                scintilla.scimoz.setMarginWidthN(1, 0)
            return
        foldstyle = prefSet.getStringPref('editFoldStyle')
        if foldstyle != 'none':
            self._enableFolding(1, foldstyle)
            # we'll just work with one of the views
            scimoz = self._scintillas[0].scimoz
            # XXX review logic
            lastLine = min(scimoz.firstVisibleLine + scimoz.linesOnScreen,
                           scimoz.lineCount-1)
            needStyleTo = scimoz.positionFromLine(lastLine)
            if scimoz.endStyled < needStyleTo:
                scimoz.colourise(scimoz.endStyled, needStyleTo)
            for scintilla in self._scintillas:
                scintilla.scimoz.setMarginWidthN(1, 15)
        else:
            for scintilla in self._scintillas:
                scimoz = scintilla.scimoz
                scimoz.showLines(0, scimoz.lineCount-1)
                for line in range(scimoz.lineCount):
                    if (scimoz.getFoldLevel(line) &
                        scimoz.SC_FOLDLEVELHEADERFLAG):
                        scimoz.setFoldExpanded(line, 1)
                # If we don't do this, folding trails off into other buffers.
                scimoz.setProperty("fold", "0")
                scimoz.setMarginWidthN(1, 0)
            
    def _apply_encoding(self, prefSet):
        if prefSet.hasStringPref('encoding'):
            for scintilla in self._scintillas:
                scintilla.encoding = prefSet.getStringPref('encoding')
    
    def _applyPrefs(self, prefs, scimoz):
        timeline.enter('_applyPrefs')
        for prefName in self._viewPrefList:
            self._dispatchPrefChange(prefs, prefName)
        timeline.leave('_applyPrefs')
            
    def _apply_Default_fixed(self, prefSet):
        pass
        #self._applyStyles()
            
    def _apply_Default_proportional(self, prefSet):
        pass
        #self._applyStyles()
    
    def _enableFolding(self, whichMargin, foldstyle):
        for scin in self._scintillas:
            scin.setFoldStyle(whichMargin, foldstyle)

