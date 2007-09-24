/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Ask the user for two file to compare. */

var log = ko.logging.getLogger("dialogs.compare");
//log.setLevel(ko.logging.LOG_DEBUG);
var gCWD = null;


//---- interface routines for XUL

function OnLoad()
{
    try {
        var dialog = document.getElementById("dialog-compare");
        var okButton = dialog.getButton("accept");
        okButton.setAttribute("accesskey", "c");
        okButton.setAttribute("label", "Compare Files");
        okButton.setAttribute("disabled", "true");
        var first = document.getElementById('first')
        var second = document.getElementById('second');
        document.title = "Compare Two Files";

        if (opener.ko.views.manager &&
            opener.ko.views.manager.currentView &&
            opener.ko.views.manager.currentView.getAttribute('type') == 'editor' &&
            ! opener.ko.views.manager.currentView.document.isUntitled) {
            first.value = opener.ko.views.manager.currentView.document.displayPath;
            gCWD = opener.ko.window.getCwd();
            first.searchParam = stringutils_updateSubAttr(
                first.searchParam, "cwd", gCWD);
            second.searchParam = stringutils_updateSubAttr(
                second.searchParam, "cwd", gCWD);
            second.focus();
        } else {
            // Prefill the two entries with the last used ones.
            var prefName = stringutils_getSubAttr(first.searchParam, "mru");
            first.value = ko.mru.get(prefName);
            prefName = stringutils_getSubAttr(second.searchParam, "mru");
            second.value = ko.mru.get(prefName);
            first.focus();
        }
        updateOK();

        window.sizeToContent();
        if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
            dialog.centerWindowOnScreen();
        } else {
            dialog.moveToAlertPosition(); // requires a loaded opener
        }
    } catch (e) {
        log.exception(e);
    }
}

function choose(which)
{
    var file = ko.filepicker.openFile(null, null, "Please select the " + which + " file:");
    if (!file) return;
    document.getElementById(which).value = file;
    updateOK();
}

function updateOK()
{
    var ok = document.getElementById('first').value && document.getElementById('second').value;
    var dialog = document.getElementById("dialog-compare");
    var okButton = dialog.getButton("accept");
    if (ok) {
        if (okButton.hasAttribute('disabled')) {
            okButton.removeAttribute('disabled')
        }
    } else {
        okButton.setAttribute('disabled', 'true');
    }
}

function OK()
{
    try {
        var first = document.getElementById('first');
        var second = document.getElementById('second');
        var firstPath = first.value; 
        var secondPath = second.value;

        // If one or both of the files are remote, we need to open the files to
        // get the correct status for the files. Also, ensure that local file
        // paths are absolute (using gCWD if necessary).
        var fileSvc = Components.classes["@activestate.com/koFileService;1"]
            .getService(Components.interfaces.koIFileService)
        var osPathSvc = Components.classes["@activestate.com/koOsPath;1"]
            .getService(Components.interfaces.koIOsPath)
        var file1 = fileSvc.getFileFromURI(firstPath)
        if (!file1.isLocal) {
            file1.open('rb');
        } else if (!osPathSvc.isabs(firstPath)) {
            firstPath = osPathSvc.join(gCWD, firstPath);
            file1 = fileSvc.getFileFromURI(firstPath);
        }
        var file2 = fileSvc.getFileFromURI(secondPath)
        if (!file2.isLocal) {
            file2.open('rb');
        } else if (!osPathSvc.isabs(secondPath)) {
            secondPath = osPathSvc.join(gCWD, secondPath);
            file2 = fileSvc.getFileFromURI(secondPath);
        }

        // Ensure the files exist.
        if (!file1.exists) {
            alert("There is no file at '" + firstPath + "'.  Please enter another path.");
            first.focus();
            return false
        }
        if (!file2.exists) {
            alert("There is no file at '" + secondPath + "'.  Please enter another path.");
            second.focus();
            return false
        }

        ko.mru.addFromACTextbox(first);
        ko.mru.addFromACTextbox(second);
        window.setCursor('wait');
        opener.ko.fileutils.showDiffs(firstPath, secondPath);
        window.setCursor('auto');
    } catch (e) {
        log.exception(e);
    } finally {
        if (file1 && !file1.isLocal)
            file1.close();
        if (file2 && !file2.isLocal)
            file2.close();
    }
    return true;
}

function Cancel()
{
    return true;
}

