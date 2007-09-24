#!/usr/bin/env python
# Copyright (c) 2005-2007 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

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



#---- internal support routines

def _unescape_quotes(s):
    return s.replace("\\'", "'").replace('\\"', '"')
