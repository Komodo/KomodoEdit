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

try {
dump("Loading test_bindings.js...\n");

// the idea of this test is to read all the bindings loaded, and execute events
// for each one to test if we get back the same command that the binding is
// set for.  This should show that the binding system is working from the
// aspect of turning events into a command.

// to prevent komodo running a bunch of stuff, we override the actual
// command handler during this test

// example of setting up a class based test case
function test_keybindings_bindings() {
    // The name supplied must be the same as the class name!!
    Casper.UnitTest.TestCaseSerialClass.apply(this, ["test_keybindings_bindings"]);
}
test_keybindings_bindings.prototype = new Casper.UnitTest.TestCaseSerialClass();
test_keybindings_bindings.prototype.constructor = test_keybindings_bindings;

test_keybindings_bindings.prototype.setup = function() {
    // ensure all files are closed
    // create a macro with a keybinding
    // prevent commands executing during this test
    this._evalCommand = ko.keybindings.manager.evalCommand;
    var self = this;
    ko.keybindings.manager.evalCommand = function(event, commandname, keylabel) {
        self.evalCommand(event, commandname, keylabel);
        return true;
    };
}
test_keybindings_bindings.prototype.tearDown = function() {
    ko.keybindings.manager.evalCommand = this._evalCommand;
    // remove the macro
}
test_keybindings_bindings.prototype.evalCommand = function(event, commandname, keylabel)
{
    //dump("evalCommand "+commandname+" = "+keylabel+"\n");
    this.commandFound = true;
}

test_keybindings_bindings.prototype.key2code = function(key)
{
    for (var i in ko.keybindings.VKCodes) {
        if (key == ko.keybindings.VKCodes[i])
            return i;
    }
    return 0;
}
test_keybindings_bindings.prototype.key2event = function(seq)
{
    var events = [];
    for (var i in seq) {
        var p = seq[i].split('+');
        var key = p.pop();
        if (!key) {
            key = "+";
        }
        var keycode = this.key2code(key);
        var charcode = 0;
        if (!keycode) {
            charcode = key.charCodeAt(0);
        }
        var shift = seq[i].indexOf('Shift') >= 0;
        var alt = seq[i].indexOf('Alt') >= 0;
        var ctrl = seq[i].indexOf('Ctrl') >= 0;
        var meta = seq[i].indexOf('Meta') >= 0;
        //dump("    key "+seq[0]+" charcode "+charcode+" keycode "+keycode+" ctrl "+ctrl+" alt "+alt+" meta "+meta+" shift "+shift+"\n");
        // create an event object with the necessary parts
        var event = document.createEvent("KeyEvents");
        event.initKeyEvent("keypress", false, true,
                           document.defaultView,
                           ctrl, 
                           alt,
                           shift,
                           meta,
                           keycode,
                           charcode);
        events.push(event);
    }
    return events;
}

test_keybindings_bindings.prototype.test_loadConfiguration = function() {
    for (var command in ko.keybindings.manager.command2key) {
        if (command in ko.keybindings.manager._commandParams)
            continue;
        var keys = ko.keybindings.manager.command2keysequences(command);
        
        for (var k in keys) {
            var seq = ko.keybindings.keylabel2keysequence(keys[k]);
            //dump("command "+command+" = "+keys[k]+"\n");
            var events = this.key2event(seq);
            //dump("  events created :"+events.length+"\n");
            if (events.length == 1) {
                var found = false;
                //ko.logging.dumpEvent(event);
                // see if we get back what we want
                var bindings = ko.keybindings.manager.eventBindings(events[0]);
                for (var b in bindings) {
                  //dump("    binding "+bindings[b]+"\n");
                  var key2command = ko.keybindings.manager.key2command[bindings[b]];
                  //dump("    key "+seq+" command "+key2command+"\n");
                  found = key2command == command;
                }
                this.assertTrue(found, "binding "+keys[k]+" did not resolve to command "+command);
            }
            if (events.length > 0) {
                this.commandFound = false;
                for (var i=0; i < events.length; i++) {
                    this.assertFalse(this.commandFound, "command found prior to end of key combo!");
                    ko.keybindings.manager.keypressHandler(events[i]);
                }
                //dump("  key found? "+this.commandFound+"\n");
                this.assertTrue(this.commandFound, "binding "+keys[k]+" did not resolve to command "+command);
            }
        }
    }
}

// we do not pass an instance of MyTestCase, they are created in MakeSuite
var suite = new Casper.UnitTest.TestSuite("Bindings");
suite.add(new test_keybindings_bindings());
Casper.UnitTest.testRunner.add(suite);

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}
