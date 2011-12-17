/* Copyright (c) 2011 YourNameHere
   See the file LICENSE.txt for licensing information. */

var reconfigure = function() {
try {
    var macro = ko.macros.current;
    var project = macro.project;
    if (!project) {
        ko.dialogs.alert("Unexpected error: no project associated with macro "
                         + macro.name);
    }
    var targetName;
    var prefset = project.prefset;
    if (!prefset.hasPrefHere("koextgen.target")) {
        ko.dialogs.alert("Project "
                         + project.name
                         + " doesn't seem to be an extension project.");
        return;
    }
    targetName = prefset.getStringPref("koextgen.target");
    var projectFileEx = project.getFile();
    // Get the project's location, then from one point higher populate it.
    var projectPath = projectFileEx.path;
    var projectDirPath = projectFileEx.dirName;

    var koExt = ko.koextgen.extensionLib;
    
    var prefset = project.prefset;
    prefset.setStringPref("koextgen.target", targetName);
    var baseName = projectFileEx.baseName;
    var ext = projectFileEx.ext;
    baseName = baseName.substr(0, baseName.length - ext.length);
    var rdfFile = koExt.os.path.join(projectDirPath, "install.rdf");
    var rdfVars = koExt.getRDFVars(koExt.readFile(rdfFile));
    var data = {
        'valid': false,
        'configured': true,
        'vars': rdfVars,
    };
    data.vars['ext_name'] = koExt.getNiceName(data.vars.name);
    var setup_xul_uri = "chrome://koextgen/content/resources/setup.xul";
    window.openDialog(
        setup_xul_uri,
        "_blank",
        "centerscreen,chrome,resizable,scrollbars,dialog=no,close,modal=yes",
        data);
    if (data.valid) {
        koExt.updateProject(projectDirPath, targetName, data.vars);
    }
} catch(ex) {
    ko.dialogs.alert("Error in reconfigure: " + ex)
}
};
reconfigure();
