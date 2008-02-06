/* Copyright (c) 2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* 'Abbreviations': insert toolbox snippets by name */

if (typeof(ko) == 'undefined') {
    var ko = {};
}

if (typeof(ko.abbrev)=='undefined') {
    ko.abbrev = {};
}

(function() {

/**
 * Expands the abbreviation at the current cursor position, if any.
 */
this.expandAbbrev = function expandAbbrev() {
    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                        getService(Components.interfaces.koILastErrorService);
    var view = ko.views.manager.currentView;
    var scimoz = view.scimoz;
    if (!scimoz.selText) {
        scimoz.wordLeftExtend();
    }
    var name = scimoz.selText;
    scimoz.replaceSel(''); // make sure there is no selection before calling expand?
    scimoz.beginUndoAction();
    try {
        _expand(name, view);
    } catch(e) {
        scimoz.insertText(scimoz.currentPos, name);
        scimoz.wordRight();
        var errmsg = lastErrorSvc.getLastErrorMessage();
        ko.dialogs.alert("Error inserting snippet: " + errmsg);
    } finally {
        scimoz.endUndoAction();
    }
}

/**
 * Internal function to do the actual work of expanding an abbreviation.
 * 
 * @param name {String} name of the snippet to insert
 * @param view {koIView} the current view, passed through to
 *      ko.projects.snippetInsertImpl
 */
function _expand(name, view) {
    var project = ko.projects.manager.currentProject;
    var snippet = ko.projects.findPart("snippet", name, "*", project);
    
    if (snippet) {
        ko.projects.snippetInsertImpl(snippet, view);
    } else {
        var msg = "No snippet found named " + name;
        ko.statusBar.AddMessage(msg,"debugger",5000,true);
    }
}

}).apply(ko.abbrev);
