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
    "targetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"workspace_left_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabs[@id=\"project_toolbox_tabs\"]/xmlns:tab[@paneid=\"codebrowserviewbox\"]",
    "currentTargetXPath":"/",
    "originalTargetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"workspace_left_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabs[@id=\"project_toolbox_tabs\"]/xmlns:tab[@paneid=\"codebrowserviewbox\"]",
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
    "targetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"workspace_left_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabs[@id=\"project_toolbox_tabs\"]/xmlns:tab[@paneid=\"codebrowserviewbox\"]",
    "currentTargetXPath":"/",
    "originalTargetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"workspace_left_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabs[@id=\"project_toolbox_tabs\"]/xmlns:tab[@paneid=\"codebrowserviewbox\"]",
    "enabled":true,
    "action":"fire"}
    ,
  
    {"type":"focus",
    "eventPhase":1,
    "bubbles":true,
    "cancelable":true,
    "timeStamp":0,
    "target":null,
    "targetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"workspace_left_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"codebrowserviewbox\"]/xmlns:vbox[@id=\"codebrowserview-vbox\"]/xmlns:vbox[@id=\"codebrowser-tree-vbox\"]/xmlns:tree[@id=\"codebrowser-tree\"]",
    "currentTarget":null,
    "currentTargetXPath":"/",
    "originalTarget":null,
    "originalTargetXPath":"/xmlns:window[@id=\"jaguar_main\"]/xmlns:deck[1]/xmlns:vbox[@id=\"komodo-vbox\"]/xmlns:hbox[@id=\"komodo-hbox\"]/xmlns:vbox[@id=\"workspace_left_area\"]/xmlns:tabbox[@id=\"leftTabBox\"]/xmlns:tabpanels[@id=\"project_toolbox_tabpanels\"]/xmlns:tabpanel[@id=\"codebrowserviewbox\"]/xmlns:vbox[@id=\"codebrowserview-vbox\"]/xmlns:vbox[@id=\"codebrowser-tree-vbox\"]/xmlns:tree[@id=\"codebrowser-tree\"]",
    "enabled":true,
    "action":"fire"}

    ];
}
AsyncEventTest.prototype = new Casper.UnitTest.TestCaseAsync();
AsyncEventTest.prototype.constructor = AsyncEventTest;
AsyncEventTest.prototype.setup = function() {
    // make sure the project pane is open, and the project tab is selected
    ko.uilayout.ensureTabShown('placesViewbox');
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

