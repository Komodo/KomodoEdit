try {
  dump("loading test_async.js\n");


function AsyncEventTest(name) {
  Casper.UnitTest.TestCaseAsync.apply(this, [name]);

  this.eventList =  [
    {"type":"mousedown",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "detail":1,
    "button":0,
    "isChar":false,
    "shiftKey":false,
    "ctrlKey":false,
    "altKey":false,
    "metaKey":false,
    "clientX":97,
    "clientY":40,
    "layerX":93,
    "layerY":8,
    "screenX":117,
    "screenY":104,
    "timeStamp":2224091094,
    "targetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabs[@id=\"project_toolbox_tabs\"]/xmlns:tab[@id=\"codebrowser_tab\"]",
    "currentTargetXPath":"/",
    "originalTargetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabs[@id=\"project_toolbox_tabs\"]/xmlns:tab[@id=\"codebrowser_tab\"]",
    "enabled":true,
    "action":"fire"}
    ,
  
    {"type":"mouseup",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "detail":1,
    "button":0,
    "isChar":false,
    "shiftKey":false,
    "ctrlKey":false,
    "altKey":false,
    "metaKey":false,
    "clientX":97,
    "clientY":40,
    "layerX":93,
    "layerY":8,
    "screenX":117,
    "screenY":104,
    "timeStamp":2224091487,
    "targetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabs[@id=\"project_toolbox_tabs\"]/xmlns:tab[@id=\"codebrowser_tab\"]",
    "currentTargetXPath":"/",
    "originalTargetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabs[@id=\"project_toolbox_tabs\"]/xmlns:tab[@id=\"codebrowser_tab\"]",
    "enabled":true,
    "action":"fire"}
    ,
  
    {"type":"focus",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "timeStamp":0,
    "target":null,
    "targetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"codebrowserviewbox\"]/xmlns:vbox[@id=\"codebrowserview-vbox\"]/xmlns:vbox[@id=\"codebrowser-tree-vbox\"]/xmlns:tree[@id=\"codebrowser-tree\"]",
    "currentTarget":null,
    "currentTargetXPath":"/",
    "originalTarget":null,
    "originalTargetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"project_toolbox_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"codebrowserviewbox\"]/xmlns:vbox[@id=\"codebrowserview-vbox\"]/xmlns:vbox[@id=\"codebrowser-tree-vbox\"]/xmlns:tree[@id=\"codebrowser-tree\"]",
    "enabled":true,
    "action":"fire"}

    ];
}
AsyncEventTest.prototype = new Casper.UnitTest.TestCaseAsync();
AsyncEventTest.prototype.constructor = AsyncEventTest;
AsyncEventTest.prototype.setup = function() {
    // make sure the project pane is open, and the project tab is selected
    uilayout_toggleTab('project_tab');
}
AsyncEventTest.prototype.test_async = function() {
    var self = this;
    var test = new Casper.Events.test(window);
    test.complete = function(e) {
        self.complete_async(e);
    };
    test.eventList = this.eventList;
    test.replay();
}
AsyncEventTest.prototype.complete_async = function(ex) {
    // assert the state of something
    try {
      if (ex) {
          this.result.fails(ex.message, ex);
      } else {
          this.assertEqual(document.commandDispatcher.focusedElement, document.getElementById('codebrowser-tree'),
                           document.commandDispatcher.focusedElement.nodeName +" != "+document.getElementById('codebrowser-tree').nodeName);
          this.result.passes();
      }
    } catch(ex if ex instanceof Casper.UnitTest.AssertException) {
        this.result.fails(ex.message, ex);
    } catch(ex) {
        this.result.breaks(ex);
    } finally {
      this.testComplete();
    }
}
// we do not pass an instance of MyTestCase, they are created in MakeSuite
Casper.UnitTest.testRunner.add(Casper.UnitTest.MakeSuite("Async Event Test", AsyncEventTest));

} catch(e) {
    var CasperLog = Casper.Logging.getLogger("Casper::global");
    CasperLog.exception(e);
}

