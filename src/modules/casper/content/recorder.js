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

var recorder = null;

var log = Casper.Logging.getLogger("Recorder");
log.setLevel(Casper.Logging.DEBUG);

function recorder_onload() {
    try {
    recorder_fillEventsList();
    window.sizeToContent();
    } catch(e) { log.exception(e);}
}

function recorder_fillEventsList() {
    try {
    var list = document.getElementById('eventList');
    for (var eventName in Casper.Events.handler) {
        var item = list.appendItem ( eventName , eventName );
        item.setAttribute("id","event_"+eventName);
        item.setAttribute("type","checkbox");
        item.setAttribute("checked","true");
    }
    } catch(e) { log.exception(e);}
}

function recorder_start() {
    try {
        document.getElementById("recorder_tabbox").selectedTab = document.getElementById("tab_currentTest");
        recorder = new Casper.Events.recorder();
        recorder.currentTest = new Casper.Events.test(opener);
        recorder_set_results();
        var list = document.getElementById('eventList');
        var children = list.getElementsByTagName('listitem');
        for (var i = 0; i < children.length; i++) {
            if (children[i].checked)
                recorder.listener.addListener(children[i].getAttribute('label'));
        }
        recorder_listbox('resultsList');
        recorder.start(opener);
    } catch(e) { log.exception(e);}
}

function recorder_stop() {
    try {
    document.getElementById("recorder_tabbox").selectedTab = document.getElementById("tab_currentTest");
    recorder.stop(opener);
    recorder_set_results();
    } catch(e) { log.exception(e);}
}

function recorder_play() {
    try {
    document.getElementById("recorder_tabbox").selectedTab = document.getElementById("tab_currentTest");
    recorder.replay();
    } catch(e) { log.exception(e);}
}

function recorder_createUnitTest() {
    try {
    document.getElementById("recorder_tabbox").selectedTab = document.getElementById("tab_currentTest");
    recorder.currentTest.generate();
    } catch(e) { log.exception(e);}
}

function recorder_save(all) {
    try {
    document.getElementById("recorder_tabbox").selectedTab = document.getElementById("tab_currentTest");
    recorder.currentTest.save(all);
    } catch(e) { log.exception(e);}
}

function recorder_load() {
    try {
    document.getElementById("recorder_tabbox").selectedTab = document.getElementById("tab_currentTest");
    var r = new Casper.Events.recorder();
    r.currentTest = new Casper.Events.test(opener);
    r.currentTest.load();
    recorder = r;
    recorder_set_results();
    } catch(e) { log.exception(e);}
}

function recorder_showJSON() {
    var data = recorder.currentTest.getJSON(false);
    document.getElementById("json_value").value = data;
    document.getElementById("recorder_tabbox").selectedTab = document.getElementById("tab_json");
}

function recorder_testXpath() {
    document.getElementById("recorder_tabbox").selectedTab = document.getElementById("tab_xpathTest");
    document.getElementById("xpath_test_expression").setAttribute('value',document.getElementById("prop_value").getAttribute('value'));
    recorder_run_xpath_test();
}

function recorder_listbox(id) {
    var results = document.getElementById(id);
    var children = results.getElementsByTagName('listitem');
    while (children.length) {
        results.removeChild(children[0]);
    }
}

function recorder_onListItemKeypress(event) {
    if (event.charCode == event.DOM_VK_SPACE ||
              event.keyCode == event.DOM_VK_SPACE) {
      recorder_onListItemChange();
    } else
    if (event.keyCode == event.DOM_VK_RIGHT) {
        recorder_changeItemAction(true);
    } else
    if (event.keyCode == event.DOM_VK_LEFT) {
        recorder_changeItemAction(false);
    }
}

function recorder_changeItemAction(down) {
    try {
    var results = document.getElementById('resultsList');
    var menulist = results.currentItem.firstChild.nextSibling;
    var select = null;
    if (down) {
        if (menulist.selectedItem.nextSibling)
            select = menulist.selectedItem.nextSibling;
    } else {
        if (menulist.selectedItem.previousSibling)
            select = menulist.selectedItem.previousSibling;
    }
    if (select) {
        menulist.selectedItem = select;
        select.parentNode.parentNode.value.action = select.label;
    }
    } catch(e) { log.exception(e);}
}

function recorder_onListItemChange() {
    try {
    var results = document.getElementById('resultsList');
    var checkbox = results.currentItem.firstChild;
    recorder_onListItemToggle(checkbox);
    } catch(e) { log.exception(e);}
}

function recorder_onListItemToggle(checkElem) {
    // clicked the checkbox cell
    if (checkElem.getAttribute('checked') == "true") {
        checkElem.setAttribute("checked","false");
        checkElem.value.enabled=false;
    } else {
        checkElem.setAttribute("checked","true");
        checkElem.value.enabled=true;
    }
}

function recorder_onListItemClick(event) {
    var checkElem = event.target;
    if (event.target.nodeName == 'listcell') {
        checkElem = event.target;
    } else
    if (event.target.nodeName == 'listitem') {
        checkElem = event.target.firstChild;
    }
    if (!checkElem)
        return;
    if (checkElem.nodeName == 'listcell' && checkElem.getAttribute('type') == 'checkbox') {
        if ((event.clientX < checkElem.boxObject.x + checkElem.boxObject.width) &&
            (event.clientX > checkElem.boxObject.x)) {
    
            recorder_onListItemToggle(checkElem);
        }
    } else
    if (checkElem.nodeName == 'menuitem') {
        checkElem.parentNode.parentNode.value.action = checkElem.label;
    }
    recorder_show_event();
}

function _recorder_item_action_menu(obj) {
    var menu = document.createElement('menulist');
    menu.value = obj;
    var popup = document.createElement('menupopup');
    var i1 = document.createElement('menuitem');
    i1.setAttribute('label', 'fire');
    i1.setAttribute('selected', 'true');
    var i2 = document.createElement('menuitem');
    i2.setAttribute('label', 'wait');
    popup.appendChild(i1);
    popup.appendChild(i2);
    menu.appendChild(popup);
    return menu;
}

function recorder_set_results() {
    try {
    recorder_listbox('resultsList');
    document.getElementById("prop_name").setAttribute('value','');
    document.getElementById("prop_value").setAttribute('value','');
    var results = document.getElementById('resultsList');
    for (var i =0; i < recorder.currentTest.eventList.length; i++) {
        var item = document.createElement('listitem');
        item.setAttribute("allowevents",true);
        item.addEventListener("click", recorder_onListItemClick, true);

        var cell = document.createElement('listcell');
        cell.setAttribute("type","checkbox");
        if (recorder.currentTest.eventList[i].enabled)
            cell.setAttribute("checked","true");
        else
            cell.setAttribute("checked","false");
        cell.value = recorder.currentTest.eventList[i];
        item.appendChild(cell);

        cell = document.createElement('listcell');
        var menu = _recorder_item_action_menu(recorder.currentTest.eventList[i]);
        item.appendChild(menu);
        
        cell = document.createElement('listcell');
        cell.setAttribute('label',recorder.currentTest.eventList[i].type);
        cell.setAttribute('value',i);
        item.appendChild(cell);
        
        cell = document.createElement('listcell');
        var parts = recorder.currentTest.eventList[i].originalTargetXPath.split('/');
        cell.setAttribute('label',parts[parts.length-1]);
        item.setAttribute("tooltiptext", recorder.currentTest.eventList[i].type+": "+parts[parts.length-1]);
        item.appendChild(cell);
        
        results.appendChild(item);
    }
    } catch(e) { log.exception(e);}
}

function recorder_show_event() {
    try {
    recorder_listbox('eventInfo');
    var eventInfo = document.getElementById('eventInfo');
    var results = document.getElementById('resultsList');
    var index= results.selectedIndex;
    var e = recorder.currentTest.eventList[index];
    for (var name in e) {
        var item = document.createElement('listitem');
        var cell = document.createElement('listcell');
        cell.setAttribute('label',name);
        item.appendChild(cell);
        cell = document.createElement('listcell');
        cell.setAttribute('label',e[name]);
        item.setAttribute('name', name);
        item.setAttribute('value', e[name]);
        item.setAttribute('tooltiptext', name+": "+e[name]);
        item.appendChild(cell);
        eventInfo.appendChild(item);
        
    }
    } catch(e) { log.exception(e);}
}

function recorder_show_event_item() {
    var eventInfo = document.getElementById('eventInfo');
    var index= eventInfo.selectedIndex;
    document.getElementById("prop_name").setAttribute('value',eventInfo.selectedItem.getAttribute('name'));
    document.getElementById("prop_value").setAttribute('value',eventInfo.selectedItem.getAttribute('value'));
}


function recorder_run_xpath_test() {
    try {
    var expr = document.getElementById('xpath_test_expression').value;
    var s;
    log.lastErrorMsg = null;
    log.setLevel(Casper.Logging.DEBUG);
    var result = Casper.XPath.evaluatePaths(opener.document.documentElement, expr);
    s = log.lastErrorMsg;
    if (typeof(result[0].nodeName)!='undefined') {
        s += "node is "+result[0].nodeName+": "+result[0]+"\n";
    }
    s += Casper.Logging.getObjectTree(result, true);
    log.setLevel(Casper.Logging.WARN);
    document.getElementById('xpath_test_result').setAttribute('value', s);
    } catch(e) { log.exception(e);}
}
