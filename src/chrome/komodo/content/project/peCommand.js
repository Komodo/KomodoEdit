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

// The "command" project extension.
//
// This extension manages "run command" project entries.
//

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {

this.commandProperties = function command_editProperties(item)
{
    var obj = new Object();
    obj.part = item;
    window.openDialog(
        "chrome://komodo/content/run/commandproperties.xul",
        "Komodo:CommandProperties",
        "chrome,close=yes,dependent=yes,modal=yes,centerscreen",
        obj);
}

this.runCommand = function Run_CommandPart(cmdPart) {
    // Have to guard against new (since Komodo 2.0.0 release) command
    // attributes not being defined.
    var parseOutput = null;
    if (cmdPart.hasAttribute("parseOutput")) {
        parseOutput = cmdPart.getBooleanAttribute("parseOutput");
    }
    var parseRegex = null;
    if (cmdPart.hasAttribute("parseRegex")) {
        parseRegex = cmdPart.getStringAttribute("parseRegex");
    }
    var showParsedOutputList = null;
    if (cmdPart.hasAttribute("showParsedOutputList")) {
        showParsedOutputList = cmdPart.getBooleanAttribute("showParsedOutputList");
    }
    var clearOutputWindow = true;
    var terminationCallback = null;
    var saveInMRU = true;
    var saveInMacro = false;
    var viewData = {};
    viewData.prefSet = cmdPart.prefset;
    ko.run.runCommand(
        window,
        cmdPart.value,
        cmdPart.getStringAttribute("cwd"),
        stringutils_unescapeWhitespace(cmdPart.getStringAttribute("env"), '\n'),
        cmdPart.getBooleanAttribute("insertOutput"),
        cmdPart.getBooleanAttribute("operateOnSelection"),
        cmdPart.getBooleanAttribute("doNotOpenOutputWindow"),
        cmdPart.getStringAttribute("runIn"),
        parseOutput,
        parseRegex,
        showParsedOutputList,
        cmdPart.getStringAttribute("name"),
        clearOutputWindow,
        terminationCallback,
        saveInMRU,
        saveInMacro,
        viewData
    );
    ko.macros.recordPartInvocation(cmdPart);
}

}).apply(ko.projects);

// setTimeout in case projectManager.p.js hasn't been loaded yet.
setTimeout(function() {
ko.projects.addDeprecatedGetter("peCommand_addCommand", "addCommand");
ko.projects.addDeprecatedGetter("command_editProperties", "commandProperties");
ko.projects.addDeprecatedGetter("Run_CommandPart", "runCommand");
ko.views.addDeprecatedGetter('ko.projects.addCommand', 'toolbox2', 'add_command');
    }, 1);

