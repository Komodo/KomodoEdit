/* Copyright (c) 2000-2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

var dialog  = {};
var gLanguageStatusView = null;
var gLastSortColId = null;

function PrefLanguages_OnLoad() {
    dialog.languageStatus = document.getElementById("languageStatus");
    dialog.languageStatusFilterTextbox =
        document.getElementById("languageStatus-filter-textbox");
    parent.hPrefWindow.onpageload();
}

function OnPreferencePageLoading(prefset) {
  gLanguageStatusView = Components.classes['@activestate.com/koLanguageStatusTreeView;1'].
      createInstance(Components.interfaces.koILanguageStatusTreeView);
  dialog.languageStatus.treeBoxObject.view = gLanguageStatusView;
  gLanguageStatusView.init(parent.hPrefWindow.prefset,
                           "file_associations_primary_languages");
}

function OnPreferencePageClosing(prefset, ok) {
    gLanguageStatusView.save();
    parent.hPrefWindow.onpageload();
}

// Handlers for the language status tree

function toggleTreeItems() {
    return parent.hPrefWindow.toggleTreeItems(gLanguageStatusView, "languageStatus-status");
}

function PrefLanguages_OnKeyPress(event)
{
    if (event.charCode == 32) {
        return toggleTreeItems();
    } else {
        return true;
    }
}

function PrefLanguages_OnClick(event)
{
    try {
        // c.f. mozilla/mailnews/base/resources/content/threadPane.js
        var t = event.originalTarget;
        // single-click on a column
        if (t.localName == "treecol") {
            PrefLanguages_UpdateSortIndicators();
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function PrefLanguages_OnDblClick(event)
{
    try {
        toggleTreeItems();
    } catch(ex) {
        log.exception(ex);
    }
}

function PrefLanguages_UpdateSortIndicators()
{
    var sortColId = gLanguageStatusView.sortColId;
    var sortDirection = gLanguageStatusView.sortDirection;

    if (gLastSortColId && sortColId != gLastSortColId) {
        document.getElementById(gLastSortColId).removeAttribute("sortDirection");
    }
    if (sortColId) {
        document.getElementById(sortColId).setAttribute("sortDirection", sortDirection);
    }
    gLastSortColId = sortColId;
}

function updateLanguageNames(filterText) {
    try {
        gLanguageStatusView.filter = filterText;
    } catch (e) {
        log.exception(e);
    }
}
