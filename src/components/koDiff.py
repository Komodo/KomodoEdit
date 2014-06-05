import os
import sys
import re
import difflib

from zope.cachedescriptors.property import LazyClassAttribute

from xpcom import components, nsError, ServerException
from xpcom.client import WeakReference

import eollib
import difflibex

class KoDiff:
    _com_interfaces_ = [components.interfaces.koIDiff]
    _reg_desc_ = "Komodo Document Diff"
    _reg_contractid_ = "@activestate.com/koDiff;1"
    _reg_clsid_ = "{5faaa9b1-4c2f-41d1-936d-22d2e24768c5}"
    
    @LazyClassAttribute
    def docSvc(self):
        return components.classes["@activestate.com/koDocumentService;1"].\
                    getService(components.interfaces.koIDocumentService)

    def __init__(self):
        self._reset()

    def _reset(self):
        self.doc1 = None
        self.doc2 = None
        self.diff = None
        self._diffex = None
        self.warning = None

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
        doc1 = self.docSvc.createDocumentFromURI(fname1)
        doc1.load()
        doc2 = self.docSvc.createDocumentFromURI(fname2)
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
            self.lastErrorSvc.setLastError(0, str(ex))
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
            self.lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))

    def inferCwdAndStripFromPath(self, pathInDiff, actualPath):
        try:
            return difflibex.infer_cwd_and_strip_from_path(pathInDiff,
                                                           actualPath)
        except difflibex.DiffLibExError, ex:
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))
