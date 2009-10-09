/* Copyright (c) 2000-2009 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

function getDirectoryFromTextObject(textlikeObject) {
    // textlikeObject has a 'value' property -- could be a menulist or text field
    var currentFileName = textlikeObject.value;
    var osPath = Components.classes["@activestate.com/koOsPath;1"].getService(Components.interfaces.koIOsPath);
    var path =  currentFileName ? osPath.dirname(currentFileName) : null;
    return path && osPath.exists(path) ? path : null;
}

function loadExecutableIntoInterpreterList(availInterpListID) {
    var availInterpList = document.getElementById(availInterpListID);
    var currentPath = getDirectoryFromTextObject(availInterpList);
    var path = ko.filepicker.openExeFile(currentPath);
    if (path) {
        availInterpList.selectedItem = availInterpList.appendItem(path, path);
        return true;
    }
    return false;
}
