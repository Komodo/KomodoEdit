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
dump("Loading test_kbmanager.js...\n");

// example of setting up a class based test case
function test_keybindings_manager() {
  // The name supplied must be the same as the class name!!
  Casper.UnitTest.TestCaseSerialClassAsync.apply(this, ["test_keybindings_manager"]);
  this.kbConfigName = "unittest bindings";
}
test_keybindings_manager.prototype = new Casper.UnitTest.TestCaseSerialClassAsync();
test_keybindings_manager.prototype.constructor = test_keybindings_manager;

test_keybindings_manager.prototype.setup = function() {
  this.kbm = new ko.keybindings.manager();
  this.originalConfigName = this.kbm.currentConfiguration;
  this.prefset = Components.classes["@activestate.com/koPreferenceSet;1"]
      .createInstance(Components.interfaces.koIPreferenceSet);
}
test_keybindings_manager.prototype.tearDown = function() {
  // some just-in-case cleanup
  if (this.kbm._configKnown(this.kbConfigName)) {
      if (this.originalConfigName != this.kbm.currentConfiguration) {
          this.kbm.switchConfiguration(this.originalConfigName, this.prefset);
      }
      this.kbm.deleteConfiguration(this.kbConfigName, this.prefset);
  }
}

test_keybindings_manager.prototype.test_loadConfiguration = function() {
  this.kbm.loadConfiguration(this.kbm.currentConfiguration);
  this.assertNotUndefined(this.kbm._configKeyTree, "Config failed to load");
}

test_keybindings_manager.prototype.test_makeConfiguration = function() {
  // create a new prefset, and make a new configuration
  this.assertFalse(this.kbm._configKnown(this.kbConfigName), "Config already exists");
  this.kbm.makeNewConfiguration(this.kbConfigName, this.prefset);
  this.assertTrue(this.kbm._configKnown(this.kbConfigName), "Config was not created");
}

test_keybindings_manager.prototype.test_switchConfiguration = function() {
  this.kbm.switchConfiguration(this.kbConfigName, this.prefset);
  this.assertEquals(this.kbConfigName, this.kbm.currentConfiguration, "Could not switch to the new configuration");
}

test_keybindings_manager.prototype.test_usedBy = function() {
    var cmd = "cmd_copy";
    var keyname = this.kbm.command2keylabel(cmd);
    var usedbys = this.kbm.usedBy(keyname.split(', '));
    var commandname = null;
    for (var i in usedbys) {
        commandname = usedbys[i].command;
        if (commandname == cmd) break;
    }
    this.assertEquals(cmd, commandname, "usedBy failed to find "+cmd);
}

test_keybindings_manager.prototype.test_keysequence2keylabel = function() {
    var key = "Ctrl+K, Ctrl+L";
    var seq = ["Ctrl+K", "Ctrl+L"];
    this.assertEquals(keysequence2keylabel(seq), key, "keysequence2keylabel failed "+key);
    this.assertEquals(ko.keybindings.keylabel2keysequence(key), seq, "keylabel2keysequence failed "+key);
    key = "Ctrl+C";
    seq = ["Ctrl+C"];
    this.assertEquals(keysequence2keylabel(seq), key, "keysequence2keylabel failed "+key);
    this.assertEquals(ko.keybindings.keylabel2keysequence(key), seq, "keylabel2keysequence failed "+key);
    var key = "Ctrl+K, Ctrl+L, Ctrl+M, Ctrl+N";
    var seq = ["Ctrl+K", "Ctrl+L", "Ctrl+M", "Ctrl+N"];
    this.assertEquals(keysequence2keylabel(seq), key, "keysequence2keylabel failed "+key);
    var seqresult = ko.keybindings.keylabel2keysequence(key);
    this.assertEquals(seqresult, seq, "keylabel2keysequence failed "+key+ " != "+seqresult);
}

test_keybindings_manager.prototype.test_assignKey_MultiKey = function() {
    var cmd = "cmd_copy";
    var keylabel = "Ctrl+K, Ctrl+O, Ctrl+P, Ctrl+Y";
    var keysequence = ko.keybindings.keylabel2keysequence(keylabel);
    var seqList = this.kbm.command2keysequences(cmd)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "test key sequence already exists");
    this.kbm.assignKey(cmd, keysequence);
    seqList = this.kbm.command2keysequences(cmd)
    this.assertTrue(seqList.indexOf(keylabel) >= 0, "assignKey failed");
}

test_keybindings_manager.prototype.test_clearSequence_MultiKey = function() {
    var cmd = "cmd_copy";
    var keylabel = "Ctrl+K, Ctrl+O, Ctrl+P, Ctrl+Y";
    var keysequence = ko.keybindings.keylabel2keysequence(keylabel);
    
    var seqList = this.kbm.command2keysequences(cmd)
    this.assertTrue(seqList.indexOf(keylabel) >= 0, "test key sequence does not exist yet");

    this.kbm.clearSequence(cmd, keylabel, false);

    // ensure the command is no longer tied to the sequence
    var seqList = this.kbm.command2keysequences(cmd)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "test key sequence did not get removed");

    // ensure that the keytree no longer has this sequence
    var root = this.kbm._getKeyTreeRoot(keysequence);
    this.assertNotEqual(root[keysequence[keysequence.length-1]], cmd, "keytree still has keysequence!");
}

test_keybindings_manager.prototype.test_saveCurrentConfiguration = function() {
  this.assertTrue(this.kbm._configDirty, "Config is not dirty, cannot test save");
  this.kbm.saveCurrentConfiguration();
  this.assertFalse(this.kbm._configDirty, "Config was not saved correctly, configuration is still dirty");
}

test_keybindings_manager.prototype.test_upgradeConfiguration = function() {
  var scheme_data_v1 = [
      "version 1",
      "binding cmd_vim_dedent < <",
      "binding cmd_vim_indent > >",
      "binding cmd_bufferNextMostRecent Ctrl+F6",
      "binding cmd_bufferNextLeastRecent Ctrl+Shift+F6"
  ];
  // Setup the config from data above
  this.kbm.currentScheme.data = scheme_data_v1.join("\n");
  this.kbm.loadConfiguration(this.kbConfigName, true /* forced reload */);

  var added_commands = {
        "cmd_vim_dedentOperation":   [ "<" ],
        "cmd_vim_indentOperation":   [ ">" ],
        "cmd_bufferNextMostRecent":  [ "Ctrl+Tab" ],
        "cmd_bufferNextLeastRecent": [ "Ctrl+Shift+Tab" ]
  };
  var removed_commands = [ "cmd_vim_dedent", "cmd_vim_indent" ];

  var i;
  var cmd;
  var matched;
  var keymapping;
  // Test keybindings that were added
  for (cmd in added_commands) {
    matched = false;
    keymapping = this.kbm.command2keysequences(cmd);
    for (i=0; i < keymapping.length; i++) {
      if (keymapping[i] == added_commands[cmd][0]) {
        matched = true;
        break;
      }
    }
    this.assertTrue(matched, "Keybinding was not added by upgrade process: '" +
                    cmd + "'");
  }
  // Test keybindings that were removed
  for (i=0; i < removed_commands.length; i++) {
    cmd = removed_commands[i];
    this.assertEqual(this.kbm.command2keylabel(cmd), "",
                     "Keybinding was not removed by upgrade '" + cmd + "'");
  }

  // Test keybinding upgrade doesn't add a keybinding when the keybind already
  // exists for another command
  this.kbm._add_keybinding_sequences({ "cmd_copy":   [ "<" ] });
  this.assertEqual(this.kbm.command2keylabel("cmd_copy"), "",
                   "Keybinding upgrade incorrectly overwrote existing keybind");
}

test_keybindings_manager.prototype.test_switchBackConfiguration = function() {
  this.kbm.switchConfiguration(this.originalConfigName, this.prefset);
  this.assertEquals(this.originalConfigName, this.kbm.currentConfiguration, "Could not switch to the original configuration");
}

test_keybindings_manager.prototype.test_deleteConfiguration = function() {
  this.kbm.deleteConfiguration(this.kbConfigName, this.prefset);
  this.assertFalse(this.kbm._configKnown(this.kbConfigName), "Config still exists");
}

// we do not pass an instance of MyTestCase, they are created in MakeSuite
var suite = new Casper.UnitTest.TestSuite("Keybindings Manager");
suite.add(new test_keybindings_manager());
Casper.UnitTest.testRunner.add(suite);

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}
