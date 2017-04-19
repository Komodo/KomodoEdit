/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */


//Arguments to window.arguments[0] are:
//    Required:
//        item: the item being edited
//        task: 'new' or 'edit'
//        type: the type of the part ('URL', 'template', etc...)
//        src:  the chrome of the image to be used in the dialog
//    Optional:
//        valueToTextConverter: function that takes the part's 'value'
//                              and converts it to the text which is
//                              stuffed in the 'value' textbox.
//
//        textToValueConverter: function that takes the contents of the
//                              'value' textbox and converts it to what
//                              will be stuffed in the part's value.

var ko = require("ko/windows").getMain().ko;
var log = ko.logging.getLogger("simplePartProperties");

var partname, partvalue, gOKButton, keybinding, gItem, gItem, langlist, author, website, license;
var shortcut_tab, part_tab, tabs, partnamelabel, gApplyButton;
var partViewManager;
var gItemType;
var textToValueConverter = null;
var valueToTextConverter = null;
var gDefaultPartIconURL = null;

function onLoad() {
    try {
        var dialog = document.getElementById("dialog-simplepartproperties");
        gOKButton = dialog.getButton("accept");
        gApplyButton = dialog.getButton("extra1");
        gApplyButton.setAttribute('label', 'Apply');
        gApplyButton.setAttribute('accesskey', 'a');

        gItem = window.arguments[0].item;
        gItemType = gItem.type;
        if ('textToValueConverter' in window.arguments[0]) {
            textToValueConverter = window.arguments[0].textToValueConverter;
        }
        if ('valueToTextConverter' in window.arguments[0]) {
            valueToTextConverter = window.arguments[0].valueToTextConverter;
        }
        gDefaultPartIconURL = window.arguments[0].imgsrc;
        update_icon(gItem.iconurl);

        if (window.arguments[0].task == 'new') {
            document.title = "Create New " + gItem.prettytype;
            gApplyButton.setAttribute('collapsed', 'true');
        } else {
            document.title =  gItem.prettytype + " Properties";
        }

        tabs = document.getElementById('tabs');
        shortcut_tab = document.getElementById('shortcut_tab');
        part_tab = document.getElementById('part_tab');
        langlist = document.getElementById('languageList');
        langlist.selection = gItem.getStringAttribute('language');
        partname = document.getElementById('partname');
        partname.value = gItem.getStringAttribute('name');
        partvalue = document.getElementById('partvalue');
        partnamelabel = document.getElementById('partnamelabel');
        tabs.selectedTab = part_tab; // we may want to change this sometimes.
        
        author = document.getElementById('author');
        author.value = gItem.getStringAttribute('author');
        website = document.getElementById('website');
        website.value = gItem.getStringAttribute('website');
        license = document.getElementById('license');
        license.value = gItem.getStringAttribute('license');

        partkey = document.getElementById('partkey');
        description = document.getElementById('description');
        filepicker = document.getElementById('filepicker');
        filepickerZip = document.getElementById('filepicker_zip');

        if (gItemType == "folder_template") {
            filepicker.removeAttribute("collapsed");
            filepicker.addEventListener("command", function() {
                ko.filepicker.browseForDir(partvalue);
                partvalue.value = ko.uriparse.pathToURI(partvalue.value);
            });
            filepickerZip.removeAttribute("collapsed");
            filepickerZip.addEventListener("command", function() {
                ko.filepicker.browseForFile(partvalue, null, null, "Zip", ["Zip"]);
                partvalue.value = ko.uriparse.pathToURI(partvalue.value);
            });
            partkey.setAttribute("value", "URI:");
            description.textContent = "Enter the URI of a zip file, or a local folder.";
        }

        keybinding = document.getElementById('keybindings');
        keybinding.gKeybindingMgr = opener.ko.keybindings.manager;
        keybinding.part = gItem;

        keybinding.commandParam = gItem.id;
        var value = gItem.value;
        if (valueToTextConverter) {
            value = valueToTextConverter.call(this, value);
        }
        partvalue.value = value;

        keybinding.init();
        keybinding.updateCurrentKey();
        UpdateField('name', true);
        partname.focus();
        partname.select();
        updateOK();
    } catch (e) {
        log.error(e);
    }
};

function OK()  {
    if (_Apply()) {
        window.arguments[0].res = true;
    }
    if (window.arguments[0].task == 'new') {
        var parent = window.arguments[0].parent;
        opener.ko.toolbox2.addNewItemToParent(gItem, parent);
    }
    window.close();
};

function Apply() {
    _Apply();
    gApplyButton.setAttribute('disabled', 'true');
    return false;
}

function _Apply()  {
    try {
        // The keybinding needs the commandparam to be set before the application would ever work.
        var retval = keybinding.apply(); // This may return false if a keybinding is partially entered
        if (!retval) return retval;
    } catch (e) {
        opener.log.error(e);
        log.exception(e);
        dump(e + "\n");
        return false;
    }
    try {

    var value = partvalue.value;
    if (textToValueConverter) {
        value = textToValueConverter.call(this, value);
    }
    gItem.value = value;
    gItem.name = partname.value;

    var language = langlist.selection;
    if (language == "-1")
        language = "Text";

    gItem.setStringAttribute("language", language);
    gItem.setStringAttribute("author", author.value);
    gItem.setStringAttribute("website", website.value);
    gItem.setStringAttribute("license", license.value);

    var iconuri = document.getElementById('propertiestab_icon').getAttribute('src');
    gItem.iconurl = iconuri;

    opener.ko.projects.invalidateItem(gItem);
    if (window.arguments[0].task != "new") {
        gItem.save();
    }
    } catch (e) {
        opener.log.error(e);
        log.exception(e);
        alert("Internal error: " + e.message);
        return false;
    }
    return true;
};

function updateOK() {
    if (partname.value == '' || partvalue.value== '') {
        gOKButton.setAttribute('disabled', 'true');
        gApplyButton.setAttribute('disabled', 'true');
    } else {
        if (gOKButton.hasAttribute('disabled')) {
            gOKButton.removeAttribute('disabled');
        }
        if (gApplyButton.hasAttribute('disabled')) {
            gApplyButton.removeAttribute('disabled');
        }
    }
}

// Do the proper UI updates for a user change.
//  "field" (string) indicates the field to update.
//  "initializing" (boolean, optional) indicates that the dialog is still
//      initializing so some updates, e.g. enabling the <Apply> button, should
//      not be done.
function UpdateField(field, initializing /* =false */)
{
    try {
        if (typeof(initializing) == "undefined" || initializing == null) initializing = false;

        // Only take action if there was an actual change. Otherwise things like
        // the <Alt-A> shortcut when in a textbox will cause a cycle in reenabling
        // the apply button.
        var changed = false;

        switch (field) {
            case 'name':
                var name = partname.value;
                if (name) {
                    document.title = "'"+name+"' Properties";
                } else {
                    document.title = "Unnamed " + gItem.prettytype + " Properties";
                }
                partnamelabel.value = name;
                changed = true;
                break;
            case 'icon':
                changed = true;
                break;
        }

        if (!initializing && changed) {
            updateOK();
        }
    } catch (e) {
        log.exception(e);
    }
}

function Cancel()  {
    window.arguments[0].res= false;
    window.close();
};

function Help() {
    switch (gItemType) {
    case "url":
    case "URL":
        ko.help.open("urls#url-shortcuts_url-shortcut-options");
        break;
    case "template":
        ko.help.open("templates#templates_storing-templates-in-a-toolbox_template-options");
        break;
    default:
        log.error("cannot launch help: unknown part type: '"+gItemType+"'\n");
    }
};

function update_icon(URI)
{
    try {
        document.getElementById('keybindingtab_icon').setAttribute('src', URI);
        document.getElementById('propertiestab_icon').setAttribute('src', URI);
        if (URI.indexOf('_missing.png') != -1) {
            document.getElementById('propertiestab_icon').setAttribute('tooltiptext', "The custom icon specified for this " + gItem.prettytype + " is missing. Please choose another.");
        } else {
            document.getElementById('propertiestab_icon').removeAttribute('tooltiptext');
        }
    } catch (e) {
        log.exception(e);
    }
}

function pick_icon(useDefault /* false */)
{
    try {
        var URI
        if (! useDefault) {
            URI = ko.dialogs.pickIcon();
            if (!URI) return;
        }

        if (useDefault || URI == "default" || URI == "reset") {
            URI = gDefaultPartIconURL;
        }
        update_icon(URI);
        updateOK();
    } catch (e) {
        log.exception(e);
    }
}
