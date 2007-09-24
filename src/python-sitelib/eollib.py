# Copyright (c) 2000-2006 ActiveState Software Inc.
# See the file LICENSE.txt for licensing information.

"""End-of-line constants, detection and manipulation."""

import sys

# Need xpcom.components for 'eol2scimozEOL', can move back to koDocument.py
# if requiring XPCOM is a pain.
from xpcom import components


EOL_LF = 0
EOL_CR = 1
EOL_CRLF = 2
EOL_MIXED = 3
EOL_NOEOL = 4
if sys.platform.startswith('win'):
    EOL_PLATFORM = EOL_CRLF
elif sys.platform.startswith('mac'):
    EOL_PLATFORM = EOL_CR
else:
    EOL_PLATFORM = EOL_LF
    

# EOL conversion mappings
#
# Stating that something is EOL_FOO is in-specific. Here is an attempt
# at standardization to avoid this confusion in the future. There are
# four "types" of EOL variables:
#   eol         One of the EOL_* constants in eollib.py (and duplicated
#               in koIDocument).
#   scimozEOL   One of the SC_EOL_* constants defined in ISciMoz
#   eolStr      One of '\r', '\r\n', '\n'. Use for string manipulations.
#   eolName     A string version of each of the EOL_* constants, e.g.
#               "EOL_LF" and "EOL_MIXED". This is generally only useful
#               for logging and debugging.
#   eolPref     A string used in the prefs to refer to EOL_CR, EOL_CRLF
#               or EOL_LF.
# To avoid confusion all EOL-related variable names should make it
# obvious which of the above four is being used.
#
scimozEOL2eol = {components.interfaces.ISciMoz.SC_EOL_CR: EOL_CR,
                 components.interfaces.ISciMoz.SC_EOL_CRLF: EOL_CRLF,
                 components.interfaces.ISciMoz.SC_EOL_LF: EOL_LF}
eol2scimozEOL = {EOL_CR: components.interfaces.ISciMoz.SC_EOL_CR,
                 EOL_CRLF: components.interfaces.ISciMoz.SC_EOL_CRLF,
                 EOL_LF: components.interfaces.ISciMoz.SC_EOL_LF}
eol2eolStr = {EOL_CR: "\r",
              EOL_CRLF: "\r\n",
              EOL_LF: "\n"}
eol2eolName = {EOL_CR: "EOL_CR",
               EOL_CRLF: "EOL_CRLF",
               EOL_LF: "EOL_LF",
               EOL_MIXED: "EOL_MIXED",
               EOL_NOEOL: "EOL_NOEOL"}
eolPref2eol = {
    "CR": EOL_CR,
    "CRLF": EOL_CRLF,
    "LF": EOL_LF,
}
eol2eolPref = {EOL_CR: "CR",
               EOL_CRLF: "CRLF",
               EOL_LF: "LF"}
eolMappings = eol2eolStr  #XXX For backwards compat.

# 'newl' is the current newline delimiter for the current platform
#XXX 'newl' should die, currently being used in koPrefs.py, koProject.py,
#    koXMLPrefs.py
newl = eol2eolStr[EOL_PLATFORM]



def detectEOLFormat(buffer):
    r"""detectEOLFormat('test\r\n\n\n') => (EOL_MIXED, EOL_LF)
    
    Return a 2-tuple containing a code for the detected end-of-line format and
    a code for the suggested end-of-line format to use for the given buffer,
    which may be different if the end-of-line terminator was ambiguous. If the
    buffer does not contain any end-of-lines, the return value will be
    (EOL_NOEOL, -1).
    
    XXX Should change that last to (EOL_NOEOL, None).
    """
    
    numCRLFs = buffer.count("\r\n")
    numCRs   = buffer.count("\r") - numCRLFs
    numLFs   = buffer.count("\n") - numCRLFs

    if numCRLFs == numLFs == numCRs == 0:
        return (EOL_NOEOL, -1)

    eols = [(numCRLFs, EOL_CRLF), (numCRs, EOL_CR), (numLFs, EOL_LF)]
    eols.sort()

    if eols[0][0] or eols[1][0]:
        return (EOL_MIXED, eols[2][1])
    else:
        return (eols[2][1], eols[2][1])


def getMixedEOLLineNumbers(buffer, expectedEOL=None):
    r"""getMixedEOLLineNumbers('a\nb\r\nc\nd\n') => [1]
    
        "buffer" is the buffer to analyze
        "expectedEOL" indicates the expected EOL for each line, it is one of
            the EOL_LF, EOL_CR, EOL_CRLF constants. It may also be left out
            (or None) to indicate that the most common EOL in the buffer
            is the expected one.
    
    Return a list of line numbers (0-based) with an EOL that does not match
    the expected EOL.
    """
    lines = buffer.splitlines(1)
    lfs = []; crs = []; crlfs = []
    for i in range(len(lines)):
        line = lines[i]
        if line.endswith("\r\n"): crlfs.append(i)
        elif line.endswith("\n"): lfs.append(i)
        elif line.endswith("\r"): crs.append(i)

    # Determine the expected EOL.
    if expectedEOL is None:
        eols = [(len(crlfs), EOL_CRLF),
                (len(crs), EOL_CR),
                (len(lfs), EOL_LF)]
        eols.sort()   # last in the list is the most common
        expectedEOL = eols[-1][1]
    
    # Get the list of lines with unexpected EOLs.
    if expectedEOL == EOL_LF:
        mixedEOLs = crs + crlfs
    elif expectedEOL == EOL_CR:
        mixedEOLs = lfs + crlfs
    elif expectedEOL == EOL_CRLF:
        mixedEOLs = crs + lfs
    else:
        raise ValueError("illegal 'expected EOL' value: %r")
    mixedEOLs.sort()
    return mixedEOLs

def convertToEOLFormat(buffer, format):
    r"""convertToEOLFormat("Test\r\n", EOL_LF) => "Test\n"

    Return the buffer with all EOLs converted to the given format.
    """
    import re
    return re.sub('\r\n|\r|\n', eolMappings[format], buffer)


def test():
    assert detectEOLFormat('\r') == (EOL_CR, EOL_CR)
    assert detectEOLFormat('\r\n') == (EOL_CRLF, EOL_CRLF)
    assert detectEOLFormat('\n') == (EOL_LF, EOL_LF)
    assert detectEOLFormat('') == (EOL_NOEOL, -1)
    assert detectEOLFormat('\rTest\r\n\r') == (EOL_MIXED, EOL_CR)

    assert convertToEOLFormat('\rTest\r\nTest2\nTest\n\r\n',EOL_LF) == '\nTest\nTest2\nTest\n\n'
    assert convertToEOLFormat('\r\r\r\nTest\n\nTest2\nTest\n\n\n',EOL_CRLF) == '\r\n\r\n\r\nTest\r\n\r\nTest2\r\nTest\r\n\r\n\r\n'

if __name__ == '__main__':
    test()
