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

// Globals
var log = ko.logging.getLogger("pref-ui");
var data = new Object(); // persist pref panel data here

var cmd_regex = /^ko.commands.doCommandAsync\([\'\"](cmd_\w+)[\'\"]\s*,\s*event\)$/;

function OnPreferencePageOK(prefset)
{
    var id, checkbox, broadcasterId, broadcaster, currentState;
    for (var i = 0; i < data.ids.length; i++) {
        id = data.ids[i];
        checkbox = document.getElementById(id);
        if (checkbox == null) {
            log.warn("couldn't find checkbox: " + id);
            continue;
        }
        broadcasterId = checkbox.getAttribute('broadcaster');
        broadcaster = parent.opener.document.getElementById(broadcasterId);
        if (!broadcaster) {
            log.warn("couldn't find broadcaster: " + id);
            continue;
        }
        if (broadcaster.hasAttribute('checked') && broadcaster.getAttribute('checked') == 'true') {
            currentState = 'true';
        } else {
            currentState = 'false';
        }
        if (currentState != data[id]) {
            var cmd = broadcaster.getAttribute('oncommand');
            if (parent.opener) {
                // See bug 79113: "Multi-window: opener considered harmful"
                // XXX Should send notifications to observers
                var m = cmd_regex.exec(cmd);
                if (m) {
                    parent.opener.ko.commands.doCommandAsync(m[1]);
                } else {
                    parent.opener.eval('var event;'+cmd);
                }
            }
        }
    }
    return true;
}

function updateData(id) {
    data[id] = document.getElementById('showTextButtons').getAttribute(id);
}

function OnPreferencePageInitalize(prefset) {
    // This runs once when the preferences dialog is opened.
    var id, checkbox, broadcasterId, broadcaster;

    var ids = ['showTextButtons',
               'showStandardToolbar',
               'showFindToolbar',
               'showMacroToolbar',
               'showKomodoToolbar',
              ];
    for (var i = 0; i < ids.length; i++) {
        id = ids[i];
        checkbox = document.getElementById(id);
        if (checkbox == null) {
            log.warn("couldn't find checkbox: " + id);
            continue;
        }
        broadcasterId = checkbox.getAttribute('broadcaster');
        broadcaster = parent.opener.document.getElementById(broadcasterId);
        if (!broadcaster) {
            log.warn("couldn't find broadcaster: " + id);
            continue;
        }
        if (broadcaster.hasAttribute('checked') && broadcaster.getAttribute('checked') == 'true') {
            data[id] = 'true';
        } else {
            data[id] = 'false';
        }
    }
    data.ids = ids;
    return data;
}

function OnPreferencePageLoading(prefset) {
    var id;
    for (var i = 0; i < data.ids.length; i++) {
        id = data.ids[i];
        document.getElementById(id).setAttribute('checked', data[id])
    }
}

function PrefUI_OnLoad()
{
    parent.hPrefWindow.onpageload();
}

