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

var gKeyDownKeys = null;

var gMainWindow = null;

function onload() {
    try {
    gMainWindow = ko.windowManager.getMainWindow();
    var keyset = document.importNode(gMainWindow.document.
                           getElementById('widekeyset'), true);

    for (var i=0; i < keyset.childNodes.length; i++) {
        try {
            keyset.childNodes[i].removeAttribute('command');
            //dump(keyset.childNodes[i].getAttribute('id')+': '+keyset.childNodes[i].getAttribute('oncommand')+'\n');
            //ko.logging.dumpDOM(keyset.childNodes[i]);
        } catch(e) {
            dump(e+'\n');
            dump(keyset.childNodes[i]+"\n");
        }
    }
    document.documentElement.appendChild(keyset);

    window.addEventListener('keypress',handleKeyUp, false);
    window.addEventListener('keydown', handleKeyDown, false);
    window.addEventListener('keyup', handleKeyPress, false);
    } catch(e) { dump(e+'\n'); }
}

function eventBindings(event, partial) {
    var possible = [];
    var k;
// #if PLATFORM == 'darwin'
    k = event2keylabel(event, true, partial);
// #endif
    k = event2keylabel(event, false, partial);
    if (k)
        possible.push(k);
// #if PLATFORM != 'darwin' and  PLATFORM != 'win'
    if (event.shiftKey) {
        var k = event2keylabel(event, true, partial);
        if (k && k != possible[0])
            possible.push(k);
    }
// #endif
    if (possible.length < 1) return null;
    return possible;
}

function event2keylabel(event, useShift, partial) {
    var data = [];
    try {
        if (typeof(useShift) == 'undefined')
// #if PLATFORM == 'darwin' or PLATFORM == 'win'
            useShift = true;
// #else
            useShift = false;
// #endif
        if (typeof(partial) == 'undefined')
            partial = false;
        // From an event, builds the string which corresponds to the key
        // conveniently also the menu label, pretty description, etc.
    
        // This is a little tricky because while most keystrokes that we care about spawn keypress
        // events, some only show up in keywowns.

        var keypressed = null;
        if (event.keyCode &&
            event.keyCode in gVKCodes &&
            !(event.keyCode in gVKModifiers) ) {
            keypressed = gVKCodes[event.keyCode];
        } else
        if (event.charCode == 32) {
            keypressed = 'Space';
        } else
        if (event.charCode > 32)
            keypressed = String.fromCharCode(event.charCode).toUpperCase();
        //else if (event.charCode && event.charCode in gVKFixup)
        //    keypressed = gVKFixup[event.charCode];
        
        if (!partial && keypressed == null)
            return '';

        //ko.logging.dumpEvent(event);
        if (event.metaKey) data.push("Meta");
        if (event.ctrlKey) data.push("Ctrl");
        if (event.altKey) data.push("Alt");
        if (event.shiftKey) {
            // if no other modifier, and this is ascii US a-z,
            // add the shift modifier to the keylabel, otherwise, just
            // use the charcode as-is.  
            if (event.charCode == 0 || // no char code, such as DEL
                (useShift && data.length > 0) || // with modifier
// #if PLATFORM == 'darwin' or PLATFORM == 'win'
                // ctrl and meta need to always include shift in the label
                // since the os does not shift the character
                // exception is win ctrl+shift+2|6 on US kb
                !event.altKey && event.charCode <= 127 ||
// #endif
                event.charCode >= 65 && event.charCode <= 90 ||
                event.charCode >= 97 && event.charCode <= 122)
                    data.push("Shift");
        }
        data.push(keypressed);
    } catch (e) {
      log.exception(e);
    }
    if (event.shiftKey) 
        dump(event.type+" got shift with "+data.join('+')+" useshift is "+useShift+"\n");
    return data.join('+');
}

function handleKeyUp(event) {
    handle(event);
}

function handleKeyDown(event) {
    handle(event);
}
function handleKeyPress(event) {
    handle(event);
}

function combineBindingList(kdown, kpress) {
    if (kpress.indexOf(kdown) < 0) {
        kpress.push(kdown);
    }
}

function handle (event) {
    event.cancelBubble = true;
    event.preventDefault();

    var labels = null;
    if (event.type == 'keydown') {
//// #if PLATFORM != 'darwin'
        gKeyDownKeys = event2keylabel(event);
//// #endif
        labels = eventBindings(event, true);
        document.getElementById('keyevent').setAttribute('value', "");
    } else
    if (event.type == 'keypress') {
        labels = eventBindings(event);
//// #if PLATFORM != 'darwin'
        if (gKeyDownKeys) {
            combineBindingList(gKeyDownKeys, labels);
        }
        gKeyDownKeys = null;
//// #endif
    } else
    if (event.type == 'keyup') {
        labels = eventBindings(event, true);
    }
    //dump(event.type+" event2keylabel found "+label);
    //dump("\n");
    //ko.logging.dumpEvent(event);
    

    //dump(event.type+' name = ' + data + '\n');
    var charcodeid, keycodeid, labelid, nameid;
    if (event.type == 'keydown') {
        document.getElementById('keyevent').setAttribute('value', '');
        charcodeid='charcodeDown';
        keycodeid='keycodeDown';
        labelid='labelDown';
        nameid='nameDown';
        exists="existsDown";
        eventkeycode="eventDown";
    } else
    if (event.type == 'keypress') {
        charcodeid='charcodePress';
        keycodeid='keycodePress';
        labelid='labelPress';
        nameid='namePress';
        exists="existsPress";
        eventkeycode="eventPress";
    } else
    if (event.type == 'keyup') {
        charcodeid='charcodeUp';
        keycodeid='keycodeUp';
        labelid='labelUp';
        nameid='nameUp';
        exists="existsUp";
        eventkeycode="eventUp";
    }
    
    var match = "1st Miss";
    var keyname = "No Keyname";
    var keyevent = null;

    if (labels && labels.length > 0) {
        keyname = labels[0];
        var matches = document.getElementsByAttribute("name", keyname);
        if (matches.length > 0) {
            keyevent = matches[0].getAttribute("id");
            match = "1st Match";
        }
    } else {
        match = "No Label";
    }
    if (labels && labels.length > 1) {
        keyname = labels.join(', ');
        var matches = document.getElementsByAttribute("name", labels[1]);
        if (matches.length > 0) {
            keyevent += " - "+matches[0].getAttribute("id");
            match += " - 2st Match";
        } else {
            match += " - 2nd Miss";
        }
    }
    document.getElementById(exists).setAttribute('value', match);
    document.getElementById(eventkeycode).setAttribute('value', keyname);
    if (keyevent)
        document.getElementById('keyevent').setAttribute('value', keyevent);
    document.getElementById(charcodeid).setAttribute('value', event.charCode);
    document.getElementById(keycodeid).setAttribute('value', event.keyCode);
    //dump('---\n');
}


var gVKCodes = {
    0x03: "cancel",
    0x06: "Help",
    0x08: "Backspace",
    0x09: "Tab",
    0x0c: "Clear",
    0x0d: "Return",
    0x0e: "Enter",
    //0x10: "Shift",
    //0x11: "Control",
    //0x12: "Alt",
    0x13: "Pause",
    0x14: "Caps_Lock",
    0x1b: "Escape",
    0x20: "Space",
    0x21: "Page_Up",
    0x22: "Page_Down",
    0x23: "End",
    0x24: "Home",
    0x25: "Left",
    0x26: "Up",
    0x27: "Right",
    0x28: "Down",
    0x2c: "PrintScreen",
    0x2d: "Insert",
    0x2e: "Delete",
    0x30: '0',
    0x31: '1',
    0x32: '2',
    0x33: '3',
    0x34: '4',
    0x35: '5',
    0x36: '6',
    0x37: '7',
    0x38: '8',
    0x39: '9',
    0x3b: ";",
    0x3d: "=",
    0x43: "Enter", // Ctrl Enter KeyCode on OSX
    0x4d: "Return", // Ctrl Return KeyCode on OSX
    0x50: "F16", // on OSX
    0x60: "NumPad-0",
    0x61: "NumPad-1",
    0x62: "NumPad-2",
    0x63: "NumPad-3",
    0x64: "NumPad-4",
    0x65: "NumPad-5",
    0x66: "NumPad-6",
    0x67: "NumPad-7",
    0x68: "NumPad-8",
    0x69: "NumPad-9",
    0x6a: "*",
    0x6b: "+",
    0x6c: "Separator",
    0x6d: "-",
    0x6e: ".",
    0x6f: "/",
    0x70: "F1",
    0x71: "F2",
    0x72: "F3",
    0x73: "F4",
    0x74: "F5",
    0x75: "F6",
    0x76: "F7",
    0x77: "F8",
    0x78: "F9",
    0x79: "F10",
    0x7A: "F11",
    0x7B: "F12",
    0x7C: "F13",
    0x7D: "F14",
    0x7E: "F15",
    0x7F: "F16",
    0x80: "F17",
    0x81: "F18",
    0x82: "F19",
    0x83: "F20",
    0x84: "F21",
    0x85: "F22",
    0x86: "F23",
    0x87: "F24",
    0x90: "Num_Lock",
    0x91: "Scroll_Lock",
    0xbc: ",",
    0xbe: ".",
    0xbf: "/",
    0xc0: "`",
    0xdb: "[",
    0xdc: "\\",
    0xdd: "]",
    0xde: "\""
    //0xe0: "Meta"
}

var gVKModifiers = {
    0x10: "Shift",
    0x11: "Control",
    0x12: "Alt",
    0xe0: "Meta"
};

var gVKFixup = {
    0x1b: "[", // osx
    0x1c: "\\", // osx
    0x1d: "]", // osx
    0x1e: "'",
    0x1f: "-" // osx
}
