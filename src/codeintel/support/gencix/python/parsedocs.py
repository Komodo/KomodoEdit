import re
import textwrap

#---- standard module/class/function doc parsing

LINE_LIMIT = 5      # limit full number of lines this number
LINE_WIDTH = 60     # wrap doc summaries to this width

# Examples matches to this pattern:
#    foo(args)
#    foo(args) -> retval
#    foo(args) -- description
#    retval = foo(args)
#    retval = foo(args) -- description
_gPySigLinePat = re.compile(r"^((?P<retval>[^=]+?)\s*=|class)?\s*(?P<head>[\w\.]+\s?\(.*?\))\s*(?P<sep>[:<>=-]*)\s*(?P<tail>.*)$")
_gSentenceSepPat = re.compile(r"(?<=\.)\s+", re.M) # split on sentence bndry

def parseDocSummary(doclines, limit=LINE_LIMIT, width=LINE_WIDTH):
    """Parse out a short summary from the given doclines.
    
        "doclines" is a list of lines (without trailing newlines) to parse.
        "limit" is the number of lines to which to limit the summary.

    The "short summary" is the first sentence limited by (1) the "limit"
    number of lines and (2) one paragraph. If the first *two* sentences fit
    on the first line, then use both. Returns a list of summary lines.
    """
    # Skip blank lines.
    start = 0
    while start < len(doclines):
        if doclines[start].strip():
            break
        start += 1

    desclines = []
    for i in range(start, len(doclines)):
        if len(desclines) >= limit:
            break
        stripped = doclines[i].strip()
        if not stripped:
            break
        sentences = _gSentenceSepPat.split(stripped)
        if sentences and not sentences[-1].endswith('.'):
            del sentences[-1] # last bit might not be a complete sentence
        if not sentences:
            desclines.append(stripped + ' ')
            continue
        elif i == start and len(sentences) > 1:
            desclines.append(' '.join([s.strip() for s in sentences[:2]]))
        else:
            desclines.append(sentences[0].strip())
        break
    if desclines:
        if desclines[-1][-1] == ' ':
            # If terminated at non-sentence boundary then have extraneous
            # trailing space.
            desclines[-1] = desclines[-1][:-1]
        desclines = textwrap.wrap(''.join(desclines), width)
    return desclines


def parsePyFuncDoc(doc, fallbackCallSig=None, scope="?", funcname="?"):
    """Parse the given Python function/method doc-string into call-signature
    and description bits.
    
        "doc" is the function doc string.
        "fallbackCallSig" (optional) is a list of call signature lines to
            fallback to if one cannot be determined from the doc string.
        "scope" (optional) is the module/class parent scope name. This
            is just used for better error/log reporting.
        "funcname" (optional) is the function name. This is just used for
            better error/log reporting.
    
    Examples of doc strings with call-signature info:
        close(): explicitly release resources held.
        x.__repr__() <==> repr(x)
        read([s]) -- Read s characters, or the rest of the string
        recv(buffersize[, flags]) -> data
        replace (str, old, new[, maxsplit]) -> string
        class StringIO([buffer])

    Returns a 2-tuple: (<call-signature-lines>, <description-lines>)
    """
    if doc is None or not doc.strip():
        return ([], [])
    
    limit = LINE_LIMIT
    doclines = doc.splitlines(0)
    index = 0
    siglines = []
    desclines = []

    # Skip leading blank lines.
    while index < len(doclines):
        if doclines[index].strip():
            break
        index += 1

    # Parse out the call signature block, if it looks like there is one.
    if index >= len(doclines):
        match = None
    else:
        first = doclines[index].strip()
        match = _gPySigLinePat.match(first)
    if match:
        # The 'doc' looks like it starts with a call signature block.
        for i, line in enumerate(doclines[index:]):
            if len(siglines) >= limit:
                index = i
                break
            stripped = line.strip()
            if not stripped:
                index = i
                break
            match = _gPySigLinePat.match(stripped)
            if not match:
                index = i
                break
            # Now parse off what may be description content on the same line.
            #   ":", "-" or "--" separator: tail is description
            #   "-->" or "->" separator: tail if part of call sig
            #   "<==>" separator: tail if part of call sig
            #   other separtor: leave as part of call sig for now
            descSeps = ("-", "--", ":")
            groupd = match.groupdict()
            retval, head, sep, tail = (groupd.get("retval"), groupd.get("head"),
                                       groupd.get("sep"), groupd.get("tail"))
            if retval:
                siglines.append(head + " -> " + retval)
                if tail and sep in descSeps:
                    desclines.append(tail)
            elif tail and sep in descSeps:
                siglines.append(head)
                desclines.append(tail)
            else:
                siglines.append(stripped)
        else:
            index = len(doclines)
    if not siglines and fallbackCallSig:
        siglines = fallbackCallSig
    
    # Parse out the description block.
    if desclines:
        # Use what we have already. Just need to wrap it.
        desclines = textwrap.wrap(' '.join(desclines), LINE_WIDTH)
    else:
        limit -= len(siglines)
        desclines = parseDocSummary(doclines[index:], limit=limit)

    ## debug logging
    #f = open("parsePyFuncDoc.log", "a")
    #if 0:
    #    f.write("\n---- %s:\n" % funcname)
    #    f.write(pformat(siglines)+"\n")
    #    f.write(pformat(desclines)+"\n")
    #else:
    #    f.write("\n")
    #    if siglines:
    #        f.write("\n".join(siglines)+"\n")
    #    else:
    #        f.write("<no signature for '%s.%s'>\n" % (scope, funcname))
    #    for descline in desclines:
    #        f.write("\t%s\n" % descline)
    #f.close()

    return (siglines, desclines)

