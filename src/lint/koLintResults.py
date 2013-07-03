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

"""The KoLintResults PyXPCOM component manages a set of lint results for
a file.
"""

from xpcom import components
from xpcom.server import WrapObject, UnwrapObject


#---- internal support routines

def _sortByNextLineFirst(lines, curLine):
    before = []
    after = []
    for line in lines:
        if line <= curLine:
            before.append(line)
        elif line > curLine:
            after.append(line)
    return after + before


#---- component

class koLintResults:
    _com_interfaces_ = [components.interfaces.koILintResults]

    def __init__(self):
        self.clear()

    def getResults(self):
        return self._results

    def getResultsInLineRange(self, start, end):
        #XXX:PERF Upgrade this to use the self._resultMap as in
        #         getResultsAtPosition()
        releventResults = []
        for r in self._results:
            if start <= r.lineEnd <= end or start <= r.lineStart <= end or (r.lineStart < start and r.lineEnd > end):
                releventResults.append(r)
        return releventResults
    
    def getResultsAtPosition(self, line, column):
        # find the results spanning the given position
        results = []
        for r in self._resultMap.get(line, []):
            # There is a (perhaps partial) result on this line.
            # Is the given position within that result?
            if (
                 r.lineStart == line and r.columnStart <= column
                 or
                 r.lineStart < line
               ) and (
                 r.lineEnd == line and column <= r.columnEnd
                 or
                 line < r.lineEnd
               ):
                results.append(r)
        return results

    def clear(self):
        self._results = []
        self._resultMap = {}

    def addResult(self, result):
        """Besides the plain old results list, also maintain a mapping
        for fast lookup via the getResults*() methods.

        Typically all lintResults will only span one line and typically
        there will not be many results per line (generally there is only
        one). A dictionary with keys being line numbers including any
        part of a lint result and values being a list of lint results on
        any part of that line will allow faster lookup.
        """
        lineStart = result.lineStart
        for r in self._resultMap.get(lineStart, []):
            if r.lineEnd == result.lineEnd:
                # Because we can now use multiple linters for a document,
                # some linters will report identical results.  Cull the duplicates.
                if (r.columnStart == result.columnStart
                    and r.columnEnd == result.columnEnd
                    and r.severity == result.severity
                    and r.description == result.description):
                    # Cull duplicate results
                    return
                # Bug 93326: If we have overlapping errors and warnings on the same line,
                # hoist both of them up to a warning
                if r.severity != result.severity:
                    #XXX: If we add a third kind of severity, this is wrong
                    if (r.columnEnd >= result.columnStart
                        or result.columnEnd >= r.columnStart):
                        if result.severity == r.SEV_WARNING:
                            result.severity = r.SEV_ERROR
                        else:
                            r.severity = r.SEV_ERROR
                
        self._results.append(result)
        for lineNum in range(lineStart, result.lineEnd+1):
            if self._resultMap.has_key(lineNum):
                self._resultMap[lineNum].append(result)
            else:
                self._resultMap[lineNum] = [result]

    def addResults(self, other):
        try:
            other_results = other._results
        except AttributeError:
            other_results = UnwrapObject(other)._results
        for result in other_results:
            self.addResult(result)

    # Convenience methods (for status bar UI).
    def getNumResults(self):
        return len(self._results)

    def getNumWarnings(self):
        warns = [r for r in self._results if r.severity == r.SEV_WARNING]
        return len(warns)

    def getNumErrors(self):
        errors = [r for r in self._results if r.severity == r.SEV_ERROR]
        return len(errors)
    
    def getNextResult(self, line, column):
        if self._results:
            # If there is a result at the current position, then start
            # looking beyond it.
            resultsAtPos = self.getResultsAtPosition(line, column)
            for result in resultsAtPos:
                line = result.lineEnd
                column = result.columnEnd

            # Look forward for next result, wrapping if necessary.
            lines = self._resultMap.keys()
            lines.sort()
            if line in lines:
                # Special case of results on the current line.
                for r in self._resultMap[line]:
                    if r in resultsAtPos:
                        # "Next" cannot be one spanning the current position.
                        continue
                    if r.lineStart == line and r.columnStart >= column:
                        return r
            
            lines = _sortByNextLineFirst(lines, line)
            return self._resultMap[lines[0]][0]
        else:
            return None

