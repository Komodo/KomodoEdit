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

"""Scrape CSS property definitions from the w3 web site."""

from codeintel2.util import CompareNPunctLast
#
# Used to generate a part of lib/codeintel/css_constants.py
#
# CSS defs come from w3 at: http://www.w3.org/TR/REC-CSS2/propidx.html
#
# Prints the CSS_ATTR_DICT used in css_constants.py
#
# Requires: BeautifulSoup
#           http://www.crummy.com/software/BeautifulSoup/
#
# Note: The calltips for the CSS properties were done by hand, as scraping
#       seemed to be out of the question from this website.
#

import string
import urllib
from pprint import pprint
import xml.sax.saxutils
from BeautifulSoup import BeautifulSoup, NavigableString

def getCSSFromWebpage():
    #urlOpener = urllib.urlopen("http://www.python.org")
    urlOpener = urllib.urlopen("http://www.w3.org/TR/REC-CSS2/propidx.html")
    data = urlOpener.read()
    #print "Read in %d bytes" % (len(data))
    return data

_isident_chars = string.ascii_lowercase + string.digits + "_" + "-"
_isident_dict = {}
for c in _isident_chars:
    _isident_dict[c] = 1

def _isident(char):
    return _isident_dict.get(char, 0)

def _isIdentifierString(s):
    for c in s:
        if not _isident(c):
            #print "Not _isIdentifierString: %s" % (s)
            return False
    return True

def _isLookupIdentifierString(s):
    if s[0] != '<' or s[-1] != '>':
        return False
    for c in s[1:-1]:
        if not _isident(c):
            #print "Not _isLookupIdentifierString: %s" % (s)
            return False
    return True

def cleanupIdentifiers(s):
    s = xml.sax.saxutils.unescape(s)
    s = s.replace("'", " ")
    s = s.replace("[", " ")
    s = s.replace("]", " ")
    # Remove all { ... }
    while 1:
        posStart = s.find("{")
        posEnd = s.find("}")
        if posStart < 0 or posEnd < 0:
            break
        s = s[:posStart] + s[posEnd+1:]
    s = s.replace("|", " ")
    return s

special_attribute_lookups = {
    'angle'         : [ ],
    'absolute-size' : [ 'xx-small', 'x-small', 'small', 'medium', 'large', 'x-large', 'xx-large' ],
    'border-width'  : [ 'thin', 'thick', 'medium' ],
    'border-style'  : [ 'none', 'hidden', 'dotted', 'dashed', 'solid', 'double', 'groove', 'ridge', 'inset', 'outset' ],
    'color'         : [ '#', 'rgb(' ],
    'counter'       : [ 'counter(' ],
    'family-name'   : [ ],
    'frequency'     : [ 'Hz', 'kHz' ],
    'generic-family': [ 'serif', 'sans-serif', 'cursive', 'fantasy', 'monospace' ],
    'generic-voice' : [ 'male', 'female', 'child' ],
    'identifier'    : [ ],
    'inherit'       : [ 'inherit', '!important' ],
    'integer'       : [ ],
    'length'        : [ ],
    'margin-width'  : [ 'auto' ],
    'number'        : [ ],
    'padding-width' : [ ],
    'percentage'    : [ ],
    'relative-size' : [ 'larger', 'smaller' ],
    'shape'         : [ 'rect(' ],
    'specific-voice': [ ],
    'string'        : [ '""', "''" ],
    'time'          : [ 'ms', 's' ],
    'uri'           : [ 'url(' ],
}

def lookup_all_attrs(name, result_dict, lookup_dict, seenSoFar=None):
    if name in seenSoFar:
        return []
    seenSoFar.append(name)
    if _isLookupIdentifierString(name):
        name = name[1:-1]
    attrs = None
    if name in special_attribute_lookups:
        attrs = special_attribute_lookups[name]
    if attrs != None:
        attrs += result_dict.get(name, [])
    else:
        attrs = result_dict.get(name)
    if attrs == None:
        print "WARNING: No attributes found for: %s" % (name)
        return []
    attrs = set(attrs)
    lookup_ids = lookup_dict.get(name, [])
    for id in lookup_ids:
        if id[1:-1] == name:
            if name not in special_attribute_lookups:
                print "WARNING: Lookup id same as name: '%s', but no matching special_attribute_lookups" % id
        if id not in seenSoFar:
            attrs.update(lookup_all_attrs(id, result_dict, lookup_dict, seenSoFar))
    return list(attrs)

def processTrTags(soup, taglist):
    printlist = [ "CSS_ATTR_DICT = {" ]
    result = {  }
    lookups = {}
    for tag in taglist:
        #print "Tag: %s" % tag
        #print "Span: %s" % tag.span
        #print "Td: %s" % tag.findAll('td')[1]
        #print
        names = [ cleanupIdentifiers(x.string).strip() for x in tag.td.findAll('span')]
        #name_links = tag.td.findAll('a')
        #print name_links
        values = []
        for item in tag.findAll('td')[1]:
            #if hasattr(item, 'name'): print "item.name:", item.name
            if isinstance(item, NavigableString):
                #print "anchor:", item.string
                idents = cleanupIdentifiers(item.string)
                #print "idents:", idents
                for sp in [ s.strip() for s in idents.split(" ") ]:
                    v = [ s for s in sp.split() if _isIdentifierString(s) ]
                    for id in v:
                        if id not in values:
                            values.append(id)
            else:
                #print "item.span", item.span
                id = cleanupIdentifiers(item.span.string).strip()
                #print id
                lookup_id = id
                for name in names:
                    l = lookups.get(name)
                    if not l:
                        lookups[name] = [lookup_id]
                    else:
                        l.append(lookup_id)
                #if _isIdentifierString(id) and id not in values:
                #    values.append(id)
            #if names[0] == "background-attachment":
            #    print "Background"
            #    print tag
            #    print item
            #    if isinstance(item, NavigableString):
            #        print "NavigableString"
            #        print item.string
            #    return
        values.sort(CompareNPunctLast)
        for name in names:
            result[name] = values

    #pprint(lookups)
    names = result.keys()
    names.sort()
    for name in names:
        printvalues = []
        values = lookup_all_attrs(name, result, lookups, seenSoFar=[])
        values.sort(CompareNPunctLast)
        for v in values:
            val = v
            if val[0] not in ("'", '"'):
                val = "'%s" % val
            if val[-1] not in ("'", '"'):
                val += "'"
            printvalues.append("            %s," % (val))
        printlist.append("    %-12s: [" % ("'%s'" % name))
        printlist += printvalues
        printlist.append("        ],")
    printlist.append("}")

    #printlist.append("")
    #printlist.append("")
    #printlist.append("CSS_ATTR_CALLTIPS_DICT = {")
    #for name in names:
    #    printlist.append('    %-18s: """ """,' % ("'%s'" % name))
    #printlist.append("}")

    print "\n".join(printlist)

# Soup parsing of CSS properties
def main():
    data = getCSSFromWebpage()
    soup = BeautifulSoup(data)
    tr_tags = soup.findAll('tr')
    processTrTags(soup, tr_tags[1:])

if __name__ == '__main__':
    main()
