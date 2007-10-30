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
// Use this sample to explore editing JavaScript with Komodo.

var myStr = "123";

// JavaScript Code Intelligence notes:
// * automatically triggers on a "." or a "(" character
// * you can use Ctrl-J (Cmd-J on Mac) to force a completion trigger

// You can enter a "." after the variable name "myStr" to trigger
// JavaScript code completion, in this case a list of string object
// methods for myStr, such as concat, indexOf etc...
myStr.toLowerCase();

// When entering "(" for a function call, like "parseInt(", Komodo
// shows a calltip for that function, in this case it's for a
// built-in JavaScript function.
var i = parseInt(myStr);

// Defining a function/class so we can see class completion later
function MyCommand(cmd, args) {
    this.cmd = cmd;
    this.args = args;
    this.result = 0;
}
MyCommand.prototype.toString = function() {
    return "Cmd: " + this.cmd + "('" + arguments.join("', '") + "')";
}
MyCommand.prototype.run = function() {
    return true;
}

// Creating an object instance
var mycmd = new MyCommand("alert", "Hello there");

// When entering a "." after an object instance, like "mycmd",
// Komodo shows the class completions defined, such as those
// from MyCommand above.
mycmd.run();

var s = mycmd.toString();

// Komodo will also knows about function return types, so entering
// a "." after the "s" will show completions for the return type of
// toString, which in this case is a String.
s.length;


// Komodo also supports JSDoc (JavaScript documentation) comments,
// which can be used to provide additional information for calltips,
// argument types, return types, etc... See the sample below.
// See: http://jsdoc.sourceforge.net/#tagref

/**
 * Run the command from the supplied directory (the calltip shown).
 * @param directory {RegExp} Local directory to be run from
 * @returns {bool}
 */
MyCommand.prototype.runInDirectory = function(directory) {
    // Directory is set as a String type, from the jsdoc
    // "@param" above, so we will get string completions
    // Changing the type in curly braces (i.e. Int, RegExp)
    // will change the completions given for directory below
    var c = directory.charAt(0);
}
// You can see the custom calltip when you hit "(" for the start
// of the function call
mycmd.runInDirectory("/tmp");


// Code Folding: Click the "-" and "+" symbols in the left margin
// to collapse and expand blocks

// Syntax Coloring: Language elements are colored according to the
// Fonts and Colors preference.

// Background Syntax Checking:
//   - Syntax errors are underlined in red.
//   - Syntax warnings are underlined in green.
//   - Position the cursor over the underline to view the error or
//     warning message.

// Code Browsing:
//   - The Code tab in the pane to the left shows a tree view of the
//     elements of code in this sample.
//   - Click any element to jump to the the relevant point in the code

// More: Press 'F1' to view the Komodo User Guide.
