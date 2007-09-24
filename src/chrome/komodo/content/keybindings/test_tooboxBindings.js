try {
dump("Loading test_kbmanager.js...\n");


// example of setting up a class based test case
function test_keybindings_toolbox() {
  // The name supplied must be the same as the class name!!
  Casper.UnitTest.TestCaseSerialClassAsync.apply(this, ["test_keybindings_toolbox"]);

  this.eventList1 = 

  [
    {"type":"keypress",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "detail":0,
    "isChar":false,
    "charCode":107,
    "shiftKey":false,
    "ctrlKey":true,
    "altKey":false,
    "keyCode":0,
    "metaKey":false,
    "layerX":0,
    "layerY":0,
    "timeStamp":3528496864,
    "target":null,
    "targetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"projectviewbox\"]/xmlns:vbox[@id=\"projectview-vbox\"]/xmlns:partviewer[@id=\"projectview\"]",
    "currentTarget":null,
    "currentTargetXPath":"/",
    "originalTarget":null,
    "originalTargetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"projectviewbox\"]/xmlns:vbox[@id=\"projectview-vbox\"]/xmlns:partviewer[@id=\"projectview\"]/anonymousChild()[0]/./xul:tree[@id=\"project-tree\"]",
    "enabled":true,
    "action":"fire",
    "waitTimeout":3000}
    ,
  
    {"type":"keypress",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "detail":0,
    "isChar":false,
    "charCode":98,
    "shiftKey":false,
    "ctrlKey":true,
    "altKey":false,
    "keyCode":0,
    "metaKey":false,
    "layerX":0,
    "layerY":0,
    "timeStamp":3528498053,
    "target":null,
    "targetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"projectviewbox\"]/xmlns:vbox[@id=\"projectview-vbox\"]/xmlns:partviewer[@id=\"projectview\"]",
    "currentTarget":null,
    "currentTargetXPath":"/",
    "originalTarget":null,
    "originalTargetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"projectviewbox\"]/xmlns:vbox[@id=\"projectview-vbox\"]/xmlns:partviewer[@id=\"projectview\"]/anonymousChild()[0]/./xul:tree[@id=\"project-tree\"]",
    "enabled":true,
    "action":"fire",
    "waitTimeout":3000}
    ]
  ;
  this.eventList2 = 
  [
    {"type":"keypress",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "detail":0,
    "isChar":false,
    "charCode":107,
    "shiftKey":false,
    "ctrlKey":true,
    "altKey":false,
    "keyCode":0,
    "metaKey":false,
    "layerX":0,
    "layerY":0,
    "timeStamp":3586573730,
    "target":null,
    "targetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"projectviewbox\"]/xmlns:vbox[@id=\"projectview-vbox\"]/xmlns:partviewer[@id=\"projectview\"]",
    "currentTarget":null,
    "currentTargetXPath":"/",
    "originalTarget":null,
    "originalTargetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"projectviewbox\"]/xmlns:vbox[@id=\"projectview-vbox\"]/xmlns:partviewer[@id=\"projectview\"]/anonymousChild()[0]/./xul:tree[@id=\"project-tree\"]",
    "enabled":true,
    "action":"fire",
    "waitTimeout":3000}
    ,
  
    {"type":"keypress",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "detail":0,
    "isChar":false,
    "charCode":75,
    "shiftKey":false,
    "ctrlKey":false,
    "altKey":false,
    "keyCode":0,
    "metaKey":false,
    "layerX":0,
    "layerY":0,
    "timeStamp":3586574215,
    "target":null,
    "targetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"projectviewbox\"]/xmlns:vbox[@id=\"projectview-vbox\"]/xmlns:partviewer[@id=\"projectview\"]",
    "currentTarget":null,
    "currentTargetXPath":"/",
    "originalTarget":null,
    "originalTargetXPath":"/xmlns:window[@id=\"komodo_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"projectviewbox\"]/xmlns:vbox[@id=\"projectview-vbox\"]/xmlns:partviewer[@id=\"projectview\"]/anonymousChild()[0]/./xul:tree[@id=\"project-tree\"]",
    "enabled":true,
    "action":"fire",
    "waitTimeout":3000}
    ]
  ;
}
test_keybindings_toolbox.prototype = new Casper.UnitTest.TestCaseSerialClassAsync();
test_keybindings_toolbox.prototype.constructor = test_keybindings_toolbox;

test_keybindings_toolbox.prototype.setup = function() {
  var item = ko.toolboxes.user.findItemByAttributeValue('name', 'keybinding test macro');
  this.assertNull(item, 'keybinding test macro already exists');
  var part = this.createTestMacro();
  this.assertEqual(ko.projects.findPartById(part.id),part,"Could not create test macro");
  this.macroExecuted = false;
  // we need a new file for one of our tests, lets open one now
  this.view = gViewMgr.doNewView();
}
test_keybindings_toolbox.prototype.tearDown = function() {
  // some just-in-case cleanup
  var item = ko.toolboxes.user.findItemByAttributeValue('name', 'keybinding test macro');
  ko.toolboxes.user.removeItem(item, true);
  this.view.close();
}

test_keybindings_toolbox.prototype.createTestMacro = function() {
    var part = ko.toolboxes.user.toolbox.createPartFromType('macro');
    part.setStringAttribute('name', 'keybinding test macro');
    part.value = "kbToolboxTestCase.macroExecuted = true;";
    part.setBooleanAttribute('trigger_enabled', false);
    part.setStringAttribute('trigger', '');
    part.setLongAttribute('rank', 0);
    part.setBooleanAttribute('async', false);
    part.setStringAttribute('language', 'JavaScript');
    ko.toolboxes.user.addItem(part);
    return part;
}

test_keybindings_toolbox.prototype.test_toolbox_runMacro = function() {
    // just a quick test that the macro works
    this.assertFalse(this.macroExecuted, "macro was already executed?");
    var item = ko.toolboxes.user.findItemByAttributeValue('name', 'keybinding test macro');
    ko.projects.executeMacroById(item.id, false);
    this.assertTrue(this.macroExecuted, "macro was not executed");
    this.macroExecuted = false;
}

test_keybindings_toolbox.prototype.test_keybinding_toolboxMacro = function() {
    var item = ko.toolboxes.user.findItemByAttributeValue('name', 'keybinding test macro');
    var cmd = "cmd_callPart";
    var keylabel = "Ctrl+K, Ctrl+B";
    var commandParam = item.id;
    
    var seqList = gKeybindingMgr.command2keysequences(cmd, commandParam);
    this.assertTrue(seqList.length == 0,"command already has binding!");

    var keysequence = keylabel2keysequence(keylabel);
    seqList = gKeybindingMgr.command2keysequences(cmd)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "test key sequence already exists");
    
    gKeybindingMgr.assignKey(cmd, keysequence, commandParam);
    seqList = gKeybindingMgr.command2keysequences(cmd, commandParam)
    this.assertTrue(seqList.indexOf(keylabel) >= 0, "assignKey failed");
    
    gKeybindingMgr.makeKeyActive(cmd, keysequence);
    gKeybindingMgr.stashIn(item, keylabel);
    this.assertEqual(item.getStringAttribute('keyboard_shortcut'), keylabel, "keylabel was not stashed in part");
}

test_keybindings_toolbox.prototype.testAsync_keybinding_runToolboxMacro_FocusView = function() {
    this.macroExecuted = false;
    // place focus on the editor buffer
    this.view.setFocus();
    //dump("*** runToolboxMacro_FocusView\n");
    var self = this;
    var test = new Casper.Events.test(window);
    test.complete = function(e) {
        self.complete_runToolboxMacro(e, true);
    };
    test.eventList = this.eventList1;
    test.replay();
}

test_keybindings_toolbox.prototype.testAsync_keybinding_runToolboxMacro_FocusProjects = function() {
    this.macroExecuted = false;
    // place focus on project
    //ko.commands.doCommand('cmd_viewRightPane');
    ko.uilayout.toggleTab('project_tab', false);
    //dump("*** runToolboxMacro_FocusProjects\n");
    var self = this;
    var test = new Casper.Events.test(window);
    test.complete = function(e) {
        self.complete_runToolboxMacro(e, true);
    };
    test.eventList = this.eventList1;
    test.replay();
}

test_keybindings_toolbox.prototype.testAsync_keybinding_runToolboxMacro_FocusToolbox = function() {
    this.macroExecuted = false;
    // place focus on toolbox
    ko.uilayout.toggleTab('toolbox_tab', false);
    //dump("*** runToolboxMacro_FocusToolbox\n");
    var self = this;
    var test = new Casper.Events.test(window);
    test.complete = function(e) {
        self.complete_runToolboxMacro(e, true);
    };
    test.eventList = this.eventList1;
    test.replay();
}

test_keybindings_toolbox.prototype.complete_runToolboxMacro = function(e, expectedResult) {
    //dump("in complete_runToolboxMacro\n");
    try {
      if (e) {
          this.currentTest.result.fails(e.message, e);
          this.result.fails(e.message, e);
      } else {
          // Add final assertions here
          this.assertTrue(this.macroExecuted == expectedResult, "macro was not executed");
          this.currentTest.result.passes();
      }
    } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
        this.result.fails(ex.message, ex);
        this.currentTest.result.fails(ex.message, ex);
    } catch(ex) {
        this.result.breaks(ex);
        this.currentTest.result.breaks(ex);
    } finally {
      this.macroExecuted = false;
      this.runNext();
    }
}

test_keybindings_toolbox.prototype.test_changeKey_toolboxMacro = function() {
    var item = ko.toolboxes.user.findItemByAttributeValue('name', 'keybinding test macro');
    var cmd = "cmd_callPart";
    var keylabel = "Ctrl+K, K";
    var oldkeylabel = "Ctrl+K, Ctrl+B";
    var commandParam = item.id;
    var seqList = gKeybindingMgr.command2keysequences(cmd, commandParam);
    this.assertTrue(seqList.length != 0,"command does not have a binding!");
    
    gKeybindingMgr.clearSequence(cmd, oldkeylabel, false);
    // ensure the command is no longer tied to the sequence
    seqList = gKeybindingMgr.command2keysequences(cmd)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "test key sequence did not get removed");
    seqList = gKeybindingMgr.command2keysequences(cmd, commandParam)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "test key sequence did not get removed");
    
    var keysequence = keylabel2keysequence(keylabel);
    gKeybindingMgr.assignKey(cmd, keysequence, commandParam);
    seqList = gKeybindingMgr.command2keysequences(cmd, commandParam)
    this.assertEqual(keysequence2keylabel(seqList), keylabel, "assignKey failed");
}

test_keybindings_toolbox.prototype.testAsync_keybinding_runToolboxMacro_newBinding = function() {
    this.macroExecuted = false;
    //dump("in testAsync_keybinding_runToolboxMacro2\n");
    //dump("*** runToolboxMacro_newBinding\n");
    var self = this;
    var test = new Casper.Events.test(window);
    test.complete = function(e) {
        self.complete_runToolboxMacro(e, true);
    };
    test.eventList = this.eventList2;
    test.replay();
}

test_keybindings_toolbox.prototype.test_clearSequence_toolboxMacro = function() {
    var item = ko.toolboxes.user.findItemByAttributeValue('name', 'keybinding test macro');
    var commandParam = item.id;
    var cmd = "cmd_callPart";
    var keylabel = "Ctrl+K, K";
    var keysequence = keylabel2keysequence(keylabel);
    
    var seqList = gKeybindingMgr.command2keysequences(cmd, commandParam)
    this.assertTrue(seqList.indexOf(keylabel) >= 0, "test key sequence does not exist yet");

    gKeybindingMgr.clearSequence(cmd, keylabel, false);

    // ensure the command is no longer tied to the sequence
    var seqList = gKeybindingMgr.command2keysequences(cmd, commandParam)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "test key sequence did not get removed");

    // ensure that the keytree no longer has this sequence
    var root = gKeybindingMgr._getKeyTreeRoot(keysequence);
    this.assertNotEqual(root[keysequence[keysequence.length-1]], cmd, "keytree still has keysequence!");
}

test_keybindings_toolbox.prototype.testAsync_keybinding_runToolboxMacroExpectFail = function() {
    this.macroExecuted = false;
    //dump("in testAsync_keybinding_runToolboxMacro2\n");
    //dump("*** runToolboxMacroExpectFail\n");
    var self = this;
    var test = new Casper.Events.test(window);
    test.complete = function(e) {
        self.complete_runToolboxMacro(e, false);
    };
    test.eventList = this.eventList2;
    test.replay();
}

// we do not pass an instance of MyTestCase, they are created in MakeSuite
var kbToolboxTestCase = new test_keybindings_toolbox();
var suite = new Casper.UnitTest.TestSuite("Toolbox Keybindings");
suite.add(kbToolboxTestCase);
Casper.UnitTest.testRunner.add(suite);

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}
