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


//---- globals

var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
        .getService(Components.interfaces.nsIStringBundleService)
        .createBundle("chrome://komodo/locale/pref/pref-winInteg.properties");

var log = ko.logging.getLogger("pref-winInteg");
//log.setLevel(ko.logging.LOG_DEBUG);

var _gData = new Object(); // persisted pref panel data

//---- internal support routines

function _ValidateExtensions(window, extsStr) {
    if (extsStr) {
        var exts = extsStr.split(/[;:,]/);
        for (var i in exts) {
            var ext = exts[i];
            ext = ext.replace(/^\s*|\s*$/g, ''); // strip whitespace
            if (!ext) {
                continue
            } else if (ext.match(/^\.[\w\+_-]+$/) == null) {
                ko.dialogs.alert(bundle.formatStringFromName("invalidExtension", [ext], 1));
                
                return false;
            }
        }
    } else {
        ko.dialogs.alert(bundle.GetStringFromName("youMustEnterAnExtension"));
        return false;
    }
    return true;
}



//---- public methods

function PrefWinInteg_OnLoad()
{
    log.info("PrefWinInteg_OnLoad()");
    try {
        // Register this pref panel and an OK callback function.
        parent.hPrefWindow.onpageload();
    } catch(ex) {
        log.exception(ex, "Error loading windows integration pref panel.");
    }
}


function OnPreferencePageInitalize(prefset) {
    log.info("OnPreferencePageInitalize()");
    try {
        _gData.winIntegSvc = Components.classes['@activestate.com/koWindowsIntegrationService;1']
                           .createInstance(Components.interfaces.koIWindowsIntegrationService);

        //XXX We keep a cache of the current lists of the extension to
        //    remember changes through pref panels changes. Ideally we would
        //    just create the koIExtensionView instances here and use
        //    _those_ as the cache. However instanciating a tree view
        //    once and then binding it to the <tree/> on subsequent re-entries
        //    to this pref's panel results in a hard Mozilla crash.
        _gData.editAssocsCache = _gData.winIntegSvc.getEditAssociations();
        _gData.editWithAssocsCache = _gData.winIntegSvc.getEditWithAssociations();
    } catch(ex) {
        log.exception(ex);
    }
}


function OnPreferencePageLoading(prefset) {
    log.info("OnPreferencePageLoading(): 'Edit'='"+_gData.editAssocsCache+
             "' 'Edit with Komodo'='"+_gData.editWithAssocsCache+"'");
    try {
        // Initialize trees
        _gData.editAssocView = Components.classes['@activestate.com/koExtensionsView;1']
                             .createInstance(Components.interfaces.koIExtensionsView);
        _gData.editAssocView.SetExtensions(_gData.editAssocsCache);
        var editAssocTree = document.getElementById("edit-assoc");
        editAssocTree.treeBoxObject.view = _gData.editAssocView;
        EditAssoc_UpdateDeleteButton();

        _gData.editWithAssocView = Components.classes['@activestate.com/koExtensionsView;1']
                                 .createInstance(Components.interfaces.koIExtensionsView);
        _gData.editWithAssocView.SetExtensions(_gData.editWithAssocsCache);
        var editWithAssocTree = document.getElementById("edit-with-assoc");
        editWithAssocTree.treeBoxObject.view = _gData.editWithAssocView;
        EditWithAssoc_UpdateDeleteButton();
        
        // Check if current associations are set and update warning box
        // as appropriate.
        PrefWinInteg_UpdateAssocWarning();
    } catch(ex) {
        log.exception(ex);
    }
}


function PrefWinInteg_ConfigureCommonAssociations()
{
    log.info("PrefWinInteg_ConfigureCommonAssociations()");
    try {
        var i, ext;

        var obj = new Object();
        obj.editAssocs = {};
        var editAssocs = _gData.editAssocView.GetExtensions().split(/[;:,]/);
        for (i in editAssocs) {
            ext = editAssocs[i];
            ext = ext.replace(/^\s*|\s*$/g, ''); // strip whitespace
            if (ext) {
                obj.editAssocs[ext] = true;
            }
        }
        obj.editWithAssocs = {};
        var editWithAssocs = _gData.editWithAssocView.GetExtensions().split(/[;:,]/);
        for (i in editWithAssocs) {
            ext = editWithAssocs[i];
            ext = ext.replace(/^\s*|\s*$/g, ''); // strip whitespace
            if (ext) {
                obj.editWithAssocs[ext] = true;
            }
        }

        window.openDialog("chrome://komodo/content/pref/setupFileAssociations.xul",
                          "_blank",
                          "chrome,modal,resizable,titlebar,centerscreen",
                          obj);

        if (obj.retval == "OK") {
            for (ext in obj.editAssocs) {
                if (obj.editAssocs[ext]) {
                    _gData.editAssocView.Add(ext);
                } else {
                    _gData.editAssocView.Remove(ext);
                }
            }
            _gData.editAssocsCache = _gData.editAssocView.GetExtensions();
            for (ext in obj.editWithAssocs) {
                if (obj.editWithAssocs[ext]) {
                    _gData.editWithAssocView.Add(ext);
                } else {
                    _gData.editWithAssocView.Remove(ext);
                }
            }
            _gData.editWithAssocsCache = _gData.editWithAssocView.GetExtensions();
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function EditAssoc_Add()
{
    log.info("EditAssoc_Add()");
    try {
        var extsStr = ko.dialogs.prompt(
                bundle.GetStringFromName("specifyExtensionToUse"),
                null, // label
                null, // value
                bundle.GetStringFromName("addExtension"), // title
                bundle.GetStringFromName("extension"), // mruName
                _ValidateExtensions); // validator
        if (extsStr) {
            var exts = extsStr.split(/[;:,]/);
            for (var i in exts) {
                var ext = exts[i];
                ext = ext.replace(/^\s*|\s*$/g, ''); // strip whitespace
                if (ext) { // skip empty strings
                    _gData.editAssocView.Add(ext);
                }
            }
            _gData.editAssocsCache = _gData.editAssocView.GetExtensions();
            EditAssoc_UpdateDeleteButton();
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function EditAssoc_Delete()
{
    log.info("EditAssoc_Delete()");
    try {
        var editAssocTree = document.getElementById("edit-assoc");
        var index = editAssocTree.currentIndex;
        var rowCount = _gData.editAssocView.rowCount;
        if (0 <= index && index <= rowCount-1) {
            _gData.editAssocView.RemoveIndex(index);
            _gData.editAssocsCache = _gData.editAssocView.GetExtensions();
            EditAssoc_UpdateDeleteButton();
        } else {
            ko.dialogs.alert(bundle.GetStringFromName("youMustFirstSelectARowToDelete"));
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function EditAssoc_UpdateDeleteButton()
{
    log.info("EditAssoc_UpdateDeleteButton()");
    try {
        var deleteButton = document.getElementById("edit-assoc-delete-button");
        if (_gData.editAssocView.rowCount == 0 ||
            _gData.editAssocView.selection.count == 0) {
            deleteButton.setAttribute("disabled", "true");
        } else if (deleteButton.hasAttribute("disabled")) {
            deleteButton.removeAttribute("disabled");
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function EditWithAssoc_Add()
{
    log.info("EditWithAssoc_Add()");
    try {
        var extsStr = ko.dialogs.prompt(
                bundle.GetStringFromName("specifyExtensionToUse"),
                null, // label
                null, // value
                bundle.GetStringFromName("addExtension"), // title
                bundle.GetStringFromName("extension"), // mruName
                _ValidateExtensions); // validator
        if (extsStr) {
            var exts = extsStr.split(/[;:,]/);
            for (var i in exts) {
                var ext = exts[i];
                ext = ext.replace(/^\s*|\s*$/g, ''); // strip whitespace
                if (ext) { // skip empty strings
                    _gData.editWithAssocView.Add(ext);
                }
            }
            _gData.editWithAssocsCache = _gData.editWithAssocView.GetExtensions();
            EditWithAssoc_UpdateDeleteButton();
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function EditWithAssoc_Delete()
{
    log.info("EditWithAssoc_Delete()");
    try {
        var editWithAssocTree = document.getElementById("edit-with-assoc");
        var index = editWithAssocTree.currentIndex;
        var rowCount = _gData.editWithAssocView.rowCount;
        if (0 <= index && index <= rowCount-1) {
            _gData.editWithAssocView.RemoveIndex(index);
            _gData.editWithAssocsCache = _gData.editWithAssocView.GetExtensions();
            EditWithAssoc_UpdateDeleteButton();
        } else {
            ko.dialogs.alert(bundle.GetStringFromName("youMustFirstSelectARowToDelete"));
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function EditWithAssoc_UpdateDeleteButton()
{
    log.info("EditWithAssoc_UpdateDeleteButton()");
    try {
        var deleteButton = document.getElementById("edit-with-assoc-delete-button");
        if (_gData.editWithAssocView.rowCount == 0 ||
            _gData.editWithAssocView.selection.count == 0) {
            deleteButton.setAttribute("disabled", "true");
        } else if (deleteButton.hasAttribute("disabled")) {
            deleteButton.removeAttribute("disabled");
        }
    } catch(ex) {
        log.exception(ex);
    }
}


function OnPreferencePageOK(prefset)
{
    log.info("PrefWinInteg_OkCallback()");
    try {
        // Set the user's selected associations in the registry and save
        // those lists to a well-known registry location for installer
        // custom actions.
        try {
            _gData.winIntegSvc.setEditAssociations(_gData.editAssocsCache);
            _gData.winIntegSvc.setEditWithAssociations(_gData.editWithAssocsCache);
        } catch (ex) {
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                               .getService(Components.interfaces.koILastErrorService);
            var errorMessage = bundle.formatStringFromName("thereWasAnErrorCreatingOrRemovingWindowsFileAssociations",
                                                           [lastErrorSvc.getLastErrorMessage()], 1);
            ko.dialogs.alert(errorMessage);
            // We still return "ok" because we don't want a lack of system
            // permissions to hold up closing prefs.
        }
        return true;
    } catch(ex2) {
        log.exception(ex2);
        return ignorePrefPageOKFailure(prefset,
                bundle.GetStringFromName("AttemptSaveWindowsIntegrationSettingsFailed"),
                                       ex2.toString());
    }
}


function PrefWinInteg_ApplyAssociations()
{
    log.info("PrefWinInteg_ApplyAssociations()");
    try {
        // Apply file association changes to the system.
        var i, ext;
        try {
            var encodedEditAssocs = _gData.editAssocView.GetExtensions();
            _gData.winIntegSvc.setEditAssociations(encodedEditAssocs);
            var encodedEditWithAssocs = _gData.editWithAssocView.GetExtensions();
            _gData.winIntegSvc.setEditWithAssociations(encodedEditWithAssocs);
        } catch (ex1) {
            var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"]
                               .getService(Components.interfaces.koILastErrorService);
            var errorMessage = bundle.formatStringFromName("thereWasAnErrorCreatingOrRemovingWindowsFileAssociations",
                                                           [lastErrorSvc.getLastErrorMessage()], 1);
            ko.dialogs.alert(errorMessage);
            // We still return "ok" because we don't want a lack of system
            // permissions to hold up closing prefs.
        }
        PrefWinInteg_UpdateAssocWarning();
        return true;
    } catch(ex2) {
        log.exception(ex2);
    }
    return false;
}


// Check if current associations are set and update warning box
// as appropriate.
function PrefWinInteg_UpdateAssocWarning()
{
    log.info("PrefWinInteg_UpdateAssocWarning()");
    try {
        //var encodedEditAssocs = _gData.editAssocView.GetExtensions();
        //var encodedEditWithAssocs = _gData.editWithAssocView.GetExtensions();
        var check = _gData.winIntegSvc.checkAssociations();
        var warningBox = document.getElementById("file-assocs-warning");
        if (check == null) {
            warningBox.setAttribute("collapsed", "true");
        } else {
            if (warningBox.hasAttribute("collapsed")) {
                warningBox.removeAttribute("collapsed");
            }
            var warningText = document.getElementById("file-assocs-warning-text");
            warningText.value = check;
        }
    } catch(ex) {
        log.exception(ex);
    }
}


