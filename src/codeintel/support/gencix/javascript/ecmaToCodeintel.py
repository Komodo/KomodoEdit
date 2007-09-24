#!/usr/bin/env python

import os

import libxml2
import libxslt

# Shared code for cix generation
from codeintel2.gencix_utils import *
#from cix_utils import *

xsl_file = os.path.join(os.path.dirname(__file__), "ECMAScript.xsl")
xml_file = os.path.join(os.path.dirname(__file__), "ECMAScript.xml")
out_file = os.path.join(os.path.dirname(__file__), "javascript.cix")

# Main function
def performXSLTransform():
    styledoc = libxml2.parseFile(xsl_file)
    style = libxslt.parseStylesheetDoc(styledoc)
    doc = libxml2.parseFile(xml_file)
    result = style.applyStylesheet(doc, None)
    style.saveResultToFilename(out_file, result, 0)
    style.freeStylesheet()
    doc.freeDoc()
    result.freeDoc()


def fixFunctionDocTag(funcnode):
    doctext = funcnode.get("doc")
    if doctext:
        if funcnode.attrib["name"] == "eval":
            # Update the doc for this function call, more user friendly.
            funcnode.attrib["doc"] = doctext.replace("ECMAScript", "JavaScript")
        sp = doctext.rsplit("Return Type: ", 1)
        if len(sp) == 2:
            funcnode.attrib["doc"] = sp[0].rstrip()
            returnType = standardizeJSType(sp[1].split(None, 1)[0])
            addCixReturns(funcnode, returnType)
            return returnType
    return None

def addFunctionSignature(funcnode, returnType):
    argnodes = [ x for x in funcnode.findall('variable') if x.get("ilk") == "argument" ]
    argnames = []
    for argnode in argnodes:
        argname = argnode.get("name")
        if not argname:
            # Invalid argument name, remove it
            funcnode.remove(argnode)
        else:
            argnames.append(argname)
            if argname in ("...", ):
                # Don't want to keep these
                funcnode.remove(argnode)
    argnames = ", ".join(argnames)
    if returnType:
        signatureText = "%s(%s) -> %s" % (funcnode.attrib["name"], argnames, returnType)
    else:
        signatureText = "%s(%s)" % (funcnode.attrib["name"], argnames)
    setCixSignature(funcnode, signatureText)
            

def fixTags():
    tree = ElementTree()
    tree.parse(out_file)
    root = tree.getroot()

    for scope in root.findall(".//scope"):
        # Fix function name "parseInt()", removing brackets
        if scope.get("ilk") == "function":
            funcnode = scope
            funcnode.attrib["name"] = funcnode.attrib["name"].rstrip(" ()")
            # Fix doc tags
            returnType = fixFunctionDocTag(funcnode)
            # Add a signature
            addFunctionSignature(funcnode, returnType)

    # Now update the hierarchy, the classes inherit from Object, so we add
    # a classref and then remove any duplicated functions/variables.
    objElem = None
    for scope in root.findall(".//scope"):
        if scope.get("ilk") == "class":
            if scope.attrib["name"] == "Object":
                objElem = scope
            else:
                addClassRef(scope, "Object")
                if objElem is None:
                    raise Exception("Did not find the Object scope!")
                # Remove all duplicated functions between this class and Object
                for childnode in scope.getchildren():
                    name = childnode.get("name")
                    try:
                        objChildNode = objElem.names[name]
                        # Both have something with this name, check details
                        if childnode.tag == objChildNode.tag and \
                           childnode.get("ilk") == objChildNode.get("ilk") and \
                           childnode.get("signature") == objChildNode.get("signature") and \
                           childnode.get("doc") == objChildNode.get("doc"):
                            # They match, remove the duplicate from scope
                            print "Removing duplicated Object item: %s, from %s" % (
                                        name, scope.get("name"))
                            scope.remove(childnode)
                        else:
                            print "Duplicate %s differed in %s" % (name, scope.get("name"))
                    except KeyError:
                        # Not found, so that is okay
                        pass

    tree.write(out_file)

def tidy():
    os.popen("tidy -xml -m -w 1000 -i %s" % (out_file))

def main():
    performXSLTransform()
    fixTags()
    tidy()

# When run from command line
if __name__ == '__main__':
    main()
