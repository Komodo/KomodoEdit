from xpcom import components, ServerException
from koLanguageServiceBase import *

def registerLanguage(registery):
    registery.registerLanguage(koTextLanguage())
    
class koTextLanguage(KoLanguageBase):
    name = "Text"
    _reg_desc_ = "%s Language" % name
    _reg_contractid_ = "@activestate.com/koLanguage?language=%s;1" \
                       % (name)
    _reg_clsid_ = "{CDFF6BC6-C21B-420c-9796-C90C37377FE6}"

    accessKey = 'e'
    primary = 1
    defaultExtension = ".txt"
    commentDelimiterInfo = { "line": [ "#" ]  }
    sample = "Text files only have one style."

    def __init__(self):
        """In plain text we can't tell when a quote starts a sentence and
        when it means something else, so we simply never provide a close-quote.
        """
        KoLanguageBase.__init__(self)
        del self.matchingSoftChars["'"]
        del self.matchingSoftChars['"']

    def getEncodingWarning(self, encoding):
            return ''
        
    def guessIndentation(self, scimoz, tabWidth):
        guess = 0
        usesTabs = 0
        N = min(scimoz.lineCount, 100)
        for lineNo in range(N):
            lineEndPos = scimoz.getLineEndPosition(lineNo)
            lineStartPos = scimoz.positionFromLine(lineNo)
            line = scimoz.getTextRange(lineStartPos, lineEndPos)
            if line.strip():
                guess = len(line) - len(line.lstrip())
                break
        # investigate whether tabs are used
        for lineNo in range(N):
            lineEndPos = scimoz.getLineEndPosition(lineNo)
            lineStartPos = scimoz.positionFromLine(lineNo)
            line = scimoz.getTextRange(lineStartPos, lineEndPos)
            front = line[:len(line)-len(line.lstrip())]
            if '\t' in front or u'\t' in front:
                usesTabs = 1
                break
        return guess, usesTabs
