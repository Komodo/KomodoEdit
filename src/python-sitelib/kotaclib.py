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

"""Provides the base class for Komodo Textbox AutoComplete providers.

See the docs strings below for and components/koTextboxAutoComplete.py
for details and examples.
"""

import re


class KoTACSearch(object):
    """Base class for all KoTAC*Search classes.
    
    All bases classes must override:
    - all _reg_*_ and _com_interfaces_ attributes
    - startSearch() method
    
    Utility methods:
    - parseSearchParam()
    
    """
    #_com_interfaces_ = [components.interfaces.nsIAutoCompleteSearch]
    #_reg_clsid_ = "{<guid>}"
    #_reg_contractid_ = "@mozilla.org/autocomplete/search;1?name=<name>"
    #_reg_desc_ = "<desc>"

    def startSearch(self, searchString, searchParam, previousResult, listener):
        """Synchronously or asynchronously search for the given search string.

            searchString (str)
            searchParam (str)
            previousResult (nsIAutoCompleteResult)
            listener (nsIAutoCompleteObserver)

        The result of the search should be reported via the "listener":
            void onSearchResult(in nsIAutoCompleteSearch search, in nsIAutoCompleteResult result);

        AutoComplete search best practices:
        - If possible limit the search to just the set in
          "previousResult". I.e. if the last search was for "fo" and
          this one is for "foo", then searching within the previous
          result might be faster. If so, then don't need to create a new
          nsIAutoCompleteResult: just pare down the "previousResult" and
          pass it back.
        """
        raise NotImplementedError("virtual base method")
    
    def stopSearch(self):
        """This is sent by the autocomplete controller to stop a
        possible previous asynchronous search.
        """
        pass

    search_param_pats = [
        # Matches un-quoted params.
        re.compile(r'''(?P<key>[\w-]+):\s*()(?P<name>[^'";]+)\s*;?'''),
        # Matches quoted params.
        re.compile(r'''(?P<key>[\w-]+):\s*(['"])(?P<name>.*?)(?<!\\)\2\s*;?'''),
    ]
    def parseSearchParam(self, searchParam):
        """Parse the given CSS-like search parameter (i.e. the value of
        the 'autocompletesearchparam' attribute of the <textbox> element).
        
        To support more than one piece of data, some TAC searches use a
        CSS-like search param.
        
            >>> parseSearchParam("foo: bar")
            {'foo': 'bar'}
            >>> parseSearchParam("foo-bar: baz qxz; batman: 'pif pow'")
            {'batman': 'pif pow', 'foo-bar': 'baz qxz'}
            >>> parseSearchParam(r'''robin: 'holy \\'cow\\''; batman: 'pif "pow"';''')
            {'batman': 'pif "pow"', 'robin': "holy 'cow'"}
        
        Returns a dict of name/value pairs.
        """
        data = {}
        for search_param_pat in self.search_param_pats:
            for name, quote, value in search_param_pat.findall(searchParam):
                data[name] = _unescape_quotes(value)
        return data


class KoTACMatch(object):
    """A class representing a single textbox autocomplete hit/match.

    These are used by a koIAutoCompleteResult like this:

        result = components.classes["@activestate.com/autocomplete/result;1"] \
            .createInstance(components.interfaces.koIAutoCompleteResult)
        result.init(<search-string>)
        for hit in <find-hits>:
            result.addMatch(KoTACMatch(...))

    See `KoTACResult` docstring (in "koTextboxAutoComplete.py") for details.
    """
    #_com_interfaces_ = [components.interfaces.koIAutoCompleteMatch]
    #TODO: remove these if not necessary
    #_reg_clsid_ = "{5AEEBCBF-6C23-4765-9113-2B3C6D52D44E}"
    #_reg_contractid_ = "@activestate.com/autocomplete/match;1"
    #_reg_desc_ = "Komodo textbox autocomplete search match"

    value = None
    comment = None
    style = None
    isDefault = False
    image = None

    def __init__(self, value=None, comment=None, style=None, isDefault=False, image=None):
        self.value = value
        self.comment = comment
        self.style = style
        self.isDefault = isDefault
        self.image = image



#---- internal support routines

def _unescape_quotes(s):
    return s.replace("\\'", "'").replace('\\"', '"')

