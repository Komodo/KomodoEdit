#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

import os
import sys
import urllib
import htmllib
import textwrap
from os.path import exists, join
from pprint import pprint, pformat
from optparse import OptionParser
from hashlib import md5

from BeautifulSoup import BeautifulSoup, NavigableString

def unescape(s):
    p = htmllib.HTMLParser(None)
    p.save_bgn()
    p.feed(s)
    return p.save_end()

def getHtmlForUrl(url):
    urlhash = md5(url).hexdigest()
    cache_filename = join(".cache", urlhash)
    if exists(cache_filename):
        return file(cache_filename).read()
    urlOpener = urllib.urlopen(url)
    content = urlOpener.read()
    file(cache_filename, "wb").write(content)
    return content

def getText(elem):
    l = []
    for element in elem:
        #if isinstance(element, NavigableString):
        #    continue
        if element.string:
            l.append(element.string)
        else:
            l.append(getText(element))
    text = " ".join(l)
    try:
        return unescape(text)
    except:
        return text

def getNextSibling(tag):
    sibling = tag.nextSibling
    while sibling and isinstance(sibling, NavigableString):
        sibling = sibling.nextSibling
    return sibling

def parseVersion(tag):
    for child_tag in tag.parent('tr'):
        text = getText(child_tag).strip()
        if not text:
            continue
        if 'Firefox' in text:
            return text

def parseValues(tag):
    values = {}
    for child_tag in tag.parent('dt'):
        text = getText(child_tag).strip()
        if not text:
            continue
        split = text.split(None, 1)
        attribute = unescape(split[0].replace("&nbsp;", " "))
        if not attribute:
            continue
        description = ''
        if len(split) > 1:
            description = split[1] + ". "
        sibling = getNextSibling(child_tag)
        if sibling is not None and sibling.name == 'dd':
            description += getText(sibling)
        values[attribute] = description
    return values

def parseProperty(property_name, property_details):
    url = "https://developer.mozilla.org/en/CSS/%s" % (property_name, )
    data = getHtmlForUrl(url)
    if "Welcome to the Mozilla Developer Network" in data:
        # Page did not exist, was re-directed to the main page.
        return
    try:
        soup = BeautifulSoup(data)
    except:
        print "Unable to pass HTML for property: %r" % (property_name, )
        return
        
    tags = soup.html.body("h3", {'class': "editable"})
    foundData = False
    for tag in tags:
        if not tag.string:
            continue
        string = tag.string.strip()
        if string == "Summary":
            property_details["description"] = getText(getNextSibling(tag)).strip()
            foundData = True
        elif string == "Values":
            property_details["values"] = parseValues(getNextSibling(tag))
            foundData = True
        elif string == "Browser compatibility":
            version = parseVersion(getNextSibling(tag))
            if version:
                property_details["version"] = version
    if not foundData:
        # Alternative syntax.
        tag = soup.html.body.find("div", {'id': "pageText"})
        desc = getText(tag.p)
        if "Obsolete" in desc:
            split = desc.split("Obsolete", 1)
            if len(split) == 2 and split[1].strip():
                desc = split[1].strip()
            else:
                desc = getText(list(tag.parent.findAll('p'))[2])
            desc = "(OBSOLETE) %s" % (desc, )
        property_details["description"] = desc.strip()
        property_details["values"] = parseValues(tag.p)
            

    # Fix ups.
    version = property_details.get("version")
    if version is not None and " -" in version:
        property_details["version"] = version.split(" -")[0].strip()
        
    if property_name == '-moz-background-origin':
        values = property_details["values"]
        for value, desc in values.items():
            split = desc.split("New in Firefox 4")
            if len(split) > 1:
                alt_value, alt_desc = split[1].split(None, 1)
                values[alt_value] = alt_desc
                values[value] = "(New in Firefox 4). %s" % (alt_desc.split(". ", 1)[1], )
    elif property_name == '-moz-background-clip':
        values = property_details["values"]
        for value, desc in values.items():
            split = desc.split("Requires Gecko 1.9.3 ")
            if len(split) > 1:
                alt_value, alt_desc = split[1].split(None, 1)
                values[alt_value] = alt_desc
                values[value] = "(Requires Gecko 1.9.3). %s" % (alt_desc.split(". ", 1)[1], )
    elif property_name == '-moz-box-flex':
        values = property_details["values"]
        values.pop(">", None)

def processProperty(property_name, properties):
    property_details = {}
    properties[property_name] = property_details
    print property_name
    parseProperty(property_name, property_details)

# Soup parsing of API documentation from webpage
def main(filename):
    moz_properties = [
        "-moz-appearance",
        "-moz-background-clip",
        "-moz-background-inline-policy",
        "-moz-background-origin",
        "-moz-background-size",
        "-moz-binding",
        "-moz-border-bottom-colors",
        "-moz-border-left-colors",
        "-moz-border-right-colors",
        "-moz-border-top-colors",
        "-moz-border-end",
        "-moz-border-end-color",
        "-moz-border-end-style",
        "-moz-border-end-width",
        "-moz-border-image",
        "-moz-border-radius",
        "-moz-border-radius-bottomleft",
        "-moz-border-radius-bottomright",
        "-moz-border-radius-topleft",
        "-moz-border-radius-topright",
        "-moz-border-start",
        "-moz-border-start-color",
        "-moz-border-start-style",
        "-moz-border-start-width",
        "-moz-box-align",
        "-moz-box-direction",
        "-moz-box-flex",
        "-moz-box-flexgroup",
        "-moz-box-ordinal-group",
        "-moz-box-orient",
        "-moz-box-pack",
        "-moz-box-shadow",
        "-moz-box-sizing",
        "-moz-column-count",
        "-moz-column-gap",
        "-moz-column-width",
        "-moz-column-rule",
        "-moz-column-rule-width",
        "-moz-column-rule-style",
        "-moz-column-rule-color",
        "-moz-float-edge",
        "-moz-force-broken-image-icon",
        "-moz-image-region",
        "-moz-margin-end",
        "-moz-margin-start",
        "-moz-opacity",
        "-moz-outline",
        "-moz-outline-color",
        "-moz-outline-offset",
        "-moz-outline-radius",
        "-moz-outline-radius-bottomleft",
        "-moz-outline-radius-bottomright",
        "-moz-outline-radius-topleft",
        "-moz-outline-radius-topright",
        "-moz-outline-style",
        "-moz-outline-width",
        "-moz-padding-end",
        "-moz-padding-start",
        "-moz-stack-sizing",
        "-moz-transform",
        "-moz-transform-origin",
        "-moz-transition",
        "-moz-transition-delay",
        "-moz-transition-duration",
        "-moz-transition-property",
        "-moz-transition-timing-function",
        "-moz-user-focus",
        "-moz-user-input",
        "-moz-user-modify",
        "-moz-user-select",
        "-moz-window-shadow",
    ]

    properties = {}
    for property_name in moz_properties:
        processProperty(property_name, properties)

    # Write out the properties.
    
    f = file(filename, "w")

    f.write("CSS_MOZ_DATA = {\n")
    for property_name in sorted(properties):
        data = properties.get(property_name)
        #values = sorted(data.get("values", {}).keys())
        #values = [x for x in values if not x.startswith("<")]
        f.write("""
    %r:\n%s,
""" % (str(property_name), pformat(data, indent=8)))
    f.write("}\n")

    f.close()

if __name__ == '__main__':
    filename = "moz_properties.py"
    main(filename)
