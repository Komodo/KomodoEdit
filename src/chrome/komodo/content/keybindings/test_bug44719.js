try {
//dump("Loading test_bug44719.js...\n");

// XXX bug doesn't happen when we dont drag/drop

// example of setting up a class based test case
function test_keybindings_bug44719() {
  // The name supplied must be the same as the class name!!
  Casper.UnitTest.TestCaseSerialClassAsync.apply(this, ["test_keybindings_bug44719"]);
}
test_keybindings_bug44719.prototype = new Casper.UnitTest.TestCaseSerialClassAsync();
test_keybindings_bug44719.prototype.constructor = test_keybindings_bug44719;

test_keybindings_bug44719.prototype.setup = function() {
  ko.projects.active = ko.toolboxes.user.viewMgr;
  this.folderName = 'bug 44719 test folder';
  var folder = ko.toolboxes.user.findItemByAttributeValue('name', this.folderName);
  this.assertNull(folder, 'keybinding test folder already exists');
  
  ko.projects.addFolder(this.folderName, ko.toolboxes.user.viewMgr.view.toolbox);
  folder = ko.toolboxes.user.findItemByAttributeValue('name', this.folderName);
  this.assertNotNull(folder, 'could not retrieve folder');
  var index = ko.toolboxes.user.viewMgr.view.getIndexByPart(folder);
  //dump("folder index is "+index+"\n");
  
  this.snippetName = 'bug 44719 test snippet';
  var item = ko.toolboxes.user.findItemByAttributeValue('name', this.snippetName);
  this.assertNull(item, 'keybinding test snippet already exists');

  var snippet = ko.projects.addSnippetFromText(this.snippetName, item);
  this.assertEqual(ko.projects.findPartById(snippet.id),snippet,"Could not create test snippet");

  this.snippetExecuted = false;
}

test_keybindings_bug44719.prototype.tearDown = function() {
    var item = ko.toolboxes.user.findItemByAttributeValue('name', this.folderName);
    if (item)
        ko.toolboxes.user.removeItem(item, true);
    item = ko.toolboxes.user.findItemByAttributeValue('name', this.snippetName);
    if (item)
        ko.toolboxes.user.removeItem(item, true);
}

test_keybindings_bug44719.prototype.test_toggleFolderOpen = function() {
  var folder = ko.toolboxes.user.findItemByAttributeValue('name', this.folderName);
  var index = ko.toolboxes.user.viewMgr.view.getIndexByPart(folder);
  ko.toolboxes.user.viewMgr.view.toggleOpenState(index);
  this.assertTrue(ko.toolboxes.user.viewMgr.view.isContainerOpen(index),"Folder did not open");
}

test_keybindings_bug44719.prototype.test_addKeyBinding = function() {
    var item = ko.toolboxes.user.findItemByAttributeValue('name', this.snippetName);
    this.assertNotNull(item , 'could not find snippet!');
    var cmd = "cmd_callPart";
    var keylabel = "Ctrl+K, B";
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

test_keybindings_bug44719.prototype.test_movesnippetOutOfFolder = function() {
    // this tests whether a binding is reapplied when an item is out of a folder
    // move the snippet into a folder
    var cmd = "cmd_callPart";
    var keylabel = "Ctrl+K, B";
    var snippet = ko.toolboxes.user.findItemByAttributeValue('name', this.snippetName);
    this.assertNotNull(snippet , 'could not find snippet!');
    var commandParam = snippet.id;

    // assert the keybinding exists
    var seqList = gKeybindingMgr.command2keysequences(cmd, commandParam);
    this.assertFalse(seqList.length == 0,"item does not have a binding!");

    var newpart = snippet.clone();
    
    ko.toolboxes.user.removeItem(snippet,true);
    // assert the keybinding doesn't exist
    seqList = gKeybindingMgr.command2keysequences(cmd)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "item bindings did not get removed");

    ko.toolboxes.user.addItem(newpart);
    // assert the keybinding exists
    commandParam = newpart.id;
    seqList = gKeybindingMgr.command2keysequences(cmd, commandParam);
    this.assertFalse(seqList.length == 0,"bindings on new part did not get applied");
}

test_keybindings_bug44719.prototype.test_movesnippetIntoFolder = function() {
    // this tests whether a binding is reapplied when an item is moved into a folder
    // move the snippet into a folder
    var cmd = "cmd_callPart";
    var keylabel = "Ctrl+K, B";
    var snippet = ko.toolboxes.user.findItemByAttributeValue('name', this.snippetName);
    this.assertNotNull(snippet , 'could not find snippet!');
    var commandParam = snippet.id;
    var folder = ko.toolboxes.user.findItemByAttributeValue('name', this.folderName);
    this.assertNotNull(folder , 'could not find folder!');
    var index = ko.toolboxes.user.viewMgr.view.getIndexByPart(folder);
    //ko.toolboxes.user.viewMgr.view.toggleOpenState(index);

    // assert the keybinding exists
    var seqList = gKeybindingMgr.command2keysequences(cmd, commandParam);
    this.assertFalse(seqList.length == 0,"item does not have a binding!");

    var newpart = snippet.clone();
      
    ko.toolboxes.user.removeItem(snippet,true);
    // assert the keybinding doesn't exist
    seqList = gKeybindingMgr.command2keysequences(cmd)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "item bindings did not get removed");
    
    ko.toolboxes.user.addItem(newpart, folder);
    // assert the keybinding exists
    commandParam = newpart.id;
    seqList = gKeybindingMgr.command2keysequences(cmd, commandParam);
    this.assertFalse(seqList.length == 0,"bindings on new part did not get applied");
}

test_keybindings_bug44719.prototype.test_removeChildBindings = function() {
    // this tests whether keybindings of children are recursivly removed when
    // we remove a folder that has children with bindings
    
    var snippet = ko.toolboxes.user.findItemByAttributeValue('name', this.snippetName);
    this.assertNotNull(snippet , 'could not find snippet!');
    var commandParam = snippet.id;
    // we remove the folder, the child bindings should also be removed
    var folder = ko.toolboxes.user.findItemByAttributeValue('name', this.folderName);
    this.assertNotNull(folder , 'could not find folder!');
    ko.toolboxes.user.removeItem(folder, true);

    var cmd = "cmd_callPart";
    var keylabel = "Ctrl+K, B";
    
    // assert the snippet is removed from the toolbox
    snippet = ko.toolboxes.user.findItemByAttributeValue('name', this.snippetName);
    this.assertNull(snippet, "snippet did not get deleted with folder");
    
    // assert our binding no longer exists
    seqList = gKeybindingMgr.command2keysequences(cmd)
    this.assertFalse(seqList.indexOf(keylabel) >= 0, "item bindings did not get removed");

    // assert our binding no longer exists
    var seqList = gKeybindingMgr.command2keysequences(cmd, commandParam);
    this.assertTrue(seqList.length == 0,"the binding still exists after removing the snippet!");
}

// we do not pass an instance of MyTestCase, they are created in MakeSuite
var kbBug44719 = new test_keybindings_bug44719();
var suite = new Casper.UnitTest.TestSuite("Bug 44719");
suite.add(kbBug44719);
Casper.UnitTest.testRunner.add(suite);

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}
