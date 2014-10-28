/**
 * Script to build an xpi, running koext build in the current project root and
 * then install it into the currently running Komodo.
 */

var project = ko.macros.current.project;
var projectDir = ko.interpolate.interpolateString('%p');
var callback = function() {
  require("notify/notify").send("Build complete", "projects");
  ko.projects.manager.saveProject(project);
  var os = Components.classes["@activestate.com/koOs;1"].
                  getService(Components.interfaces.koIOs);
  var entries = os.listdir(projectDir, {});
  var xpi_entries = entries.filter(function(name) { return /.xpi$/.test(name); } );
  if (xpi_entries.length == 0) {
    ko.dialogs.alert("No xpi file found in project dir: " + projectDir);
  } else if (xpi_entries.length == 1) {
    ko.open.URI(os.path.join(projectDir, xpi_entries[0]));
  } else {
    var result = ko.dialogs.selectFromList("Extension Installation",
                              "Pick the xpi to install: ",
                              xpi_entries,
                              "one");
    if (result) {
      ko.open.URI(os.path.join(projectDir, result));
    }
  }
};
var osPath = Components.classes["@activestate.com/koOsPath;1"].
                getService(Components.interfaces.koIOsPath);
var preprocessedChromePath = osPath.join(projectDir, "chrome.p.manifest");
if (osPath.exists(preprocessedChromePath)) {
  ko.koextgen.extensionLib.command('build -i chrome.manifest -i chrome.p.manifest ' +
                                   '-d "' + projectDir + '"',
                                   callback);
} else {
  ko.koextgen.extensionLib.command('build -i chrome.manifest ' +
                                   '-d "' + projectDir + '"',
                                   callback);
}
