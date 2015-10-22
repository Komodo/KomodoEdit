/**
 * Script to build an xpi, running koext build in the current project root.
 */

var project = ko.macros.current.project;
var projectDir = ko.interpolate.interpolateString('%p');
var callback = function() {
  require("notify/notify").send("Build complete", "projects");
  ko.projects.manager.saveProject(project);
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
