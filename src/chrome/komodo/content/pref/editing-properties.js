/* Copyright (c) 2000-2008 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

// Globals
var log = ko.logging.getLogger("pref.editing-properties");
var _pref_lint_dialog = {};

function editingPropertiesOnLoad() {
    try {
        parent.hPrefWindow.onpageload();
        _pref_lint_dialog.lintEOLs = document.getElementById("lintEOLs");
        _pref_lint_dialog.editUseLinting = document.getElementById("editUseLinting");
        pref_lint_doEnabling();
        parent.initPanel();
    } catch(e) {
        log.exception(e);
    }
}

function _pref_lint_setElementEnabledState(elt, enabled) {
    if (enabled) {
        if (elt.hasAttribute('disabled')) {
            elt.removeAttribute('disabled');
        }
    } else {
        elt.setAttribute('disabled', true);
    }
}

function pref_lint_doEnabling() {
    var enabled = _pref_lint_dialog.editUseLinting.checked;
    _pref_lint_setElementEnabledState(_pref_lint_dialog.lintEOLs, enabled);
}
