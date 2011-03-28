#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

"""Generates a file containing the list of WebKit CSS properties.

Uses the web pages found here:
  http://css-infos.net/properties/webkit.php
"""

import re
import urllib
import htmlentitydefs
from os.path import exists, join
from pprint import pprint, pformat
from hashlib import md5

from BeautifulSoup import BeautifulSoup, NavigableString

def unescape(text):
    """Removes HTML or XML character references 
       and entities from a text string.
    from Fredrik Lundh
    http://effbot.org/zone/re-sub.htm#unescape-html
    """
    text = text.replace("\r\n", "\n")
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                print "erreur de valeur"
                pass
        else:
           # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                print "keyerror"
                pass
        return text # leave as is
    text = re.sub("&#?\w+;", fixup, text)
    # Reduce multiple spaces.
    text = re.sub(r"\s(\s)+", " ", text)
    return text

def getNextTagWithName(tag, name):
    tag = tag.nextSibling
    while tag:
        if not isinstance(tag, NavigableString):
            if tag.name == name:
                return tag
        tag = tag.nextSibling

def getText(elem):
    l = []
    for element in elem:
        #if isinstance(element, NavigableString):
        #    continue
        if element.string:
            l.append(element.string)
        else:
            l.append(getText(element))
    return unescape(" ".join(l))

def getTextStoppingAtTag(tag, name):
    l = []
    for element in tag:
        if not isinstance(element, NavigableString) and tag.name == name:
            break
        if element.string:
            l.append(element.string)
        else:
            l.append(getTextStoppingAtTag(element, name))
    return unescape(" ".join(l))

def getNextSibling(tag):
    sibling = tag.nextSibling
    while sibling and isinstance(sibling, NavigableString):
        sibling = sibling.nextSibling
    return sibling

def getHtmlForUrl(url):
    urlhash = md5(url).hexdigest()
    #print 'urlhash: %r' % (urlhash, )
    cache_filename = join(".cache", urlhash)
    if exists(cache_filename):
        return file(cache_filename).read()
    urlOpener = urllib.urlopen(url)
    content = urlOpener.read()
    file(cache_filename, "wb").write(content)
    return content

def parseParameters(tag):
    values = {}
    for child_tag in tag('dt'):
        value = getText(child_tag)
        dd_tag = getNextSibling(child_tag)
        description = getText(dd_tag.p or dd_tag)
        values[value] = description
    return values

def parseValues(tag):
    values = {}
    for child_tag in tag.tbody('tr'):
        text = getText(child_tag)
        split = text.split(None, 1)
        attribute = split[0]
        if len(split) > 1:
            values[attribute] = split[1]
        else:
            values[attribute] = ''
    return values

def parseVersions(tag):
    versions = []
    for child_tag in tag('li'):
        text = getText(child_tag)
        versions.append(text)
    return versions

def parseProperty(property_name):
    property_details = {}
    url = "http://css-infos.net/property/%s" % (property_name, )
    data = getHtmlForUrl(url)
    try:
        soup = BeautifulSoup(data)
    except:
        print "Unable to pass HTML for property: %r" % (property_name, )
        return property_details
        
    tags = soup.html.body("h2")
    for tag in tags:
        if tag.string == "Description":
            property_details["description"] = getText(getNextSibling(tag))
        elif tag.string == "Syntax":
            property_details["syntax"] = getText(getNextSibling(tag))
        elif tag.string == "Parameters":
            property_details["values"] = parseParameters(getNextSibling(tag))
        elif tag.string == "Values":
            property_details["values"] = parseValues(getNextSibling(tag))
        elif tag.string == "Versions":
            property_details["versions"] = parseVersions(getNextSibling(tag))
    return property_details

def parseWebKitProperties():
    properties = {}
    url = 'http://css-infos.net/properties/webkit.php'
    data = getHtmlForUrl(url)
    try:
        soup = BeautifulSoup(data)
    except:
        print "Unable to obtain HTML for url: %r" % (url, )
        return

    tags = soup.html.body.table.tbody.findAll('td', {'class': 'element'})
    for tag in tags:
        property_name = getText(tag)
        print(property_name)
        property_details = parseProperty(property_name)
        properties[property_name] = property_details

    return properties

# Soup parsing of API documentation from webpage
def main(filename):
    properties = parseWebKitProperties()

    # Write out the properties.
    
    f = file(filename, "w")

    f.write("CSS_WEBKIT_DATA = {\n")
    for property_name in sorted(properties):
        data = properties.get(property_name)
        f.write("""
    %r:\n%s,
""" % (str(property_name), pformat(data, indent=8)))
    f.write("}\n")

    f.close()

if __name__ == '__main__':
    filename = "webkit_properties.py"
    main(filename)
