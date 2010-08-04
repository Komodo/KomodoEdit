/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

// setTimeout in case projectManager.p.js hasn't been loaded yet.
setTimeout(function() {
// backwards compat api
["getDefaultDirectory",
"addNewFileFromTemplate",
"addFileWithURL",
"addFile",
"addRemoteFile",
"addFolder",
"addLiveFolder"].map(function(name) {
    ko.projects.addDeprecatedGetter("peFolder_" + name, name);
});

ko.projects.addDeprecatedGetter("peFolder_add", "addNewPart");
ko.projects.addDeprecatedGetter("peFolder_ensureFolderAdd", "ensureAddMenu");
    }, 1000);
