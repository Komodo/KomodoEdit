/**
 * Script to build an xpi, running koext build in the current project root.
 */

var project = ko.macros.current.project;

var os = Components.classes['@activestate.com/koOs;1'].
  getService(Components.interfaces.koIOs);

var appInfo = Components.classes["@mozilla.org/xre/app-info;1"].
  getService(Components.interfaces.nsIXULRuntime);

var koDirs = Components.classes['@activestate.com/koDirs;1'].
  getService(Components.interfaces.koIDirs);

var pythonExe = koDirs.pythonExe;
var projectDir = ko.interpolate.interpolateString('%p');
var scriptName = 'koext';

if (appInfo.OS == 'WINNT') {
  scriptName += ".py"; 
}

var arr = [koDirs.sdkDir, 'bin', scriptName]
var app = os.path.joinlist(arr.length, arr);
var cmd = ('"'
           + pythonExe
           + '" "'
           + app
           + '" build -i chrome.manifest -i chrome.p.manifest -d "'
           + projectDir
           + '"');

if (appInfo.OS == 'WINNT') {
  cmd = '"' + cmd + '"';
}
var cwd = koDirs.mozBinDir;
cmd += " {'cwd': u'"+cwd+"'}";

ko.run.runEncodedCommand(window, cmd, function() {
  ko.statusBar.AddMessage('Build complete', 'projects', 5000, true);
  ko.projects.manager.saveProject(project);
});
