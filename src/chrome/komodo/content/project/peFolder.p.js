/* Copyright (c) 2000-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.projects)=='undefined') {
    ko.projects = {};
}

(function() {

var log = ko.logging.getLogger('peFolder');
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/project/peFolder.properties");

this.addFileWithURL = function peFolder_addFileWithURL(url, /*koIPart*/ parent)
{
    return this.addPartWithURLAndType(url, 'file', parent);
}

this.addPartWithURLAndType = function(url, typename, parent) {
    if (typeof(parent)=='undefined' || !parent)
        parent = ko.projects.active.getSelectedItem();
    var part = parent.project.createPartFromType(typename);
    part.setStringAttribute('url', url);
    part.setStringAttribute('name', ko.uriparse.baseName(url));
    ko.projects.manager.addItem(part, parent);
    return part;
}

this.addNewFileFromTemplate = function peFolder_addNewFileFromTemplate(/*koIPart*/ parent)
{
    var obj = {
      type:"file",
      defaultDir:parent.getFile().dirName,
      filename: null
    };
    ko.launch.newTemplate(obj);
    if (obj.filename) {
        return this.addPartWithURLAndType(ko.uriparse.pathToURI(obj.filename),
                                          'file', parent);
    }
}
    
this.addFile = function peFolder_addFile(parent_item)
{
    //XXX todo: Support other resources

    var defaultDir = parent_item.project.getFile().dirName;
    var files = ko.filepicker.browseForFiles(defaultDir, // default dir
                                             null, // default filename
                                             _bundle.GetStringFromName("addFilesToProject")); // title
    if (files == null) {
        return false;
    } else {
        var url;
        for (var i = 0; i < files.length; ++i) {
            url = ko.uriparse.localPathToURI(files[i]);
            ko.projects.addFileWithURL(url, parent_item);
        }
        return true;
    }
}


}).apply(ko.projects);

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
    }, 1000);
