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

var log = ko.logging.getLogger("pref-codeintel");
//log.setLevel(ko.logging.LOG_INFO);

var gWidgets = new Object();
var gEnabled = null;
var gCatalogsView = null;
var gLastSortColId = null;



//---- internal support functions

function _setElementEnabledState(elt, enabled) {
    if (enabled) {
        if (elt.hasAttribute('disabled')) {
            elt.removeAttribute('disabled');
        }
    } else {
        elt.setAttribute('disabled', true);
    }
}


//---- functions for XUL

function PrefCodeIntel_OnLoad()
{
    log.info("PrefCodeIntel_OnLoad");
    try {
        gWidgets.triggeringEnabledCheckbox = document.getElementById("codeintel_completion_triggering_enabled");
        gWidgets.fillupsEnabledCheckbox = document.getElementById("codeintel_completion_auto_fillups_enabled");
        gWidgets.scanProjectCheckbox = document.getElementById("codeintel_scan_files_in_project");
        gWidgets.scanDepthTextbox = document.getElementById("codeintel_max_recursive_dir_depth");
        gWidgets.notPreparedDesc = document.getElementById("notPreparedForLanguagesWarning");
        gWidgets.catalogs = document.getElementById("catalogs");
        gWidgets.addCatalogButton = document.getElementById("add-catalog");
        gWidgets.removeCatalogButton = document.getElementById("remove-catalog");

        parent.hPrefWindow.onpageload();

    } catch(ex) {
        log.exception(ex);
    }
}

function OnPreferencePageLoading(prefset)
{
    try {
        // Disable the UI if codeintel is not enabled.
        gEnabled = prefset.getBooleanPref("codeintel_enabled");
        _setElementEnabledState(gWidgets.fillupsEnabledCheckbox, gEnabled);
        _setElementEnabledState(gWidgets.triggeringEnabledCheckbox, gEnabled);
        _setElementEnabledState(gWidgets.catalogs, gEnabled);
        _setElementEnabledState(gWidgets.addCatalogButton, gEnabled);
        _setElementEnabledState(gWidgets.removeCatalogButton, gEnabled);
        _setElementEnabledState(gWidgets.scanProjectCheckbox, gEnabled);
        _setElementEnabledState(gWidgets.scanDepthTextbox, gEnabled);

        if (gEnabled) {
            // Init the catalogs tree.
            gCatalogsView = Components.classes['@activestate.com/koCodeIntelCatalogsTreeView;1']
                .createInstance(Components.interfaces.koICodeIntelCatalogsTreeView);
            gWidgets.catalogs.treeBoxObject.view = gCatalogsView;
            var codeintelSvc = Components.classes["@activestate.com/koCodeIntelService;1"]
                                      .getService(Components.interfaces.koICodeIntelService);
            gCatalogsView.init(codeintelSvc,
                               parent.hPrefWindow.prefset,
                               "codeintel_selected_catalogs");
            PrefCodeIntel_UpdateCatalogsUI();
        } else {
            document.getElementById("disabled-warning").removeAttribute("collapsed");
            document.getElementById("groupbox-1").setAttribute("collapsed", "true");
            document.getElementById("groupbox-2").setAttribute("collapsed", "true");
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function OnPreferencePageOK(prefset)
{
    log.info("OnPreferencePageOK(prefset)");
    try {
        if (gEnabled) {
            gCatalogsView.save();
        }
        return true;
    } catch(ex) {
        log.exception(ex);
        var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
            .getService(Components.interfaces.nsIStringBundleService)
            .createBundle("chrome://komodo/locale/pref/pref-languages.properties");
        return ignorePrefPageOKFailure(prefset,
                                       bundle.GetStringFromName("savingCodeintelPrefsFailed"),
                                       ex.toString());
    }
}

function PrefCodeIntel_CatalogsOnKeyPress(event)
{
    if (event.charCode == 32) { /* spacebar */
        return parent.hPrefWindow.toggleTreeItems(gCatalogsView, "catalogs-selected");
    } else {
        return true;
    }
}

function PrefCodeIntel_CatalogsOnClick(event)
{
    try {
        // c.f. mozilla/mailnews/base/resources/content/threadPane.js
        var t = event.originalTarget;
        // single-click on a column
        if (t.localName == "treecol") {
            _PrefCodeIntel_UpdateSortIndicators();
        }

    } catch(ex) {
        log.exception(ex);
    }
}

function _PrefCodeIntel_UpdateSortIndicators()
{
    var sortColId = gCatalogsView.sortColId;
    var sortDirection = gCatalogsView.sortDirection;

    if (gLastSortColId && sortColId != gLastSortColId) {
        document.getElementById(gLastSortColId).removeAttribute("sortDirection");
    }
    if (sortColId) {
        document.getElementById(sortColId).setAttribute("sortDirection", sortDirection);
    }
    gLastSortColId = sortColId;
}


function PrefCodeIntel_AddCatalog()
{
    try {
        //TODO: A "don't ask again" dialog explaining what catalogs are on
        //      disk, where to look for them, how to make them, etc.

        var prefName = "codeintel.catalogs";
        var default_dir = ko.filepicker.internDefaultDir(prefName);
        var cix_paths = ko.filepicker.browseForFiles(
                default_dir, null,
                "Add API Catalog", // title
                "Code Intelligence XML", // defaultFilterName
                ["Code Intelligence XML", "All"]); // filterNames
        if (cix_paths == null) {
            return;
        }
        ko.filepicker.updateDefaultDirFromPath(prefName, cix_paths);
        var adder = gCatalogsView.addPaths(cix_paths.length, cix_paths);
        ko.dialogs.progress(adder,
                        "Adding API Catalog(s).",
                        "Code Intelligence",
                        true,  // cancellable
                        null,  // cancel_warning
                        true); // modal
        gWidgets.catalogs.focus();
    } catch(ex) {
        log.exception(ex);
    }
}

function PrefCodeIntel_RemoveCatalog()
{
    try {
        var answer = ko.dialogs.yesNo(
                "Are you sure you want to remove this catalog?");
        if (answer != "Yes") {
            return;
        }

        var remover = gCatalogsView.removeUISelectedPaths();
        ko.dialogs.progress(remover,
                        "Remove API Catalog(s).",
                        "Code Intelligence",
                        true,  // cancellable
                        null,  // cancel_warning
                        true); // modal
    } catch(ex) {
        log.exception(ex);
    }
}

function PrefCodeIntel_UpdateCatalogsUI()
{
    try {
        _setElementEnabledState(gWidgets.removeCatalogButton,
            gCatalogsView.areUISelectedRowsRemovable());
    } catch(ex) {
        log.exception(ex);
    }
}

