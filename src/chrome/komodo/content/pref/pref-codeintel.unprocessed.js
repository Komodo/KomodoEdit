/* Copyright (c) 2004-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


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
        gWidgets.fillupsEnabledCheckbox = document.getElementById("codeintel_completion_fillups_enabled");
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

        if (gEnabled) {
            // Init the catalogs tree.
            gCatalogsView = Components.classes['@activestate.com/koCodeIntelCatalogsTreeView;1']
                .createInstance(Components.interfaces.koICodeIntelCatalogsTreeView);
            gWidgets.catalogs.treeBoxObject.view = gCatalogsView;
            gCatalogsView.init(parent.opener.gCodeIntelSvc,
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
        return false;
    }
}

function PrefCodeIntel_CatalogsOnKeyPress(event)
{
    try {
        if (event.charCode == 32) { /* spacebar */
            var row_idx = gWidgets.catalogs.currentIndex;
            gCatalogsView.toggleSelection(row_idx);
            return false;
        }
    } catch(ex) {
        log.exception(ex);
    }
    return true;
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

        var cix_paths = ko.filepicker.openFiles(
                null, null,
                "Add API Catalog", // title
                "Code Intelligence XML", // defaultFilterName
                ["Code Intelligence XML", "All"]); // filterNames
        if (cix_paths == null) {
            return;
        }
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

