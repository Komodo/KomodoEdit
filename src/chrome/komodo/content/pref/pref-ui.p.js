/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Globals
var log = ko.logging.getLogger("pref-ui");
var data = new Object(); // persist pref panel data here

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
            parent.opener.eval('var event;'+cmd);
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

