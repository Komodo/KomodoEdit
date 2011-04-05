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

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {
var _log = ko.logging.getLogger('peURL');

this.URLProperties = function peURL_editProperties(/*koIPart*/ item)
{
    var obj = new Object();
    obj.item = item;
    obj.task = 'edit';
    obj.imgsrc = 'chrome://komodo/skin/images/xlink.png';
    obj.type = 'url';
    obj.prettytype = 'URL';
    window.openDialog(
        "chrome://komodo/content/project/simplePartProperties.xul",
        "Komodo:URLProperties",
        "chrome,centerscreen,close=yes,dependent=yes,modal=yes,resizable=yes", obj);
}

this.addURLFromText = function peURL_addURL(URLtext, /*koITool*/ parent) {
    if (typeof(parent) == 'undefined' || !parent)
        parent = ko.toolbox2.getStandardToolbox();
    try {
        var uriTool = ko.toolbox2.createPartFromType('URL');
        uriTool.type = 'URL';
        var name = URLtext;
        var value = URLtext;
        if (URLtext.search("\n")) {
            var s = URLtext.split("\n");
            name = typeof(s[1])!='undefined'?s[1]:s[0];
            value = s[0];
        }
        uriTool.setStringAttribute('name', name);
        uriTool.value = value;
        ko.toolbox2.addItem(uriTool, parent);
        //dump("leaving AddURL\n");
    } catch (e) {
        _log.exception(e);
    }
}

this.addURL = function peURL_newURL(/*koIPart|koITool*/ parent,
                                    /*koIPart|koITool = null */ part )
{
    if (typeof(part) == "undefined") {
        part = parent.project.createPartFromType('snippet');
    }
    part.setStringAttribute('name', 'New URL');
    part.value = '';
    var obj = new Object();
    obj.item = part;
    obj.task = 'new';
    obj.imgsrc = 'chrome://komodo/skin/images/xlink.png';
    obj.type = 'url';
    obj.prettytype = 'URL';
    obj.parent = parent;
    window.openDialog(
        "chrome://komodo/content/project/simplePartProperties.xul",
        "Komodo:URLProperties",
        "chrome,centerscreen,close=yes,modal=yes,resizable=yes", obj);
}

}).apply(ko.projects);
