
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

/**
 * An extension to add dialog-based spellchecking of text parts of files.
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (!('extensions' in ko)) {
    ko.extensions = {};
}
if (!('spellchecker' in ko.extensions)) {
    ko.extensions.spellchecker = {};
}

(function() {
// Set up a controller to make sure we do this only when there's a view

var __SpellCheckController = null;

function SpellCheckController() {
    try {
        window.controllers.appendController(this);
        window.addEventListener("unload", this.destroy.bind(this), false);
    } catch(e) {
        ko.logging.getLogger('spellchecker').exception(e);
    }
}

// The following two lines ensure proper inheritance (see Flanagan, p. 144).
SpellCheckController.prototype = new xtk.Controller();
SpellCheckController.prototype.constructor = SpellCheckController;

SpellCheckController.prototype.destroy = function() {
    window.controllers.removeController(this);
}

SpellCheckController.prototype.is_cmd_checkSpelling_enabled = function() {
    return (ko.views.manager.currentView
            && ko.views.manager.currentView.languageObj != null);
}

SpellCheckController.prototype.do_cmd_checkSpelling = function() {
    var obj = {};
    var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"].
                    getService(Components.interfaces.nsIStringBundleService).
                    createBundle("chrome://komodospellchecker/locale/spellcheck.properties");
    try {
        obj.view = ko.views.manager.currentView;
        if (!obj.view || !obj.view.languageObj) {
            alert(_bundle.GetStringFromName("noCurrentDocumentToSpellcheck"));
            return;
        }
        obj.ko = ko;
    } catch(ex) {
        var message = _bundle.formatStringFromName("errorCouldNotFindDocument",
                                                   [ex], 1);
        alert(message);
        return;
    }
    window.openDialog("chrome://komodospellchecker/content/koSpellCheck.xul",
                      "spellchecker",
                      "chrome,modal,titlebar",
                      obj);
}

this.SpellCheckController_onload = function() {
    __SpellCheckController = new SpellCheckController();
    window.removeEventListener("komodo-ui-started", ko.extensions.spellchecker.SpellCheckController_onload, true);
}

}).apply(ko.extensions.spellchecker);

window.addEventListener("komodo-ui-started", ko.extensions.spellchecker.SpellCheckController_onload, true);
