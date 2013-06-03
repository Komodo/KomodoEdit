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

# Implementation of the tree view for displaying find results in the find
# results tab in the output pane of Komodo.

from xpcom import components
import logging
log = logging.getLogger('koFindResultsView')
import sys, os, re, types
from koTreeView import TreeView

class KoFindResultsView(TreeView):
    _com_interfaces_ = [components.interfaces.koIFindResultsView,
                        components.interfaces.nsITreeView]
    _reg_clsid_ = "{154CF0D6-D556-4be5-9F55-65AE5DB46312}"
    _reg_contractid_ = "@activestate.com/koFindResultsView;1"
    _reg_desc_ = "Komodo Find Results Tree Table View"

    _columns = None

    def __init__(self):
        TreeView.__init__(self, debug=0)
        #TODO: lock guard for this data
        self._data = []
        self._unfiltered_data = []
        # When set (not None), it's a tuple of (include_word_list, exclude_word_list)
        self._filter_words = None
        self._tree = None
        self._sortedBy = None
        self.id = None

        atomSvc = components.classes["@mozilla.org/atom-service;1"].\
                  getService(components.interfaces.nsIAtomService)
        self._warning_atom = atomSvc.getAtom("warning")

    def get_rowCount(self):
        return len(self._data)

    def getCellText(self, row, column):
        try:
            datum = self._data[row][column.id]
        except IndexError:
            # Silence this, it is too annoying.
            # c.f. http://bugs.activestate.com/show_bug.cgi?id=27487
            #log.error("no %sth find result" % row)
            return ""
        except KeyError:
            log.error("unknown find result column id: '%s'" % column.id)
            return ""
        if type(datum) not in (types.StringType, types.UnicodeType):
            datum = str(datum)
        return datum

    def getCellProperties(self, row_idx, col, properties=None):
        # Only for the "Content" column cells.
        if not col.id.endswith("-context"):
            return
        datum = self._data[row_idx]
        if datum["type"] == "warning":
            # Mozilla 22+ does not have a properties argument.
            if properties is None:
                return "warning"
            else:
                properties.AppendElement(self._warning_atom)

    def getRowProperties(self, row_idx, properties=None):
        datum = self._data[row_idx]
        if datum["type"] == "warning":
            # Mozilla 22+ does not have a properties argument.
            if properties is None:
                return "warning"
            else:
                properties.AppendElement(self._warning_atom)

    def Clear(self):
        length = len(self._data)
        self._data = []
        self._unfiltered_data = []
        self._filter_words = None
        self._sortedBy = None
        self._tree.beginUpdateBatch()
        self._tree.rowCountChanged(0, -length)
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    def AddFindResult(self, type, url, startIndex, endIndex, value,
                      fileName, lineNum, columnNum, context):
        len_before = len(self._data)
        rows_added = 0
        datum = {"type": type,
                 "url": url,
                 "startIndex": startIndex,
                 "endIndex": endIndex,
                 "value": value,
                 "lineNum": lineNum,
                 "columnNum": columnNum,
                 "findresults-filename": fileName,
                 "findresults-linenum": lineNum,
                 "findresults-context": context}
        if type == "warning":
            datum["findresults-linenum"] = "-"

        self._unfiltered_data.append(datum)
        if not self._filter_words or \
           self._filterMatchesDatam(datum, self._filter_words):
            self._data.append(datum)
            rows_added += 1

        if rows_added:
            self._sortedBy = None
            self._tree.rowCountChanged(len_before-1, rows_added)
            self._tree.invalidateRow(len_before)

    def AddFindResults(self, types, urls, startIndexs, endIndexs, values,
                       fileNames, lineNums, columnNums, contexts):
        len_before = len(self._data)
        rows_added = 0
        for (type, url, startIndex, endIndex, value, fileName, lineNum,
             columnNum, context) in zip(types, urls, startIndexs, endIndexs,
                                        values, fileNames, lineNums,
                                        columnNums, contexts):
            datum = {"type": type,
                     "url": url,
                     "startIndex": startIndex,
                     "endIndex": endIndex,
                     "value": value,
                     "lineNum": lineNum,
                     "columnNum": columnNum,
                     "findresults-filename": fileName,
                     "findresults-linenum": lineNum,
                     "findresults-context": context}
            if type == "warning":
                datum["findresults-linenum"] = "-"

            self._unfiltered_data.append(datum)
            if not self._filter_words or \
               self._filterMatchesDatam(datum, self._filter_words):
                self._data.append(datum)
                rows_added += 1

        if rows_added:
            self._sortedBy = None
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(len_before-1, rows_added)
            self._tree.invalidateRange(len_before, len_before+rows_added)
            self._tree.endUpdateBatch()

    def AddReplaceResult(self, type, url, startIndex, endIndex, value,
                         replacement, fileName, lineNum, columnNum,
                         context):
        len_before = len(self._data)
        rows_added = 0
        datum = {"type": type,
                 "url": url,
                 "startIndex": startIndex,
                 "endIndex": endIndex,
                 "value": value,
                 "replacement": replacement,
                 "lineNum": lineNum,
                 "columnNum": columnNum,
                 "findresults-filename": fileName,
                 "findresults-linenum": lineNum,
                 "findresults-context": context}
        if type == "warning":
            datum["findresults-linenum"] = "-"

        self._unfiltered_data.append(datum)
        if not self._filter_words or \
           self._filterMatchesDatam(datum, self._filter_words):
            self._data.append(datum)
            rows_added += 1

        if rows_added:
            self._sortedBy = None
            self._tree.rowCountChanged(len_before-1, rows_added)
            self._tree.invalidateRow(len_before)

    def AddReplaceResults(self, types, urls, startIndexs, endIndexs,
                          values, replacements, fileNames,
                          lineNums, columnNums, contexts):
        len_before = len(self._data)
        rows_added = 0
        for (type, url, startIndex, endIndex, value, replacement,
             fileName, lineNum, columnNum, context
             ) in zip(types, urls, startIndexs, endIndexs, values,
                      replacements, fileNames, lineNums, columnNums,
                      contexts):
            datum = {"type": type,
                     "url": url,
                     "startIndex": startIndex,
                     "endIndex": endIndex,
                     "value": value,
                     "replacement": replacement,
                     "lineNum": lineNum,
                     "columnNum": columnNum,
                     "findresults-filename": fileName,
                     "findresults-linenum": lineNum,
                     "findresults-context": context}
            if type == "warning":
                datum["findresults-linenum"] = "-"

            self._unfiltered_data.append(datum)
            if not self._filter_words or \
               self._filterMatchesDatam(datum, self._filter_words):
                self._data.append(datum)
                rows_added += 1

        if rows_added:
            self._sortedBy = None
            self._tree.beginUpdateBatch()
            self._tree.rowCountChanged(len_before-1, rows_added)
            self._tree.invalidateRange(len_before, len_before+rows_added)
            self._tree.endUpdateBatch()

    def GetType(self, index):
        return self._data[index]["type"]
    def GetUrl(self, index):
        return self._data[index]["url"]
    def GetStartIndex(self, index):
        return self._data[index]["startIndex"]
    def GetEndIndex(self, index):
        return self._data[index]["endIndex"]
    def GetValue(self, index):
        return self._data[index]["value"]
    def GetReplacement(self, index):
        try:
            return self._data[index]["replacement"]
        except KeyError:
            return ""
    def GetLineNum(self, index):
        return self._data[index]["lineNum"]
    def GetColumnNum(self, index):
        return self._data[index]["columnNum"]

    def Sort(self, sortBy):
        """Sort the current data by the given key. If already sorted by this
        key then reverse the sorting order."""
        if self._sortedBy == sortBy:
            self._data.reverse()
        else:
            try:
                if sortBy == "findresults-context":
                    # strip leading whitespace for context sort order
                    self._data.sort(lambda dict1,dict2,sortBy=sortBy:
                                        cmp(dict1[sortBy].lstrip(), dict2[sortBy].lstrip())
                                   )
                else:
                    self._data.sort(lambda dict1,dict2,sortBy=sortBy:
                                        cmp(dict1[sortBy], dict2[sortBy])
                                   )
            except KeyError:
                log.error("Cannot sort find results by: '%s'" % sortBy)
                raise
        self._sortedBy = sortBy
        self._tree.beginUpdateBatch()
        self._tree.invalidate()
        self._tree.endUpdateBatch()

    @property
    def columns(self):
        # Get the list of treecolumn objects.
        columns = self._columns
        if columns is None:
            columns = []
            tree_columns = self._tree.columns
            for col_num in range(tree_columns.count):
                columns.append(tree_columns.getColumnAt(col_num))
            self._columns = columns
        return columns

    def _filterMatchesDatam(self, datum, filterData):
        column_texts = []
        for column in self.columns:
            # Modified form of getCellText:
            celltext = datum[column.id]
            if type(celltext) not in (types.StringType, types.UnicodeType):
                celltext = str(celltext)
            else:
                celltext = celltext.lower()
            column_texts.append(celltext)

        # Match can be against any column.
        matched = False
        include_words, exclude_words = filterData
        for text in column_texts:
            for word in include_words:
                if word not in text:
                    break
            else:
                matched = True
                break
        if matched and exclude_words:
           for word in exclude_words:
                for text in column_texts:
                    if word in text:
                        matched = False
                        break
                if not matched:
                    break
        return matched

    def _filterData(self, data, words):
        if not data or not words:
            return data
        new_data = []
        row_count = len(data)

        # Filter all the data rows.
        for row_num in range(row_count):
            if self._filterMatchesDatam(data[row_num], words):
                new_data.append(data[row_num])
        return new_data

    def SetFilterText(self, text):
        old_words = self._filter_words

        if not text:
            self._filter_words = None
        else:
            import shlex
            # Note: shlex does not handle Unicode - so we encode as utf8.
            try:
                words = shlex.split(text.lower().encode("utf8"))
                words = [x.decode("utf8") for x in words]
            except ValueError:
                # Shlex couldn't handle it - default to space separated.
                words = text.lower().split()
            out_words = [x for x in words if x.startswith("-")]
            # Tuple of (in_words, out_words)
            self._filter_words = (tuple(set(words).difference(out_words)),
                                  tuple([x[1:] for x in out_words if len(x) > 1]))

        if old_words != self._filter_words:
            # Re-filter the unfiltered rows.
            len_before = len(self._data)
            self._data = self._filterData(self._unfiltered_data, self._filter_words)
            self._tree.beginUpdateBatch()
            if len_before != len(self._data):
                self._tree.rowCountChanged(0, len(self._data) - len_before)
            self._tree.invalidate()
            self._tree.endUpdateBatch()

    def GetNumUrls(self):
        urlDict = {}
        for datum in self._data:
            if datum["type"] != "hit":
                continue
            urlDict[datum["url"]] = 1
        return len(urlDict.keys())

