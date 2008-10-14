#!python 
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

# Implementation of the tree view for displaying CGI Variable prefs

from xpcom import components
import sys, os, re, types, string
import logging, urllib
from koTreeView import TreeView


log = logging.getLogger("koEnvView")


class KoEnvironmentView(TreeView):
    _com_interfaces_ = [components.interfaces.koIEnvironmentView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{83DC7ECB-E959-4050-9449-D2A51394FD6A}"
    _reg_contractid_ = "@activestate.com/KoEnvironmentView;1"
    _reg_desc_ = "Komodo Environment Variable Tree Table View"

    def __init__(self):
        TreeView.__init__(self, debug=0)
        self._data = []
        self._sortedBy = None

    def get_rowCount(self):
        return len(self._data)

    def getCellText(self, row, column):
        col = column.id
        try:
            datum = self._data[row][col]
        except IndexError:
            # Silence this, it is too annoying.
            # c.f. http://bugs.activestate.com/show_bug.cgi?id=27487
            #log.error("no %sth result", row)
            return ""
        except KeyError:
            log.error("unknown column id: '%s'", col)
            return ""
        if type(datum) not in (types.StringType, types.UnicodeType):
            datum = str(datum)
        return datum

    def Clear(self):
        length = len(self._data)
        self._data = []
        self._sortedBy = None
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(0, length)
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def AddVariable(self, name, value):
        datum = {
            "name": _normalizeEnvVarName(name),
            "value": value
        }
        self._data.append(datum)
        self._sortedBy = None
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(len(self._data)-2, 1)
        self._tree.invalidate()  #XXX invalidating too much here?
        self._tree.endUpdateBatch()
        currentIndex = len(self._data) - 1
        self._tree.view.selection.select(currentIndex)

    def haveVariable(self, name):
        normname = _normalizeEnvVarName(name)
        for i in range(len(self._data)):
            if self._data[i]["name"] == normname:
                return i
        return -1

    def removeRow(self, index):
        if index >=0 and len(self._data) > 0:
            self._data.pop(index)
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(len(self._data)-2, 1)
            self._tree.invalidate()  #XXX invalidating too much here?
            self._tree.endUpdateBatch()
        currentIndex = -1
        if len(self._data) > 0:
            if index > 0:
                currentIndex = index - 1
            else:
                currentIndex = 0
        self._tree.view.selection.select(currentIndex)
            
    
    def GetVariable(self, index):
        return "%s=%s" % (self._data[index]["name"],self._data[index]["value"])
    def GetName(self, index):
        return self._data[index]["name"]
    def GetValue(self, index):
        return self._data[index]["value"]

    def Sort(self, sortBy):
        self._sort(sortBy, True)

    def _sort(self, sortBy, invalidate):
        """Sort the current data by the given key. If already sorted by this
        key then reverse the sorting order."""
        if self._sortedBy == sortBy:
            self._data.reverse()
        else:
            try:
                self._data.sort(lambda dict1,dict2,sortBy=sortBy:
                                    cmp(dict1[sortBy], dict2[sortBy])
                               )
            except KeyError:
                log.error("Cannot sort Environment Variables by: '%s'", sortBy)
                raise
            self._sortedBy = sortBy
        if invalidate:
            self._tree.beginUpdateBatch()
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def setVariables(self, envvars):
        senv = string.split(envvars, "\n") # XXX, mozilla only returns \n ????
        for i in range(len(senv)):
            senv[i].strip()
            if not senv[i] or senv[i].find('=') == -1:   # skip empty lines
                continue
            name, value = senv[i].split("=", 1)
            datum = {"name": name,
                     "value": value}
            self._data.append(datum)
        self._sortedBy = None
        self._sort("name", False);
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(len(self._data)-2, 1)
        self._tree.invalidate()  #XXX invalidating too much here?
        self._tree.endUpdateBatch()

    def getVariables(self):
        ret = ""
        for i in range(len(self._data)):
            ret += self._data[i]["name"] +"="+ self._data[i]["value"]+"\n"
        return ret



#---- internal support stuff

def _normalizeEnvVarName(name):
    """Environment variable names are case-insensitive on Windows
    and case-sensitive on other platforms.
    """
    if sys.platform == "win32":
        return name.upper()
    else:
        return name
