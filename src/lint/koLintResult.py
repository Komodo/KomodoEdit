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


import os
import re
import tempfile

import koprocessutils
import process
from xpcom import components
from koLintResults import koLintResults

SEV_ERROR = 2   # No xpcom here :(
SEV_WARNING = 1
SEV_INFO = 0

def createAddResult(results, textlines, severity, lineNo, desc, leadingWS=None, columnStart=1):
    """
    lineNo is 1-based
    """
    lineNo = int(lineNo)
    if lineNo > len(textlines):
        lineNo = len(textlines)
    while lineNo >= 0 and len(textlines[lineNo - 1]) == 0:
        lineNo -= 1
    if lineNo == 0:
        return
    targetLine = textlines[lineNo - 1]
    if leadingWS is not None:
        columnEndOffset = len(leadingWS)
    else:
        columnEndOffset = 0
    columnEnd = len(targetLine) + 1 - columnEndOffset

    result = KoLintResult(description=desc,
                          severity=severity,
                          lineStart=lineNo,
                          lineEnd=lineNo,
                          columnStart=columnStart,
                          columnEnd=columnEnd)
    results.addResult(result)

_leading_ws_ptn = re.compile(r'(\s+)')
def runGenericLinter(text, extension, cmd_start, err_ptns, warn_ptns, cwd, useStderr):
    tmpfilename = tempfile.mktemp() + extension
    fout = open(tmpfilename, 'wb')
    fout.write(text)
    fout.close()
    cmd = cmd_start + [tmpfilename]
    try:
        p = process.ProcessOpen(cmd, cwd=cwd, env=koprocessutils.getUserEnv(), stdin=None)
        stdout, stderr = p.communicate()
        if useStderr:
            errLines = stderr.splitlines(0) # Don't need the newlines.
        else:
            errLines = stdout.splitlines(0) # Don't need the newlines.
        textLines = None
    except:
        log.exception("Failed to run %s, cwd %r", cmd, cwd)
        return None
    finally:
        os.unlink(tmpfilename)
    results = koLintResults()
    all_ptns = (zip(err_ptns, [SEV_ERROR] * len(err_ptns))
                + zip(warn_ptns, [SEV_WARNING] * len(warn_ptns)))
    for line in errLines:
        for ptn, sev in all_ptns:
            m = ptn.match(line)
            if m:
                if textLines is None:
                    textLines = text.splitlines()
                m1 = _leading_ws_ptn.match(line)
                createAddResult(results, textLines, sev, m.group(1),
                                m.group(2),
                                m1 and m1.group(1) or None)
                break
    return results        

def encodeRequestText(request, text=None):
    if text is None:
        text = request.text
    if type(text) == unicode:
        try:
            return text.encode(request.encoding.python_encoding_name)
        except (UnicodeEncodeError, UnicodeDecodeError):
            log.exception("Failed to %s-encode %s%s ",
                          request.encoding.python_encoding_name,
                          text[:160],
                          len(text) >= 160 and "..." or "")
            try:
                return text.encode('utf-8')
            except (UnicodeEncodeError, UnicodeDecodeError):
                # We have to return something, so go with '?' for unreplaceable characters.
                return text.encode('utf-8', 'replace')
    # Otherwise assume the text is appropriately encoded
    return text
    
class KoLintResult:
    _com_interfaces_ = [components.interfaces.koILintResult]
# This object is never actually registered and created by contract ID.
# Our language linters create them explicitly.
#    _reg_desc_ = "Komodo Lint Result"
#    _reg_clsid_ = "{21648850-492F-11d4-AC24-0090273E6A60}"
#    _reg_contractid_ = "Komodo.LintResult"

    SEV_INFO    = components.interfaces.koILintResult.SEV_INFO
    SEV_WARNING = components.interfaces.koILintResult.SEV_WARNING
    SEV_ERROR   = components.interfaces.koILintResult.SEV_ERROR

    def __init__(self, description="", severity=None, lineStart=-1, lineEnd=-1, columnStart=-1, columnEnd=-1):
        self.lineStart = lineStart
        self.lineEnd = lineEnd
        self.columnStart = columnStart
        self.columnEnd = columnEnd
        self.description = description
        self.encodedDescription = None
        self.severity = severity

    def __str__(self):
        return "%d:%d (%d-%d) sev:%r %s" % (
            self.lineStart,
            self.lineEnd,
            self.columnStart,
            self.columnEnd,
            self.severity,
        self.description)

    def _encode_string(self, s):
        return re.sub(# match 0x00-0x1f except TAB(0x09), LF(0x0A), and CR(0x0D)
                   '([\x00-\x08\x0b\x0c\x0e-\x1f])',
                   # replace with XML decimal char entity, e.g. '&#7;'
                   lambda m: '\\x%02X'%ord(m.group(1)),
                   s)

    # XXX since this object is not created through xpcom createinstance,
    # using a setter doesn't work.  However, we access it through xpcom
    # from javascript, so we can do our encoding once in the getter
    # to prevent UI crashes.
    def get_description(self):
        if self.encodedDescription is None:
            _gEncodingServices = components.classes['@activestate.com/koEncodingServices;1'].\
                     getService(components.interfaces.koIEncodingServices)
            try:
                unicodebuffer, encoding, bom = _gEncodingServices.\
                                                 getUnicodeEncodedStringUsingOSDefault(self.description)
                self.encodedDescription  = self._encode_string(unicodebuffer)
            except Exception, e:
                self.encodedDescription  = repr(self.description)[1:-1] # remove quotes
        return self.encodedDescription
