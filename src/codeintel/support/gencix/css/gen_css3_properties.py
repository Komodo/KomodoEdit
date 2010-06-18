#!/usr/bin/env python
# Copyright (c) 2010 ActiveState Software Inc.
# See LICENSE.txt for license details.
#
# Contributers (aka Blame):
#  - Todd Whiteman
#

import os
import sys
import re
import urllib
import htmllib
import textwrap
import htmlentitydefs
from os.path import exists, join
from pprint import pprint, pformat
from optparse import OptionParser
from hashlib import md5

from BeautifulSoup import BeautifulSoup, NavigableString

def unescape(text):
    """Removes HTML or XML character references 
       and entities from a text string.
    from Fredrik Lundh
    http://effbot.org/zone/re-sub.htm#unescape-html
    """
    text = text.replace("\r\n", "\n")
    text = text.replace("&nbsp;", " ")
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
    text = text.strip()
    # Remove some other non ascii characters.
    text = text.replace("\xa0".decode("iso_8859-1"), " ")
    text = text.replace("\xab".decode("iso_8859-1"), "<")
    text = text.replace("\xac".decode("iso_8859-1"), "!") # not sign
    text = text.replace("\xad".decode("iso_8859-1"), "") # soft hyphen
    text = text.replace("\xb0".decode("iso_8859-1"), "") # degree symbol
    text = text.replace("\xbb".decode("iso_8859-1"), ">")
    text = text.replace(u'\u2014', "-") # mdash
    text = text.replace(u'\u2018', "'")
    text = text.replace(u'\u2019', "'")
    text = text.replace(u'\u201c', "\"") # left double quotation mark
    text = text.replace(u'\u201d', "\"") # right double quotation mark
    text = text.replace(u'\u2026', "...") # horizontal ellipsis
    text = text.replace(u'\u2208', "?")
    text = text.replace(u'\u2260', "!=")
    text = text.replace(u'\u2264', "<=")
    text = text.replace(u'\u2265', ">=")
    text = text.encode('ascii', 'replace')
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

def parseExtraValuesFromDl(dl_tag, values):
    value = None
    for tag in dl_tag:
        if isinstance(tag, NavigableString):
            continue
        if tag.name == 'dt':
            value = getText(tag).strip()
        elif value and tag.name == 'dd':
            description = ''
            split = value.split('(', 1)
            if len(split) == 1:
                split = value.split(None, 1)
            if len(split) > 1:
                description = value + ". "
                value = split[0]
            value = unescape(value)
            value = value.strip("'")
            description += getText(tag)
            values[value] = description
            value = None

def parseExtraData(property_name, properties, page_info):
    print "%r" % (property_name, )
    data = getHtmlForUrl(page_info[0])
    try:
        soup = BeautifulSoup(data)
    except:
        print "Unable to pass HTML for property: %r" % (property_name, )
        return
        
    property_details = {}
    properties[property_name] = property_details

    tag = soup.html.body.find(True, {'id': page_info[1]})
    if not tag:
        print "Unable to find HTML element with id: %r" % (page_info[1], )
        return

    description = ''
    values = {}
    while tag:
        tag = tag.next
        if not tag:
            break
        if isinstance(tag, NavigableString):
            continue
        if tag.name == 'p':
            description += getTextStoppingAtTag(tag, 'dl')
        elif tag.name == 'dl':
            parseExtraValuesFromDl(tag, values)
            break
        elif tag.name in ('h1', 'h2', 'h3'):
            break
    property_details["description"] = description
    property_details['values'] = values


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


css3_property_details = {
    'alignment-adjust': {
        'url':      'http://www.w3.org/TR/css3-linebox/#alignment-adjust',
    },
    'alignment-baseline': {
        'url':      'http://www.w3.org/TR/css3-linebox/#alignment-baseline',
    },
    'animation': {
        'url':      'http://www.w3.org/TR/css3-animations/#the-animation-shorthand-property-',
    },
    'animation-delay': {
        'url':      'http://www.w3.org/TR/css3-animations/#the-animation-delay-property-',
    },
    'animation-direction': {
        'url':      'http://www.w3.org/TR/css3-animations/#the-animation-direction-property-',
    },
    'animation-duration': {
        'url':      'http://www.w3.org/TR/css3-animations/#the-animation-duration-property-',
    },
    'animation-iteration-count': {
        'url':      'http://www.w3.org/TR/css3-animations/#the-animation-iteration-count-property-',
    },
    'animation-name': {
        'url':      'http://www.w3.org/TR/css3-animations/#the-animation-name-property-',
    },
    'animation-play-state': {
        'url':      'http://www.w3.org/TR/css3-animations/#the-animation-play-state-property-',
    },
    'animation-timing-function': {
        'url':      'http://www.w3.org/TR/css3-animations/#animation-timing-function_tag',
    },
    'appearance': {
        'url':      'http://www.w3.org/TR/css3-ui/#appearance0',
    },
    # Missing?
    #'background-break': {
    #    'url':      'http://www.w3.org/TR/css3-background/#the-background-break',
    #},
    'background-clip': {
        'url':      'http://www.w3.org/TR/css3-background/#the-background-clip',
    },
    'background-origin': {
        'url':      'http://www.w3.org/TR/css3-background/#the-background-origin',
    },
    'background-size': {
        'url':      'http://www.w3.org/TR/css3-background/#the-background-size',
    },
    'baseline-shift': {
        'url':      'http://www.w3.org/TR/css3-linebox/#baseline-shift-prop',
    },
    'binding': {
        'url':      'http://www.w3.org/TR/becss/#the-binding',
    },
    'break-after': {
        'url':      'http://www.w3.org/TR/css3-multicol/#break-after',
    },
    'break-before': {
        'url':      'http://www.w3.org/TR/css3-multicol/#break-before',
    },
    'break-inside': {
        'url':      'http://www.w3.org/TR/css3-multicol/#break-before',
    },
    'bookmark-label': {
        'url':      'http://www.w3.org/TR/css3-gcpm/#bookmark-label',
    },
    'bookmark-level': {
        'url':      'http://www.w3.org/TR/css3-gcpm/#bookmark-level',
    },
    'bookmark-target': {
        'url':      'http://www.w3.org/TR/css3-gcpm/#bookmark-target',
    },
    'border-bottom-left-radius': {
        'url':      'http://www.w3.org/TR/css3-background/#the-border-radius',
    },
    'border-bottom-right-radius': {
        'url':      'http://www.w3.org/TR/css3-background/#the-border-radius',
    },
    'border-image': {
        'url':      'http://www.w3.org/TR/css3-background/#the-border-image',
    },
    # Missing?
    #'border-length': {
    #    'url':      'http://www.w3.org/TR/css3-gcpm/#border-length',
    #},
    'border-radius': {
        'url':      'http://www.w3.org/TR/css3-background/#the-border-radius',
    },
    'border-top-left-radius': {
        'url':      'http://www.w3.org/TR/css3-background/#the-border-radius',
    },
    'border-top-right-radius': {
        'url':      'http://www.w3.org/TR/css3-background/#the-border-radius',
    },
    'box-align': {
        'url':      'http://www.w3.org/TR/css3-flexbox/#propdef-box-align',
    },
    'box-decoration-break': {
        'url':      'http://www.w3.org/TR/css3-background/#the-box-decoration-break',
    },
    'box-direction': {
        'url':      'http://www.w3.org/TR/css3-flexbox/#propdef-box-direction',
    },
    'box-flex': {
        'url':      'http://www.w3.org/TR/css3-flexbox/#propdef-box-flex',
    },
    'box-flex-group': {
        'url':      'http://www.w3.org/TR/css3-flexbox/#propdef-box-flex-group',
    },
    'box-lines': {
        'url':      'http://www.w3.org/TR/css3-flexbox/#propdef-box-lines',
    },
    'box-ordinal-group': {
        'url':      'http://www.w3.org/TR/css3-flexbox/#propdef-box-ordinal-group',
    },
    'box-orient': {
        'url':      'http://www.w3.org/TR/css3-flexbox/#propdef-box-orient',
    },
    'box-pack': {
        'url':      'http://www.w3.org/TR/css3-flexbox/#propdef-box-pack',
    },
    'box-shadow': {
        'url':      'http://www.w3.org/TR/css3-background/#the-box-shadow',
    },
    'box-sizing': {
        'url':      'http://www.w3.org/TR/css3-ui/#box-sizing0',
    },
    'color-profile': {
        'url':      'http://www.w3.org/TR/2003/CR-css3-color-20030514/#icc-color',
    },
    'column-count': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-count',
    },
    'column-fill': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-fill',
    },
    'column-gap': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-gap',
    },
    'column-rule': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-rule',
    },
    'column-rule-color': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-rule-color',
    },
    'column-rule-style': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-rule-style',
    },
    'column-rule-width': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-rule-width',
    },
    'column-span': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-span',
    },
    'column-width': {
        'url':      'http://www.w3.org/TR/css3-multicol/#column-width',
    },
    'columns': {
        'url':      'http://www.w3.org/TR/css3-multicol/#columns',
    },
    'crop': {
        'url':      'http://www.w3.org/TR/css3-content/#the-crop',
    },
    #'display-model': {
    #    'url':      'http://www.w3.org/TR/css3-layout/#tabbed',
    #},
    #'display-role': {
    #    'url':      'http://www.w3.org/TR/css3-layout/#tabbed',
    #},
    'dominant-baseline': {
        'url':      'http://www.w3.org/TR/css3-linebox/#dominant-baseline',
    },
    'drop-initial-before-adjust': {
        'url':      'http://www.w3.org/TR/css3-linebox/#drop-initial-before-adjust',
    },
    'drop-initial-after-adjust': {
        'url':      'http://www.w3.org/TR/css3-linebox/#drop-initial-after-adjust',
    },
    'drop-initial-before-align': {
        'url':      'http://www.w3.org/TR/css3-linebox/#drop-initial-before-align',
    },
    'drop-initial-after-align': {
        'url':      'http://www.w3.org/TR/css3-linebox/#drop-initial-after-align',
    },
    'drop-initial-size': {
        'url':      'http://www.w3.org/TR/css3-linebox/#drop-initial-size',
    },
    'drop-initial-value': {
        'url':      'http://www.w3.org/TR/css3-linebox/#drop-initial-value',
    },
    'fit': {
        'url': 'http://www.w3.org/TR/css3-page/#fit',
    },
    'fit-position': {
        'url': 'http://www.w3.org/TR/css3-page/#fit-position',
    },
    'float-offset': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#float-offset',
    },
    'font-size-adjust': {
        'url': 'http://www.w3.org/TR/css3-fonts/#font-size-adjust',
    },
    'font-stretch': {
        'url': 'http://www.w3.org/TR/css3-fonts/#font-stretch',
    },
    'grid-columns': {
        'url': 'http://www.w3.org/TR/css3-grid/#grid-columns',
    },
    'grid-rows': {
        'url': 'http://www.w3.org/TR/css3-grid/#grid-rows',
    },
    'hanging-punctuation': {
        'url': 'http://www.w3.org/TR/css3-text/#hanging-punctuation',
    },
    'hyphenate-after': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#hyphenate-after',
    },
    'hyphenate-before': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#hyphenate-before',
    },
    'hyphenate-character': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#hyphenate-character',
    },
    'hyphenate-lines': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#hyphenate-lines',
    },
    'hyphenate-resource': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#hyphenate-resource',
    },
    'hyphens': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#hyphens',
    },
    'icon': {
        'url': 'http://www.w3.org/TR/css3-ui/#icon',
    },
    'image-orientation': {
        'url': 'http://www.w3.org/TR/css3-page/#image-orientation',
    },
    'image-resolution': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#image-resolution',
    },
    'inline-box-align': {
        'url': 'http://www.w3.org/TR/css3-linebox/#inline-box-align',
    },
    'line-stacking': {
        'url': 'http://www.w3.org/TR/css3-linebox/#line-stacking',
    },
    'line-stacking-ruby': {
        'url': 'http://www.w3.org/TR/css3-linebox/#line-stacking-ruby',
    },
    'line-stacking-shift': {
        'url': 'http://www.w3.org/TR/css3-linebox/#line-stacking-shift',
    },
    'line-stacking-strategy': {
        'url': 'http://www.w3.org/TR/css3-linebox/#line-stacking-strategy',
    },
    'mark': {
        'url': 'http://www.w3.org/TR/css3-speech/#mark',
    },
    'mark-after': {
        'url': 'http://www.w3.org/TR/css3-speech/#mark-after',
    },
    'mark-before': {
        'url': 'http://www.w3.org/TR/css3-speech/#mark-before',
    },
    'marquee-direction': {
        'url': 'http://www.w3.org/TR/css3-marquee/#the-marquee-direction',
    },
    'marquee-play-count': {
        'url': 'http://www.w3.org/TR/css3-marquee/#the-marquee-play-count',
    },
    'marquee-speed': {
        'url': 'http://www.w3.org/TR/css3-marquee/#the-marquee-speed',
    },
    'marquee-style': {
        'url': 'http://www.w3.org/TR/css3-marquee/#the-marquee-style',
    },
    'move-to': {
        'url': 'http://www.w3.org/TR/css3-content/#moving',
    },
    'nav-down': {
        'url': u'http://www.w3.org/TR/css3-ui/#nav-down',
    },
    'nav-index': {
        'url': u'http://www.w3.org/TR/css3-ui/#nav-index',
    },
    'nav-left': {
        'url': u'http://www.w3.org/TR/css3-ui/#nav-left',
    },
    'nav-right': {
        'url': u'http://www.w3.org/TR/css3-ui/#nav-right',
    },
    'nav-up': {
        'url': 'http://www.w3.org/TR/css3-ui/#nav-up',
    },
    'opacity': {
        'url': 'http://www.w3.org/TR/css3-color/#opacity',
    },
    'outline-offset': {
        'url': 'http://www.w3.org/TR/css3-ui/#outline-offset0',
    },
    'overflow-style': {
        'url': 'http://www.w3.org/TR/css3-marquee/#the-overflow-style',
    },
    'overflow-x': {
        'url': 'http://www.w3.org/TR/css3-box/#overflow-x',
    },
    'overflow-y': {
        'url': 'http://www.w3.org/TR/css3-box/#overflow-y',
    },
    'page-policy': {
        'url': 'http://www.w3.org/TR/css3-content/#page-policy',
    },
    'phonemes': {
        'url': 'http://www.w3.org/TR/css3-speech/#phonemes',
    },
    'presentation-level': {
        'url': 'http://www.w3.org/TR/css3-preslev/#presentation-level-property',
    },
    'punctuation-trim': {
        'url': 'http://www.w3.org/TR/css3-text/#punctuation-trim',
    },
    'rendering-intent': {
        'url': 'http://www.w3.org/TR/2003/CR-css3-color-20030514/#renderingintent',
    },
    'resize': {
        'url': 'http://www.w3.org/TR/css3-ui/#resize0',
    },
    'rest': {
        'url': 'http://www.w3.org/TR/css3-speech/#rest',
    },
    'rest-after': {
        'url': 'http://www.w3.org/TR/css3-speech/#rest-after',
    },
    'rest-before': {
        'url': 'http://www.w3.org/TR/css3-speech/#rest-before',
    },
    'rotation': {
        'url': 'http://www.w3.org/TR/css3-box/#rotating',
    },
    'rotation-point': {
        'url': 'http://www.w3.org/TR/css3-box/#rotating',
    },
    'ruby-align': {
        'url': 'http://www.w3.org/TR/css3-ruby/#ruby-align',
    },
    'ruby-overhang': {
        'url': 'http://www.w3.org/TR/css3-ruby/#ruby-overhang',
    },
    'ruby-position': {
        'url': 'http://www.w3.org/TR/css3-ruby/#ruby-position',
    },
    'ruby-span': {
        'url': 'http://www.w3.org/TR/css3-ruby/#ruby-span',
    },
    'string-set': {
        'url': 'http://www.w3.org/TR/css3-gcpm/#string-set',
    },
    # Doesn't exist?
    #'tab-side': {
    #    'url': 'http://www.w3.org/TR/css3-layout/#tabbed',
    #},
    'target': {
        'url': 'http://www.w3.org/TR/css3-hyperlinks/#the-target',
    },
    'target-name': {
        'url': 'http://www.w3.org/TR/css3-hyperlinks/#the-target-name',
    },
    'target-new': {
        'url': 'http://www.w3.org/TR/css3-hyperlinks/#the-target-new',
    },
    'target-position': {
        'url': 'http://www.w3.org/TR/css3-hyperlinks/#the-target-position',
    },
    'text-align-last': {
        'url': 'http://www.w3.org/TR/css3-text/#text-align-last',
    },
    'text-emphasis': {
        'url': 'http://www.w3.org/TR/css3-text/#text-emphasis',
    },
    'text-height': {
        'url': 'http://www.w3.org/TR/css3-linebox/#text-height',
    },
    'text-justify': {
        'url': 'http://www.w3.org/TR/css3-text/#text-justify',
    },
    'text-outline': {
        'url': 'http://www.w3.org/TR/css3-text/#text-outline',
    },
    'text-wrap': {
        'url': 'http://www.w3.org/TR/css3-text/#text-wrap',
    },
    'transition': {
        'url': 'http://www.w3.org/TR/css3-transitions/#transition',
    },
    'transition-delay': {
        'url': 'http://www.w3.org/TR/css3-transitions/#transition-delay',
    },
    'transition-duration': {
        'url': 'http://www.w3.org/TR/css3-transitions/#transition-duration',
    },
    'transition-property': {
        'url': 'http://www.w3.org/TR/css3-transitions/#transition-property',
    },
    'transition-timing-function': {
        'url': 'http://www.w3.org/TR/css3-transitions/#transition-timing-function',
    },
    'voice-balance': {
        'url': 'http://www.w3.org/TR/css3-speech/#voice-balance',
    },
    'voice-duration': {
        'url': 'http://www.w3.org/TR/css3-speech/#voice-duration',
    },
    'voice-pitch': {
        'url': 'http://www.w3.org/TR/css3-speech/#voice-pitch',
    },
    'voice-pitch-range': {
        'url': 'http://www.w3.org/TR/css3-speech/#voice-pitch-range',
    },
    'voice-rate': {
        'url': 'http://www.w3.org/TR/css3-speech/#voice-rate',
    },
    'voice-stress': {
        'url': 'http://www.w3.org/TR/css3-speech/#voice-stress',
    },
    'voice-volume': {
        'url': 'http://www.w3.org/TR/css3-speech/#voice-volume',
    },
    'white-space-collapse': {
        'url': 'http://www.w3.org/TR/css3-text/#white-space-collapse',
    },
    'word-break': {
        'url': 'http://www.w3.org/TR/css3-text/#word-break',
    },
    'word-wrap': {
        'url': 'http://www.w3.org/TR/css3-text/#word-wrap',
    },
}

def parseCSS3Properties():
    properties = {}
    for property_name in sorted(css3_property_details):
        details = css3_property_details.get(property_name)
        url, id = details.get('url').split("#")
        parseExtraData(property_name, properties, (url, id))
    return properties


# Soup parsing of API documentation from webpage
def main(filename):
    properties = parseCSS3Properties()

    # Write out the properties.
    
    f = file(filename, "w")

    f.write("CSS3_DATA = {\n")
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
    filename = "css3_properties.py"
    main(filename)
