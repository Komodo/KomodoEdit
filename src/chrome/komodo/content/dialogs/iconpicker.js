/* Copyright (c) 2003-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* A dialog to let the user pick an icon, either from a standard set of
   PNG files which Komodo ships with, or from a file the user has on
   his/her filesystem.

   The object returned has up to two properties:
    - retval: if "OK", then icon was picked.
    - value: if retval is "OK", then the URL of the selected file.
 */

var log = ko.logging.getLogger("dialogs.iconpicker");
//log.setLevel(ko.logging.LOG_DEBUG);

var obj;
var gCurrentURI;
var files;
var os = Components.classes["@activestate.com/koOs;1"].getService();

function OnLoad()
{
    try {
        obj = window.arguments[0];
        var dialog = document.getElementById("dialog-iconpicker");
        var okButton = dialog.getButton("accept");
        okButton.setAttribute("accesskey", "o");
        var customButton = dialog.getButton("extra1");
        customButton.setAttribute("label", "Choose Other...");
    } catch (e) {
        log.exception(e);
    }
}

function ValidatedPickIcon(uri)
{
    try {
        Pick_Icon(uri);
        OK();
        window.close();
    } catch (e) {
        log.exception(e);
    }
}

function Pick_Icon(uri) {
    try {
        gCurrentURI = uri;
        document.getElementById('icon32').setAttribute('src', uri);
        document.getElementById('icon16').setAttribute('src', uri);
        var os_path = Components.classes["@activestate.com/koOsPath;1"].getService();
        document.getElementById('iconlabel').setAttribute('value', os_path.withoutExtension(ko.uriparse.baseName(uri)));
    } catch (e) {
        log.exception(e);
    }
}

function selectIconFamily(event) {
    var selected = document.getElementById('icon-families').selectedItem;
    dump(selected.getAttribute('src')+"\n");
    document.getElementById('iframe').setAttribute('src', selected.getAttribute('src'));
}

function OK()
{
    obj.value = gCurrentURI;
    obj.retval = "OK";
    return true;
}

function PickCustom()
{
    var path = ko.filepicker.openFile(null, null, 'Select an Icon File',
                                   'Icon', ['Icon', 'All']);
    if (!path) return;
    Pick_Icon(ko.uriparse.localPathToURI(path));
}

function Cancel()
{
    obj.retval = "Cancel";
    return true;
}

