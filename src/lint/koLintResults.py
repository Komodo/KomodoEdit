
"""The KoLintResults PyXPCOM component manages a set of lint results for
a file.
"""

from xpcom import components


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
        self._results.append(result)
        for lineNum in range(result.lineStart, result.lineEnd+1):
            if self._resultMap.has_key(lineNum):
                self._resultMap[lineNum].append(result)
            else:
                self._resultMap[lineNum] = [result]

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

