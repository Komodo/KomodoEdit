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

"""
There are many methods but only one import one:

def autoDetectEncoding(buffer):
    buffer -> (unicode buffer, encoding_name, bom)

    Attempts to determine the encoding of a buffer using
    the buffer's BOM, xml encoding and then a series of
    educated guesses.
    
    Returns (None,*,*) if encoding cannot be detected.
    Should never throw an exception.

You would use this module like this:

encoded, encoding, bom = autoDetectEncoding(text_from_disk)
if not encoding:
    alert( "could not detect encoding")
else:
    # "encoded" contains a unicode object representing the text_from_disk
    # "encoding" contains the original encoding of text_from_disk and is
    #   garanteed to be available in the current environment
    # "bom" contains the buffer's byte-order-marker, which should be
    #   prepended to the file when it is saved.
"""


import codecs, encodings, re

re_firstline = re.compile(ur'(.*?)(?:\r|\n|$)')
re_htmlmeta = re.compile(ur'<meta.*?charset=(.*?)">')

"""Komodo will hand this library a buffer and ask it to either convert
it or auto-detect the type."""

# None represents a potentially variable byte. "##" in the XML spec... 
autodetect_dict={ # bytepattern     : ("encoding"),
# XXX python 2.2 doesn't support ucs-4 in codecs module, odd since
# you can compile python with ucs4 support
#                (0x00, 0x00, 0xFE, 0xFF) : ("ucs4-be"),        
#                (0xFF, 0xFE, 0x00, 0x00) : ("ucs4-le"),
                (0xFE, 0xFF, None, None) : ("utf-16-be"), 
                (0xFF, 0xFE, None, None) : ("utf-16-le"), 
                (0xEF, 0xBB, 0xBF, None): ("utf-8")
                 }
                
def checkBOM(buffer):
    """ buffer -> encoding_name

        Return the encoding based on the buffer's BOM
        Returns None if encoding cannot be detected.
    """
    
    for i in range(min(4,len(buffer)),0,-1):
        encoding = autodetect_dict.get( tuple(map(ord, buffer[0:i]) + [None] * (4-i)) )
        if encoding:
            return (encoding, i)

    return (None,0)

def tryEncoding(buffer, encoding):
    """ buffer, encoding -> encoding_buffer

        Attempts to encode the buffer using the specified encoding

        Returns None on failure, a Unicode version of the buffer on success.
    """
    
    try:
        secret_decoder_ring = codecs.lookup(encoding)[1]
    except LookupError, e:
        # the encoding name doesn't exist, likely a pep263 failure
        # an example is using windows-1250 as the name
        return None
    try:
        (outdata,len) = secret_decoder_ring(buffer)
        return outdata
    except Exception, e: # Figure out the real exception types
        return None

pep263re = re.compile("coding[:=]\s*([\w\-_.]+)")

def autoDetectEncoding(buffer,
                       tryXMLDecl = 0,
                       tryHTMLMeta = 0,
                       tryModeline = 0,
                       wantEncoding=None,
                       defaultEncoding='iso8859-1'):
    """ buffer -> (unicode buffer, encoding_name, bom)

        Attempts to determine the encoding of a buffer using
        the buffer's BOM, xml encoding and then a series of
        educated guesses.
        
        Returns (None,*,*) if encoding cannot be detected.
    """

    if len(buffer) > 2:
        # Give the XML autodection code the first crack at it
        if tryXMLDecl:
            decodedBuffer, xmlEncoding, bom = autoDetectXMLEncoding(buffer)
            if decodedBuffer is not None:
                return (decodedBuffer, xmlEncoding, bom)
        
        # Give the HTML autodection code second crack at it
        if tryHTMLMeta:
            decodedBuffer, xmlEncoding, bom = autoDetectHTMLEncoding(buffer)
            if decodedBuffer is not None:
                return (decodedBuffer, xmlEncoding, bom)
    
        if tryModeline:
            # Give the coding: modeline detection for Python (PEP 263) a crack
            # if this fails, we want to continue trying other encodings to at least
            # open the file for the user.
            split = buffer.split('\n', 2)
            firstline = split[0]
            match = pep263re.search(firstline)
            if not match and len(split) > 1:
                secondline = split[1]
                match = pep263re.search(secondline)
            if match:
                encoding_name = match.group(1)
                decodedBuffer = tryEncoding(buffer, encoding_name)
                # specifying windows code pages with something like 'windows-1250' is
                # common, but python does not recognize that.  Python likes cp1250
                # instead.  So if we fail on that kind of name, lets try the alternate
                if decodedBuffer:
                    return (decodedBuffer, encoding_name, '')
                elif encoding_name.startswith('windows-'):
                    enc = 'cp%s' % encoding_name[8:]
                    decodedBuffer = tryEncoding(buffer, enc)
                    if decodedBuffer:
                        return (decodedBuffer, enc, '')
    
        # If we've got a BOM, then depend on it to be correct
        # this handles UCS-4, UTF-16 and UTF-8 if the BOM is present
        BOMencoding, bomLength = checkBOM(buffer)
        if BOMencoding and bomLength:
            decodedBuffer = tryEncoding(buffer[bomLength:], BOMencoding)
            if decodedBuffer is not None:
                return (decodedBuffer, BOMencoding, buffer[:bomLength])

    # 8-bit detection will ALWAYS work on a utf-8 file, however 8-bit files will not always
    # convert to utf-8 (ie. only by chance will they), so we MUST check utf-8 first.  The
    # only time we dont try utf-8 first is if the file fits in the ascii 7 bit
    # range, then we should prefer the desired (or system set) encodings. Most 8
    # bit non-utf-8 documents should fail both conversion to ascii and to utf-8,
    # so they will fall into either the desired encoding or the default
    # encoding. We have one last attempt, which is to use 8859-1. The only way
    # that should be reached is if the desired and default encodings are some
    # combination of ascii and utf-8. Famous last words...There should be no way
    # to ever fail in this function.
    
    # try ascii only to rule that out as a utf-8 file
    asciiBuffer = tryEncoding(buffer,'ascii')
    if not asciiBuffer:
        # it's not ascii, try utf-8 to see if it's valid utf-8 data
        decodedBuffer = tryEncoding(buffer,'utf-8')
        if decodedBuffer is not None:
            return (decodedBuffer, 'utf-8', '')

    # It's either ascii or 8 bit data that is not valid utf-8 data. Now try the
    # 8-bit encodings, first the one we want, then our default, and fall back to
    # a predefined default. The only way to get past what we want, or our
    # default is if they end up as ascii and/or utf-8, which is possible, and
    # our data is 8 bit.
    if wantEncoding:
        decodedBuffer = tryEncoding(buffer, wantEncoding)
        if decodedBuffer is not None:
            return (decodedBuffer, wantEncoding, '')
        
    decodedBuffer = tryEncoding(buffer, defaultEncoding)
    if decodedBuffer is not None:
        return (decodedBuffer, defaultEncoding, '')
    
    # since what we want or our default both failed, if we have an ascii buffer, return it
    if asciiBuffer:
        return (asciiBuffer, 'ascii', '')
    
    # everything failed due to configuration, this should never fail, since we
    # already checked for utf-8 and ascii, all that is left is 8bit.
    return (tryEncoding(buffer, 'iso8859-1'), 'iso8859-1', '')             
    
        
def autoDetectXMLEncoding(buffer):
    """ buffer -> (unicode buffer, encoding_name, bom)

        Attempts to determine the encoding of a buffer using
        the buffer's BOM or xml encoding.
        
        Returns (None,None,'') if encoding cannot be detected.
    """

    BOMencoding, bomLength = checkBOM(buffer)
    bom = buffer[0:bomLength]
    
    if BOMencoding:
        encoding = BOMencoding
        buffer = buffer[bomLength:]
    else:
        encoding = 'utf-8'
        
    # try to find a more precise encoding using xml declaration
    try:
        secret_decoder_ring = codecs.lookup(encoding)[1]
        (decoded,length) = secret_decoder_ring(buffer) 
    except:
        return (None, None, '')
    
    first_line = re_firstline.match(decoded).groups(0)[0]
    if first_line and first_line.startswith(u"<?xml"):
        encoding_pos = first_line.find(u"encoding")
        if encoding_pos!=-1:
            # look for double quote
            quote_pos=first_line.find('"', encoding_pos) 

            if quote_pos==-1:                 # look for single quote
                quote_pos=first_line.find("'", encoding_pos) 

            if quote_pos>-1:
                quote_char,rest=(first_line[quote_pos],
                                            first_line[quote_pos+1:])
                tryEncoding=rest[:rest.find(quote_char)]
                try:
                    (decoded,length) = codecs.lookup(tryEncoding)[1](buffer)
                    return (decoded,str(tryEncoding),bom)
                except:
                    pass
    if bom:
        return (decoded, encoding, bom)                 
    else:
        return (None, None, '') # Without a BOM or xml decl, there is no basis for a guess

def autoDetectHTMLEncoding(buffer):
    """ buffer -> (unicode buffer, encoding_name, bom)

        Attempts to determine the encoding of a buffer using
        the buffer's BOM or xml encoding.
        
        Returns (None,None,'') if encoding cannot be detected.
    """

    BOMencoding, bomLength = checkBOM(buffer)
    bom = buffer[0:bomLength]
    
    if BOMencoding:
        encoding = BOMencoding
        buffer = buffer[bomLength:]
    else:
        encoding = 'utf-8'
        
    # try to find a more precise encoding using meta declaration
    try:
        secret_decoder_ring = codecs.lookup(encoding)[1]
        (decoded,length) = secret_decoder_ring(buffer) 
    except:
        return (None, None, '')
    
    tryEncoding = re_htmlmeta.match(decoded)
    try:
        enc = tryEncoding.groups(0)[0]
        (decoded,length) = codecs.lookup(enc)[1](buffer)
        return (decoded,str(enc),bom)
    except:
        pass
    if bom:
        return (decoded, encoding, bom)                 
    else:
        return (None, None, '') # Without a BOM or xml decl, there is no basis for a guess
    
def decoderAvailable(name):
    try:
        codecs.lookup(name)
        return 1
    except LookupError:
        return 0

def makeUTF8(buffer, encoding):
    secret_decoder_ring = codecs.lookup(encoding)[1]
    (outdata,len) = secret_decoder_ring(buffer)
    rc = codecs.utf_8_encode(outdata)[0]
    return rc

def makeRaw(buffer, encoding, errors='strict'):
    (out, len) = codecs.getencoder(encoding)(buffer, errors)
    return out

def recode_unicode(buffer, from_encoding, to_encoding, errors='strict'):
    """recode_unicode
    
    This takes a unicode string, encodes it using from_encoding, then decodes
    using to_encoding, and returns a unicode string.
    
    In some instances, unicode object would not change, shortcuts will be taken.
    """
    assert(type(buffer)==type(u''))
    # unicode can always be decoded to utf-*, so we do not need to do
    # anything to recode the string now.
    if to_encoding.startswith('utf'):
        return buffer
    # get a raw string of the buffer (ie. non-unicode)
    if from_encoding.startswith('utf'):
        (raw, len) = codecs.getencoder(to_encoding)(buffer, errors)
    else:
        # we're going 8bit to 8bit, so we must do it all
        (raw, len) = codecs.getencoder(from_encoding)(buffer, errors)
    # convert back to a unicode string with the new encoding
    # decode to ucs-2 unicode object
    return unicode(raw, to_encoding, errors)

def recode_raw(buffer, from_encoding, to_encoding, errors='strict'):
    assert(type(buffer)==type(''))
    # make sure the from_encoding is good
    (uni, len) = codecs.getdecoder(from_encoding)(buffer, errors)
    (raw, len) = codecs.getencoder(to_encoding)(uni, errors)
    return raw    

def recode(buffer, from_encoding, to_encoding, errors='strict', raw=1):
    if type(buffer) == type(u''):
        newbuffer = recode_unicode(buffer, from_encoding, to_encoding, errors)
        if raw:
            return makeRaw(newbuffer, to_encoding)
        return newbuffer
    else:
        newbuffer = recode_raw(buffer, from_encoding, to_encoding, errors)
        if not raw:
            return tryEncoding(newbuffer, to_encoding)
        return newbuffer

