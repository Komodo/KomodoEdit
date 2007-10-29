/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */
if (typeof(Casper) == 'undefined') {
    var Casper = {};
}
if (typeof(Casper.XPath) == 'undefined') {
    Casper.XPath = {};
}

Casper.XPath.log = Casper.Logging.getLogger('Casper::XPath');
Casper.XPath.XPathGenerator = function() {
    // this interface is defined at:
    // http://weblogs.mozillazine.org/weirdal/archives/008806.html
    this.searchFlags = 0;
    this.resolver = 0;
    this._attrs = {};
}

Casper.XPath.XPathGenerator.prototype.includeAttributeNS = function(namespaceURI, localName, includeAttrValue)
{
    if (typeof(this._attrs[namespaceURI]) == 'undefined') {
        this._attrs[namespaceURI] = {};
    }
    this._attrs[namespaceURI][localName] = includeAttrValue;
}

Casper.XPath.XPathGenerator.prototype.excludeAttributeNS = function(namespaceURI, localName)
{
    if (typeof(this._attrs[namespaceURI]) == 'undefined')
        return;
    delete this._attrs[namespaceURI][localName];
}

Casper.XPath.XPathGenerator.prototype.clearAttributes = function()
{
    this._attrs = {};
}

Casper.XPath.XPathGenerator.prototype.generateXPath = function(targetNode, contextNode)
{
    Casper.XPath.log.debug("generateXPath: "+targetNode.nodeName);
    var lastElementPath = this._elementXPath(targetNode);
    var path = '/' + lastElementPath;
    var prevPath = '';
    var node = targetNode;
    var i, j;
    var parent = node.parentNode;
    var lastbinding = null;
    var binding = null;
    while (parent && parent.nodeType == Components.interfaces.nsIDOMNode.ELEMENT_NODE) {
            Casper.XPath.log.debug("  node: "+node.nodeName+" parent "+parent.nodeName);
        binding = node.ownerDocument.getBindingParent(node);
        if (binding) {
            Casper.XPath.log.debug("  binding: "+binding);
            Casper.XPath.log.debug("  binding name "+binding.nodeName);
        }
        if (binding == parent) {
            // we want our position in the parent
            // http://wiki.mozilla.org/DOM:XPath_Generator#XPath:_Content_Boundaries
            var p = this._getPosition(node, binding);
                Casper.XPath.log.debug("    binding is parent, child pos "+p);
            if (p >= 0)
                prevPath = "/anonymousChild()["+p+"]/." + prevPath;
            else
                prevPath = '/anonymousChild()[0]/.' + prevPath;
        } else if (binding == node) {
            // what do we do here?
            Casper.XPath.log.debug("    binding is node! "+node.nodeName);
        } else {
            if (binding != null) 
                Casper.XPath.log.debug("    binding? "+binding.nodeName+" for node "+node.nodeName);
            lastElementPath = this._elementXPath(node);
            prevPath = '/' + lastElementPath + prevPath;
        }
        path = "/" + this._elementXPath(parent) + prevPath;
        node = parent;
        parent = node.parentNode;
    }
    Casper.XPath.log.debug("  generated "+path);
    if (parent == contextNode && contextNode != targetNode.ownerDocument)
        return "/" + path;
    return path;
}

Casper.XPath.XPathGenerator.prototype.generateXPointer = function(targetNode, contextNode) {
    throw "Not Implemented";
}

Casper.XPath.XPathGenerator.prototype._getPosition = function(node, binding) {
    if (typeof(binding) == 'undefined')
        binding = null;
    var position = -1;
    if (node.parentNode) {
        var childNodes;
        if (binding)
            childNodes = binding.ownerDocument.getAnonymousNodes(binding);
        else
            childNodes = node.parentNode.getElementsByTagName(node.nodeName);
        Casper.XPath.log.debug("      node has children: "+(childNodes?childNodes.length:0));
        if (childNodes && childNodes.length > 1) {
            var j;
            for (j = 0; j < childNodes.length; j++) {
                if (childNodes[j] == node) {
                    position = j;
                    break;
                }
            }
        }
    }
    return position;
}

Casper.XPath.XPathGenerator.prototype._elementXPath = function(node, binding)
{
    if (typeof(node.nodeName) == 'undefined') {
        return "";
    }
    if (node.nodeName == "#document")
        node = node.documentElement;
    if (typeof(binding) == 'undefined')
        binding = null;
    
    var i;
    var needPos = true;
    // we always use a position
    var p = this._getPosition(node, binding);
    var position = "";
    if (p >= 0)
        position = "["+(p + 1)+"]";
    
    var conditions = new Object();
    if (node.attributes && this._attrs) {
        for (i = 0; i < node.attributes.length; i++) {
            var att = node.attributes[i];
            if (typeof(this._attrs[att.namespaceURI]) != 'undefined') {
                if (typeof(this._attrs[att.namespaceURI][att.name]) != 'undefined') {
                    if (position && att.name == 'id')
                        position = '';
                    if (this._attrs[att.namespaceURI][att.name])
                        conditions['@' + att.name] = att.value;
                    else
                        conditions['@' + att.name] = null;
                }
            }
        }
    }
    
    // XXX create a default prefix if no prefix
    // http://lxr.mozilla.org/mozilla1.8/source/dom/public/idl/xpath/
    
    // here we have to use "xmlns" as the prefix if no prefix exists
    var prefix = node.prefix
    if (prefix == null) {
        try {
        prefix = node.ownerDocument.documentElement.lookupPrefix(node.namespaceURI);
        Casper.XPath.log.debug("     node.ownerDocument.documentElement.lookupPrefix ["+prefix+"]");
        if (!prefix)
            prefix = node.prefix;
        } catch(e) {
            Casper.XPath.log.exception(e);
            dump(Casper.XPath.log.getObjectTree(node));
        }
    }
    if (prefix == null) {
        Casper.XPath.log.debug("find prefix/ns for node ["+node.nodeName+"] ns ["+node.namespaceURI+"]");
        prefix = node.lookupPrefix(node.namespaceURI);
        Casper.XPath.log.debug("     node.lookupPrefix ["+prefix+"]");
    } 
    var nodeName = prefix+":"+node.localName;
    return nodeName.toLowerCase() + position + this._encodeConditions(conditions);
}

Casper.XPath.XPathGenerator.prototype._encodeConditions = function(atts)
{
    var att;
    var result = '';
    var first = true;
    var count = 0;
    for (att in atts) {
        if (!first) result += ' and ';
        if (atts[att] == null) {
            result += att;
        } else
        if (att == 'position()') {
            result += att + '=' + atts[att];
        } else {
            result += att + '=\"' + atts[att].replace(/\"/g, "&quot;") + '\"';
        }
        first = false;
        count++;
    }
    if (result != '') {
        if (count == 1 && atts['position()'] != null) {
            return '[' + atts['position()'] + ']';
        } else {
            return '[' + result + ']';
        }
    } else {
        return '';
    }
}

Casper.XPath.createNSResolver = function(aNode) {
    var resolver = {
      node: 0,
      doc: 0,
      lookupNamespaceURI: function(aPrefix) {
        var ns = this.node.lookupNamespaceURI(aPrefix);
        if (!ns)
            ns = this.node.ownerDocument.documentElement.lookupNamespaceURI(aPrefix);
        if (!ns)
            ns = this.node.namespaceURI;
        Casper.XPath.log.debug("resolve "+aPrefix+" to "+ns);
        return ns;
      }
    }
    if (typeof(aNode.documentElement) != 'undefined') {
        resolver.node = aNode.documentElement;
    }
    else if (typeof(aNode.ownerDocument) != 'undefined') {
        resolver.node = aNode;
    }
    return resolver;
}

Casper.XPath.evaluatePaths = function(aNode, aExpr, type)
{
    // first, split into multiple xpaths so we can dig into anon nodes
    var finalNode = null;
    try {
        //(.*?)/anonymousChild\(\)\[(\d+)\]
        var paths = aExpr.split(/\/anonymousChild\(\)\[(\d+)\]\/?/);
        if (paths.length == 1) {
            return Casper.XPath.evaluateXPath(aNode , aExpr, type);
        }
        Casper.XPath.log.debug("evaluatePaths: "+paths);
        var contextNode = aNode;
        var i=0;
        for (i = 0; i < paths.length; i++) {
            Casper.XPath.log.debug("    ["+paths[i]+"]");
            finalNode = Casper.XPath.evaluateXPath(contextNode, paths[i], type);
            if (finalNode && finalNode.length > 0) {
                var tn = finalNode[0];
                Casper.XPath.log.debug("    node is ["+tn.nodeName+"]");
                Casper.XPath.log.debug("    contextNode is ["+contextNode.nodeName+"]");
                var anon = tn.ownerDocument.getAnonymousNodes(tn);
                if (++i < paths.length) {
                    contextNode = anon[paths[i]];
                    finalNode = [contextNode];
                }
            } else {
                Casper.XPath.log.debug("  ** NO RESULT");
            }
        }
    Casper.XPath.log.debug("    final node is ["+finalNode[0].nodeName+"]");
    } catch(e) {
        Casper.XPath.log.exception(e, paths+"\ncurrent: ["+paths[i]+"]");
    }
    return finalNode;
}
// Evaluate an XPath expression aExpression against a given DOM node
// or Document object (aNode), returning the results as an array
// thanks wanderingstan at morethanwarm dot mail dot com for the
// initial work.
Casper.XPath.evaluateXPath = function(aNode, aExpr, type) {
    var result;
    Casper.XPath.log.debug("evaluateXPath "+aExpr);
    if (typeof(type) == 'undefined')
        type = XPathResult.ANY_TYPE;
    var xpe = new XPathEvaluator();
    //var nsResolver = xpe.createNSResolver(aNode.ownerDocument == null ?
    //  aNode.documentElement : aNode.ownerDocument.documentElement);
    var aresolver = Casper.XPath.createNSResolver(aNode);
    //aresolver.lookupNamespaceURI("xul");
    result = xpe.evaluate(aExpr, aNode, aresolver, type, null);
    
    Casper.XPath.log.debug("evaluateXPath result type "+result.resultType);
    switch(result.resultType) {
    case XPathResult.NUMBER_TYPE:
        return result.numberValue;
    case XPathResult.STRING_TYPE:
        return result.stringValue;
    case XPathResult.BOOLEAN_TYPE:
        return result.booleanValue;
    default:
        var found = [];
        var res = result.iterateNext();
        while (res) {
          found.push(res);
          res = result.iterateNext();
        }
        if (found.length < 1) {
            Casper.XPath.log.debug("no result nodes found, try singleNodeValue");
            return [result.singleNodeValue];
        }
        return found;
    }
}
