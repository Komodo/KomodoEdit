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

import sys
import os
import types
import re
import logging
from xpcom import components, nsError, ServerException, COMException
from koTreeView import TreeView

log = logging.getLogger("koWindowsIntegrationService")
#log.setLevel(logging.DEBUG)


#---- component implementation

_gExtSplitter = re.compile('[;:,]') # be liberal about splitter char

class KoExtensionsView(TreeView):
    _com_interfaces_ = [components.interfaces.koIExtensionsView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{3C670678-691D-4128-BD16-4E8C190A3488}"
    _reg_contractid_ = "@activestate.com/koExtensionsView;1"
    _reg_desc_ = "Komodo File Extensions List View"

    def __init__(self):
        TreeView.__init__(self, debug=0)
        self._exts = []
        # A string key indicating by which column the data is
        # sorted.
        self._sortedBy = None

    def get_rowCount(self):
        return len(self._exts)

    def getCellText(self, row, column):
        """Get the value for the specified cell.
        "row" is an index into the current order (self._order).
        "col" is an 'id' of the <treecol> element. It is ignored
            here because there is only one column: the extension.
        """
        try:
            cell = self._exts[row]
        except IndexError:
            logError("no %sth row of data" % row)
            return ""

        if type(cell) not in (types.StringType, types.UnicodeType):
            cell = str(cell)
        return cell

    def Add(self, ext):
        if ext[0] != '.':
            raise ServerException(nsError.NS_ERROR_INVALID_ARG,
                      "Extension must start with a dot: '%s'" % ext)
        if sys.platform.startswith("win"):
            ext = ext.lower()
        if ext not in self._exts:
            self._exts.append(ext)
            self._sortedBy = None
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(len(self._exts)-2, 1)
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def Remove(self, ext):
        try:
            self._exts.remove(ext)
        except ValueError, ex:
            pass
        else:
            self._tree.beginUpdateBatch()
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def RemoveIndex(self, index):
        del self._exts[index]
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def Get(self, index):
        return self._exts[index]

    def GetExtensions(self):
        return os.pathsep.join(self._exts)

    def SetExtensions(self, extensions):
        self._exts = _gExtSplitter.split(extensions)
        self._exts = [ext for ext in self._exts if ext] # cull empty strings

    def Sort(self, sortBy):
        """Sort the current data by the given key.
        If already sorted by this key then reverse the sorting order.
        """
        if self._sortedBy == sortBy:
            self._exts.reverse()
        else:
            self._exts.sort()
        self._sortedBy = sortBy
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()


class KoWindowsIntegrationService:
    _com_interfaces_ = [components.interfaces.koIWindowsIntegrationService]
    _reg_clsid_ = "{61DD412D-719B-4240-9362-07C2F5C2D68C}"
    _reg_contractid_ = "@activestate.com/koWindowsIntegrationService;1"
    _reg_desc_ = "Service for integrating Komodo into the Windows OS"

    def __init__(self):
        self.lastErrorSvc = components.classes["@activestate.com/koLastErrorService;1"]\
            .getService(components.interfaces.koILastErrorService)
        koDirs = components.classes["@activestate.com/koDirs;1"]\
            .getService(components.interfaces.koIDirs)
        self._komodo = os.path.join(koDirs.binDir, "komodo.exe")

    def _addFileAssociation(self, ext, action):
        import wininteg
        try:
            wininteg.addFileAssociation(ext, action, self._komodo)
        except WindowsError, ex:
            self.lastErrorSvc.setLastError(ex.errno, ex.strerror)
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, ex.strerror)
        except EnvironmentError, ex:
            self.lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))

    def _removeFileAssociation(self, ext, action):
        import wininteg
        try:
            wininteg.removeFileAssociation(ext, action, self._komodo)
        except WindowsError, ex:
            self.lastErrorSvc.setLastError(ex.errno, ex.strerror)
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, ex.strerror)
        except EnvironmentError, ex:
            self.lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))

    def _checkFileAssociation(self, ext, action):
        """Check that the given file association matches that in the system.
        Returns None if so, a text error message otherwise.
        """
        import wininteg
        try:
            return wininteg.checkFileAssociation(ext, action, self._komodo)
        except WindowsError, ex:
            self.lastErrorSvc.setLastError(ex.errno, ex.strerror)
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, ex.strerror)
        except EnvironmentError, ex:
            self.lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))

    def _setHKLMRegistryStringValue(self, keyName, valueName, value):
        import wininteg, _winreg
        try:
            wininteg.setHKLMRegistryValue(keyName, valueName, _winreg.REG_SZ,
                                          value)
        except EnvironmentError, ex:
            self.lastErrorSvc.setLastError(0, str(ex))
            raise ServerException(nsError.NS_ERROR_UNEXPECTED, str(ex))

    def _getHKLMRegistryStringValue(self, keyName, valueName):
        """Get the given string value from the registry or the empty
        string iff it does not exist.
        """
        import wininteg, _winreg
        try:
            value, valueType = wininteg.getHKLMRegistryValue(keyName,
                                                             valueName)
        except EnvironmentError, ex:
            return ""

        if valueType != _winreg.REG_SZ:
            return ""
        else:
            return value

    def _normalizeEncodedAssocs(self, encodedAssocs):
        assocs = [a.strip() for a in _gExtSplitter.split(encodedAssocs)
                  if a.strip()]
        return ';'.join(assocs)

    def getEditAssociations(self):
        encodedAssocs = self._getHKLMRegistryStringValue(
            "SOFTWARE\\ActiveState\\Komodo", "editAssociations")
        encodedAssocs = self._normalizeEncodedAssocs(encodedAssocs)
        return encodedAssocs.lower()

    def setEditAssociations(self, encodedAssocs):
        encodedAssocs = encodedAssocs.lower()
        currAssocs = [a.strip()
            for a in _gExtSplitter.split(self.getEditAssociations())
            if a.strip()]
        newAssocs = [unicode(a.strip())
            for a in _gExtSplitter.split(encodedAssocs)
            if a.strip()]
        for currAssoc in currAssocs:
            if currAssoc not in newAssocs:
                self._removeFileAssociation(currAssoc, "Edit")
        for newAssoc in newAssocs:
            self._addFileAssociation(newAssoc, "Edit")
        self._setHKLMRegistryStringValue("SOFTWARE\\ActiveState\\Komodo",
                                         "editAssociations", encodedAssocs)

    def getEditWithAssociations(self):
        encodedAssocs = self._getHKLMRegistryStringValue(
            "SOFTWARE\\ActiveState\\Komodo", "editWithAssociations")
        encodedAssocs = self._normalizeEncodedAssocs(encodedAssocs)
        return encodedAssocs.lower()

    def setEditWithAssociations(self, encodedAssocs):
        encodedAssocs = encodedAssocs.lower()
        currAssocs = [a.strip()
            for a in _gExtSplitter.split(self.getEditWithAssociations())
            if a.strip()]
        newAssocs = [unicode(a.strip())
            for a in _gExtSplitter.split(encodedAssocs)
            if a.strip()]
        for currAssoc in currAssocs:
            if currAssoc not in newAssocs:
                self._removeFileAssociation(currAssoc, "Edit with Komodo")
        for newAssoc in newAssocs:
            self._addFileAssociation(newAssoc, "Edit with Komodo")
        self._setHKLMRegistryStringValue("SOFTWARE\\ActiveState\\Komodo",
                                         "editWithAssociations",
                                         encodedAssocs)

    def checkAssociations(self):
        messages = []
        editAssocs = [a for a in self.getEditAssociations().split(';') if a]
        for assoc in editAssocs:
            msg = self._checkFileAssociation(assoc, "Edit")
            if msg is not None:
                messages.append(msg)
        editWithAssocs = [a for a in self.getEditWithAssociations().split(';') if a]
        for assoc in editWithAssocs:
            msg = self._checkFileAssociation(assoc, "Edit with Komodo")
            if msg is not None:
                messages.append(msg)
        if not messages:
            return None
        else:
            #XXX Better error message?
            return '\n'.join(messages)

