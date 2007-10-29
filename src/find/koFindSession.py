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

# The implementation of the Komodo Find Session component

from xpcom import components
import logging


#---- globals

log = logging.getLogger("find.session")
#log.setLevel(logging.DEBUG)



#---- find and replace components

class KoFindSession:
    _com_interfaces_ = [components.interfaces.koIFindSession]
    _reg_desc_ = "Find Session"
    _reg_clsid_ = "{A037424A-1021-44ca-B62E-B9A58AD5D562}"
    _reg_contractid_ = "@activestate.com/koFindSession;1"

    def __init__(self):
        self.Reset()

    def Reset(self):
        """Start a new find session."""
        log.debug("find session reset")
        # state of the find session from the last find/replace operation
        self._state = {
            "pattern": None,
            "replacement": None,
            "url": None,
            "mode": None,    # either 'replace' or 'find'
            "findSelectionStartPos": None,
            "findSelectionEndPos": None,
            "findStartPos": None,
            "patternType": None,
            "matchWord": None,
            "searchBackward": None,
            "caseSensitivity": None,
        }
        self.wrapped = 0
        self._urlsSearched = {}
        self._finds = []
        self._findsMap = {}
        self._replacements = []
        self.fileStartPos = None
        self.fileSelectionStartPos = None
        self.fileSelectionEndPos = None
        self.firstUrl = None
        self.firstFileStartPos = None
        self.firstFileSelectionStartPos = None
        self.firstFileSelectionEndPos = None


    def _UpdateState(self, **kwargs):
        """Compare the state of the given elements in the keyword arguments
        for the current find/replace operation. If there is a change then
        the find session is reset as appropriate.

        XXX One limitation of this algorithm is that no XPCOM object can
            be included in the '_state' because they cannot be compared.
            Rather the XPCOM object's attributes must be listed individually.  
        """
        changedKeys = [key for key in kwargs.keys()\
                           if self._state[key] is not None and\
                              self._state[key] != kwargs[key]]
        if len(changedKeys) > 0:
            # log the changes (for debugging)
            if log.isEnabledFor(logging.DEBUG):
                msg = "reset find session because:"
                for changedKey in changedKeys:
                    msg += " %s:'%s'->'%s'" % (changedKey,
                                               self._state[changedKey],
                                               kwargs[changedKey])
                log.debug(msg)
            # reset as appropriate
            self.Reset()
        for key in kwargs.keys():
            self._state[key] = kwargs[key]


    def NoteUrl(self, url):
        """Note that the given URL has been (or shortly will be) searched.
        XXX This is a hack because FindAll will call this where as FindNext
            will rely on calls to StartFind() to perform this step as a
            side-effect.
        """
        self._urlsSearched[url] = 1

    def StartFind(self, pattern, url, options,
                  findStartPos, findSelectionStartPos, findSelectionEndPos,
                  mode):
        """Determine if this find operation should be part of the same find
        session or if the current find session should be reset.
        """
        log.debug("start find for %r at %r in '%s' "
                  "(findSelectionStartPos=%r, findSelectionEndPos=%r, "
                  "mode=%r)", pattern,
                  findStartPos, url, findSelectionStartPos,
                  findSelectionEndPos, mode)
        self._UpdateState(pattern=pattern,
                          mode=mode,
                          url=url,
                          findStartPos=findStartPos,
                          findSelectionStartPos=findSelectionStartPos,
                          findSelectionEndPos=findSelectionEndPos,
                          patternType=options.patternType,
                          matchWord=options.matchWord,
                          searchBackward=options.searchBackward,
                          caseSensitivity=options.caseSensitivity)

        self._urlsSearched[url] = 1

        # Save data that is used to restore a buffer's state after a
        # completing searching in the current document. (This is used for
        # finding in "all open documents" and is explicitly set on document
        # swiches but must be set here for the *first* document in a find
        # session.)
        if self.fileStartPos is None:
            self.fileStartPos = findStartPos
            self.fileSelectionStartPos = findSelectionStartPos
            self.fileSelectionEndPos = findSelectionEndPos

        # Save data that is used to restore a buffer's state after a
        # completing a find session.
        if self.firstFileStartPos is None:
            self.firstUrl = url
            self.firstFileStartPos = findStartPos
            self.firstFileSelectionStartPos = findSelectionStartPos
            self.firstFileSelectionEndPos = findSelectionEndPos
            log.debug("find session started at %s in '%s'",
                      self.firstFileStartPos, self.firstUrl)


    def NoteFind(self, findResult):
        log.debug("finish find: findResult={url:'%s', value:%r, "\
                  "start:%d, end:%d}", findResult.url, findResult.value,
                  findResult.start, findResult.end)
        self._finds.append(findResult)
        self._findsMap[(findResult.url,
                        findResult.start,
                        findResult.end)] = 1
        # Adjust the cache of the state that the start of the next find
        # operation must match to remain in the same find session.
        if self._state["searchBackward"]:
            self._state["findStartPos"] = findResult.start
        else:
            self._state["findStartPos"] = findResult.end
        self._state["findSelectionStartPos"] = findResult.start
        self._state["findSelectionEndPos"] = findResult.end   #XXX should do math here n'est-ce-pas?
        self._state["url"] = findResult.url


    def StartReplace(self, pattern, replacement, url, options):
        """Determine if this replace operation should be part of the same
        find session or if the current find session should be reset.
        """
        log.debug("start replace of %r with %r in '%s'",
                  pattern, replacement, url)
        self._UpdateState(pattern=pattern,
                          replacement=replacement,
                          mode='replace',
                          url=url,
                          patternType=options.patternType,
                          matchWord=options.matchWord,
                          searchBackward=options.searchBackward,
                          caseSensitivity=options.caseSensitivity)


    def NoteReplace(self, replaceResult):
        log.debug("finish replace: replaceResult={url:'%s', value:%r, "\
                  "replacement:%r, start:%d, end:%d}",
                  replaceResult.url, replaceResult.value,
                  replaceResult.replacement,
                  replaceResult.start, replaceResult.end)
        self._replacements.append(replaceResult)
        # Adjust the cache of the state that the start of the next find
        # operation must match to remain in the same find session.
        if self._state["searchBackward"]:
            self._state["findStartPos"] = replaceResult.start
        else:
            self._state["findStartPos"] = replaceResult.start +\
                                          len(replaceResult.replacement)
        self._state["findSelectionStartPos"] = replaceResult.start
        self._state["findSelectionEndPos"] = replaceResult.start +\
                                             len(replaceResult.replacement)
        self._state["url"] = replaceResult.url
        # There is a special case where a replacement can be made before
        # any find's have been registered with the find session: when
        # the target was selected to begin with. The find should
        # manually be registered.  (Also, correct the last find in the
        # _findsMap (the delta must be used to adjust where the result
        # "end"s).
        # XXX 'delta' is not correct if the replaceResult overlaps the
        #     previous find result.
        delta = len(replaceResult.replacement) - len(replaceResult.value)
        oldhash = (replaceResult.url, replaceResult.start, replaceResult.end)
        newhash = (replaceResult.url, replaceResult.start,
                   replaceResult.end+delta)
        if len(self._finds) == 0:
            self._finds.append(replaceResult)
        else:
            del self._findsMap[oldhash]
        self._findsMap[newhash] = 1
        # The indeces for find and replace results that fall *after* the
        # position of this replacement in the same URL must have their
        # indeces updated to reflect the text change. (XXX This is only
        # currently done for self._findsMap() to assist WasAlreadyFound().
        # self._finds and self._replacements *should* also be updated.)
        for find in self._findsMap.keys():
            if find[0] == replaceResult.url and find[1] > replaceResult.start:
                log.debug("update _findsMap entry: %r -> (%s, %s, %s)",
                          find, find[0], find[1]+delta, find[2]+delta)
                self._findsMap[(find[0], find[1]+delta, find[2]+delta)] = 1
                del self._findsMap[find]

    def NoteReplaces(self, replaceResults):
        """Note a bunch of replacements in one go.

        This is called when doing "Replace All". This presumption is
        used to skip some work. For example, we don't bother updating
        self._finds and self._findsMap, so WasAlreadyFound() won't work
        for these results."""
        if not replaceResults: return

        log.debug("note replaces:")
        for rr in replaceResults:
            log.debug("\treplaceResult={url:'%s', value:%r, "\
                      "replacement:%r, start:%d, end:%d}", rr.url,
                      rr.value, rr.replacement, rr.start, rr.end)
            self._replacements.append(rr)
        # Adjust the cache of the state that the start of the next find
        # operation must match to remain in the same find session.
        if self._state["searchBackward"]:
            self._state["findStartPos"] = replaceResults[-1].start
        else:
            self._state["findStartPos"] =\
                replaceResults[-1].start + len(replaceResults[-1].replacement)
        self._state["findSelectionStartPos"] = replaceResults[-1].start
        self._state["findSelectionEndPos"] =\
            replaceResults[-1].start + len(replaceResults[-1].replacement)
        self._state["url"] = replaceResults[-1].url

    def WasAlreadyFound(self, findResult):
        retval = self._findsMap.has_key((findResult.url,
                                         findResult.start,
                                         findResult.end))
        log.debug("was this find result, {url:'%s', start:%d, end:%d}, "\
                  "already found? %s   (_findsMap=%s)",
                  findResult.url, findResult.start, findResult.end, retval,
                  self._findsMap)
        return retval

    def IsRecursiveHit(self, findResult):
        """Return true iff the given findResult overlaps a previous replace
        result, i.e. is a find hit created by a replacement.
        """
        for url, start, end in self._findsMap.keys():
            if findResult.url == url and\
               (  start < findResult.start < end
               or start < findResult.end   < end):
                retval = 1
                break
        else:
            retval = 0
        log.debug("was this find result, {url:'%s', start:%d, end:%d}, "\
                  "a recursive hit? %s   (_findsMap=%s)",
                  findResult.url, findResult.start, findResult.end, retval,
                  self._findsMap)
        return retval
    
    def HaveSearchedThisUrlAlready(self, url):
        retval = self._urlsSearched.has_key(url)
        log.debug("has URL '%s' already been search? %s (_urlsSearched=%r)",
                  url, retval, self._urlsSearched)
        return retval
    
    def GetPattern(self):
        return self._state["pattern"]

    def GetReplacement(self):
        return self._state["replacement"]

    def GetNumFinds(self):
        return len(self._finds)

    def GetNumReplacements(self):
        return len(self._replacements)

    def GetFinds(self):
        return self._finds

    def GetReplacements(self):
        return self._replacements

    def GetLastFindResult(self):
        if len(self._finds) == 0:
            return None
        else:
            return self._finds[-1]

    def GetSecondLastFindResult(self):
        # Optimization for koIFindService.replaceallex(). Not in IDL.
        if len(self._finds) < 2:
            return None
        else:
            return self._finds[-2]

