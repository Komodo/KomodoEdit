"""Usage: parseJSProf.py filename"""

import re, sys

profRe = re.compile(r"\s*\[(\d+),(\d+)\]\s+([^(]+)\(\)\s+\{(\d+)-(\d+)\}\s+(\d+)(?:\s+\{min\s+(\d+),\s+max\s+(\d+)\s+avg\s+(\d+)\})?")
groupDesc = [("compiles", int), ("calls", int), ("name", str), ("base", int), ("extent", int), ("size", int), ("min", int), ("max", int), ("avg", int)]

def parse(text):
    functions = []
    currentFile = "<no file>"
    lines = text.splitlines()
    for line in lines:
        match = profRe.match(line)
        if match:
            item = {}
            item["file"] = currentFile
            groups = match.groups()
            for i in range(len(groupDesc)):
                if groups[i]:
                    item[groupDesc[i][0]] = groupDesc[i][1](groups[i])
                else:
                    item[groupDesc[i][0]] = None
            functions.append(item)
        else:
            currentFile = line
    return functions


anonFuncRe = re.compile(r"\s*([^\s:=]+)\s*[=:]\s*function")
def findRealFunctionName(chromeURL, base):
    import urlparse, os
    partialPath = urlparse.urlparse(chromeURL)[2]
    args = ["src", "chrome"] + partialPath.split('/')
    filename = apply(os.path.join, args)
    file = open(filename)
    text = file.read()
    file.close()
    line = text.splitlines()[base-1]
    if line.strip() == "{":
        line = text.splitlines()[base-2]
    match = anonFuncRe.match(line)
    if match:
        return match.group(1)
    else:
        return line

def getFileNameFromChromeURL(url):
    import urlparse, os
    parsedUrl = urlparse.urlparse(url)
    if parsedUrl[0] != "chrome":
        raise ValueError, "must be a chrome:// URL"

    #XXX this will only work for developer builds
    args = ["src", "chrome"] + parsedUrl[2].split('/')
    return apply(os.path.join, args)    

def resolveAnonymousFunctionNames(functions):
    """Replace "anonymous" with a guess at the real name extracted from the source file"""

    anons = filter(lambda x: x["name"] == "anonymous", functions)
    anons.sort(lambda a, b: cmp(a["file"], b["file"]))

    currURL = None
    for anon in anons:
        if anon["file"] != currURL:
            sourceFile = open(getFileNameFromChromeURL(anon["file"]))
            lines = sourceFile.read().splitlines()
            sourceFile.close()
            currURL = anon["file"]

        base = anon["base"]
        line = lines[base-1]
        if line.strip() == "{":
            line = lines[base-2]
        match = re.match("\s*([^\s:=]+)\s*[=:]\s*function", line)
        if match:
            anon["name"] = match.group(1)
        else:
            anon["name"] = line


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print __doc__
        sys.exit(1)
    text = open(sys.argv[1]).read()
    functions = parse(text)
    functions = filter(lambda x: x["calls"] != 0, functions)
    resolveAnonymousFunctionNames(functions)
    functions.sort(lambda a, b: cmp(b["calls"]*b["avg"], a["calls"]*a["avg"]))
    for function in functions:
        print function["file"], function["name"], function["calls"], function["avg"], function["calls"]*function["avg"]
