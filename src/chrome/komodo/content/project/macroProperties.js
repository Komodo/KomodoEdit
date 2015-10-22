/* ***** BEGIN LICENSE BLOCK *****
 * Version: MPL 1.1/GPL 2.0/LGPL 2.1
 * 
 * The contents of this file are subject to the Mozilla Public License
 * Version 1.1 (the "License"); you may not use this file except in
 * compliance with the License. You may obtain a copy of the License at
 * http://www.mozilla.org/MPL/
 * 
 * Software distributed under the License is distributed on an "AS IS"
 * basis, WITHOUT WARRANTY OF ANY KIND, either express or implied. See the
 * License for the specific language governing rights and limitations
 * under the License.
 * 
 * The Original Code is Komodo code.
 * 
 * The Initial Developer of the Original Code is ActiveState Software Inc.
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2007
 * ActiveState Software Inc. All Rights Reserved.
 * 
 * Contributor(s):
 *   ActiveState Software Inc
 * 
 * Alternatively, the contents of this file may be used under the terms of
 * either the GNU General Public License Version 2 or later (the "GPL"), or
 * the GNU Lesser General Public License Version 2.1 or later (the "LGPL"),
 * in which case the provisions of the GPL or the LGPL are applicable instead
 * of those above. If you wish to allow use of your version of this file only
 * under the terms of either the GPL or the LGPL, and not to allow others to
 * use your version of this file under the terms of the MPL, indicate your
 * decision by deleting the provisions above and replace them with the notice
 * and other provisions required by the GPL or the LGPL. If you do not delete
 * the provisions above, a recipient may use your version of this file under
 * the terms of any one of the MPL, the GPL or the LGPL.
 * 
 * ***** END LICENSE BLOCK ***** */
var bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
        .getService(Components.interfaces.nsIStringBundleService)
        .createBundle("chrome://komodo/locale/project/macro.properties");

xtk.include('domutils');
        
var gPartname, gKeybinding, gPart, gItem, gScintilla = null;
var gDefaultPartIconURL = null;
var gTriggerGroup, gRank, gLanguage, gTriggerCheckbox, gRunInBackground;
var log = ko.logging.getLogger("macroproperties");
var gTriggerTypes = ['trigger_startup', 'trigger_postopen', 'trigger_presave', 'trigger_postsave',
                     'trigger_preclose', 'trigger_postclose', 'trigger_quit',
                     'trigger_observer'];
var gTriggerObserverNotification, gTriggerObserverRunsInBackground;
var gPartNameLabelKeybinding;
var gPartNameLabelTrigger;
var gMacroContents;
var gOKButton, gApplyButton;
var _gPrefSvc = Components.classes["@activestate.com/koPrefService;1"].
            getService(Components.interfaces.koIPrefService);

function _getTriggerProperties(item) {
    var obj = {};
    try {
        if (item.hasAttribute('trigger_enabled')) {
            obj.trigger_enabled = item.getBooleanAttribute('trigger_enabled');
            if (obj.trigger_enabled) {
                obj.trigger = item.getStringAttribute('trigger');
                obj.rank = item.getLongAttribute('rank');
                if (obj.trigger == 'trigger_observer') {
                    obj.trigger_observer_topic = (item.hasAttribute('trigger_observer_topic')
                                                  ? item.getStringAttribute('trigger_observer_topic')
                                                  : "");
                }
            }
        } else {
            obj.trigger_enabled = false;
        }
    } catch(e) {
        log.exception(e);
        obj.trigger_enabled = false;
    }
    return obj;
}

var _gOldTriggerProperties;

function onLoad() {
    try {
        scintillaOverlayOnLoad();
        var dialog = document.getElementById("dialog-macroproperties");

        gMacroContents = document.getElementById('macrocontents');

        gOKButton = dialog.getButton("accept");
        gApplyButton = dialog.getButton("extra1");
        gApplyButton.setAttribute('label', bundle.GetStringFromName("apply"));
        gApplyButton.setAttribute('accesskey', bundle.GetStringFromName("applyAccessKey"));

        gItem = window.arguments[0].item;
        gPart = gItem;
        var language = gPart.getStringAttribute('language');
        gPartname = document.getElementById('partname');
        gPartNameLabelKeybinding = document.getElementById('partnamelabel');
        gPartNameLabelTrigger = document.getElementById('partnamelabel2');
        gTriggerGroup = document.getElementById('trigger_type');
        gTriggerCheckbox = document.getElementById('trigger_checkbox');
        gLanguage = document.getElementById('language');
        gRank = document.getElementById('rank');
        gRunInBackground = document.getElementById('async');
        if (window.arguments[0].task == 'new') {
            document.title = bundle.GetStringFromName("Create New Userscript");
            gApplyButton.setAttribute('collapsed', 'true');
        } else {
            document.title = bundle.GetStringFromName("Userscript Properties");
        }

        gKeybinding = document.getElementById('keybindings');
        gKeybinding.gKeybindingMgr = opener.ko.keybindings.manager;
        gKeybinding.part = gPart;
        gKeybinding.commandParam = gPart.id;
        gKeybinding.init();

        if (gPart.hasAttribute("name")) {
            gPartname.value = gPart.getStringAttribute('name');
            gPartNameLabelKeybinding.value = gPartname.value;
            gPartNameLabelTrigger.value = gPartname.value;
        }
        gKeybinding.updateCurrentKey();
        var text = gPart.value;

        gLanguage.selectedItem = document.getElementById(language);
        gMacroContents.scintilla.symbolMargin = false; // we don't have breakpoints
        gMacroContents.initWithBuffer(text, language);
        gMacroContents.setFoldStyle(_gPrefSvc.prefs.getStringPref("editFoldStyle"));
        gMacroContents.setFocus();
        gScintilla = gMacroContents.scimoz;
        gScintilla.useTabs = 0;
        
        // On Mac OSX, ensure the Scintilla view is visible by forcing a repaint.
        // TODO: investigate why this happens and come up with a better solution.
        // NOTE: repainting a Scintilla view by itself is not sufficient;
        // Mozilla needs to repaint the entire window.
        if (navigator.platform.match(/^Mac/)) {
            window.setTimeout(function() {
                window.resizeBy(1, 0);
                window.resizeBy(-1, 0);
            }, 10);
        }

        setupTriggers();
        gDefaultPartIconURL = window.arguments[0].imgsrc;
        update_icon(gPart.iconurl);
        UpdateField('name', true);
        if (gPart.hasAttribute('trigger') && gPart.getStringAttribute('trigger')) {
            var t = gPart.getStringAttribute('trigger');
            gTriggerGroup.selectedItem = document.getElementById(t);
        } else {
            // just setting something for the sake of setting something.
            gTriggerGroup.selectedItem = document.getElementById('trigger_postopen');
        }
        gTriggerObserverNotification = document.getElementById('trigger_observer_name');
        if (gPart.hasAttribute('trigger_observer_topic')
            && gPart.getStringAttribute('trigger_observer_topic')) {
            gTriggerObserverNotification.value = gPart.getStringAttribute('trigger_observer_topic');
            gTriggerObserverRunsInBackground = (gPart.hasAttribute('async')
                                                && gPart.getBooleanAttribute('async'));
        }

        if (! _gPrefSvc.prefs.getBooleanPref("triggering_macros_enabled")) {
            gTriggerCheckbox.setAttribute('disabled', 'true');
            gTriggerCheckbox.setAttribute('tooltiptext', bundle.GetStringFromName("Triggering of Userscripts on events has been disabled"));
        }
        if (gPart.hasAttribute('trigger_enabled') &&
            gPart.getBooleanAttribute('trigger_enabled')) {
            gTriggerCheckbox.setAttribute('checked', 'true');
            gTriggerGroup.removeAttribute('disabled');
            gTriggerObserverNotification.removeAttribute('disabled');
        } else {
            gTriggerCheckbox.removeAttribute('checked');
            gTriggerGroup.setAttribute('disabled', 'true');
            gTriggerObserverNotification.setAttribute('disabled', 'true');
        }
        if (gPart.hasAttribute('async')) {
            gRunInBackground.checked = gPart.getBooleanAttribute('async');
        } else {
            gRunInBackground.checked = false;
        }
        UpdateField('do_trigger', true);
        UpdateField('background', true);
        gPartname.focus();
        gPartname.select();
        _gOldTriggerProperties = _getTriggerProperties(gPart);
    } catch (e) {
        log.exception(e);
    }
};

function onUnload() {
    try {
        // The "close" method ensures the scintilla view is properly cleaned up.
        gMacroContents.close();
        scintillaOverlayOnUnload();
    } catch (e) {
        log.exception(e);
    }
}

function makeAppliable() {
    gApplyButton.removeAttribute('disabled');
}

function OK(event)  {
    if (!_Apply()) {
        return false;
    }
    if (window.arguments[0].task == 'new') {
        var parent = window.arguments[0].parent;
        var toolbox2 = opener.ko.toolbox2;
        if (typeof(parent)=='undefined' || !parent) {
            var parent;
            try {
                parent = toolbox2.manager.getSelectedItem();
            } catch(ex) {
                log.exception("macroProperties::OK - can't get a selected item, use the standard toolbox:\n" + ex);
                parent = null;
            }
            if (!parent) {
                parent = toolbox2.getStandardToolbox();
            }
        }
        toolbox2.addNewItemToParent(gPart, parent);
    } else if (window.arguments[0].task == 'edit') {
        //XXX Should be done through an observer.
        //XXX Reviewers: should this be done in Apply?
        opener.ko.macros.eventHandler.updateMacroHooks(gPart, _gOldTriggerProperties, _getTriggerProperties(gPart));
    }
    window.arguments[0].res = true;
    return true;
};

function Apply() {
    return _Apply();
}

function _Apply()  {
    try {
        gPart.setStringAttribute('name', gPartname.value);
        gPart.value = gScintilla.text;
        gItem.name = gPartname.value;
        var iconuri = document.getElementById('propertiestab_icon').getAttribute('src');
        gPart.iconurl = iconuri;
        gItem.iconurl = iconuri;
        opener.ko.projects.invalidateItem(gItem);
        var elt, trueOrFalse;
        if (gTriggerCheckbox.hasAttribute('checked')) {
            gPart.setBooleanAttribute('trigger_enabled', true);
            if (gTriggerGroup.selectedItem.id == 'trigger_observer') {
                var notificationTopic = 
                    gTriggerObserverNotification.value.match(/^\s*(.*?)\s*$/)[1];
                if (!notificationTopic) {
                    alert("A value is required for notification triggers");
                    gTriggerObserverNotification.focus();
                    return false;
                }
                gPart.setStringAttribute('trigger_observer_topic', notificationTopic);
            }
        } else {
            gPart.setBooleanAttribute('trigger_enabled', false);
        }
        gPart.setStringAttribute('trigger', gTriggerGroup.selectedItem.getAttribute('id'));
        gPart.setLongAttribute('rank', Number(gRank.value));
        gPart.setBooleanAttribute('async', gRunInBackground.checked);
        gPart.setStringAttribute('language', gLanguage.selectedItem.getAttribute('id'));
        var ret = gKeybinding.apply();
        if (window.arguments[0].task != 'new') {
            gPart.save();
        }
        return ret;
    } catch (e) {
        log.exception(e);
    }
    return false;
};

function updateOK() {
    try {
        if (gPartname.value == '') {
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
    } catch (e) {
        log.exception(e);
    }
}

function Cancel()  {
    if (gScintilla.modify) {
        var resp = ko.dialogs.yesNoCancel(bundle.GetStringFromName("Do you wish to save your changes"),
                               "No", // default response
                               null, // text
                               bundle.GetStringFromName("Macro was modified") //title
                               );
        if (resp == "Cancel") {
            return false;
        }
        if (resp == "Yes") {
            return OK();
        }
    }
    window.arguments[0].res= false;
    return true;
};

function updateStaticLabel() {
    gPartNameLabelKeybinding.value = gPartname.value;
    gPartNameLabelTrigger.value = gPartname.value;
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
                var name = gPartname.value;
                if (name) {
                    document.title = bundle.formatStringFromName("namedProperties", [name], 1);
                } else {
                    document.title = bundle.formatStringFromName("unnamedProperties", [gPart.prettytype], 1);
                }
                gPartNameLabelKeybinding.value = name;
                gPartNameLabelTrigger.value = name;
                changed = true;
                break;
            case 'icon':
                changed = true;
                break;
            case 'do_trigger':
                changed = true;
                var enabled = (_gPrefSvc.prefs.getBooleanPref("triggering_macros_enabled") &&
                            gTriggerCheckbox.getAttribute('checked') == 'true');
                if (enabled) {
                    gTriggerGroup.removeAttribute('disabled');
                    for (var i = 0; i < gTriggerTypes.length; i++) {
                        document.getElementById(gTriggerTypes[i]).removeAttribute('disabled');
                    }
                    gRank.removeAttribute('disabled');
                    gTriggerObserverNotification.removeAttribute('disabled');
                    if (typeof(gTriggerGroup.selectedItem) == 'undefined') {
                        var presave = document.getElementById('trigger_presave')
                        gTriggerGroup.selectedItem = presave;
                    }
                    UpdateField('trigger_type', 0);
                } else {
                    gTriggerGroup.setAttribute('disabled', 'true');
                    for (var i = 0; i < gTriggerTypes.length; i++) {
                        document.getElementById(gTriggerTypes[i]).setAttribute('disabled', 'true');
                    }
                    gRank.setAttribute('disabled', 'true');
                    gTriggerObserverNotification.setAttribute('disabled', 'true');
                    gRunInBackground.removeAttribute('disabled');
                }
                break;
            case 'trigger_type':
                switch (gTriggerGroup.selectedItem.id) {
                    case 'trigger_observer':
                        gRunInBackground.removeAttribute('disabled');
                        UpdateField('trigger_observer', false);
                        break;
                    case 'trigger_presave':
                    case 'trigger_preclose':
                    case 'trigger_quit':
                        gRunInBackground.setAttribute('disabled', 'true');
                        gRunInBackground.removeAttribute('checked');
                        break;
                    default:
                        gRunInBackground.setAttribute('disabled', 'true');
                        gRunInBackground.setAttribute('checked', 'true');
                }
                //ko.logging.dumpDOM(gRunInBackground);
                break;
            case 'trigger_observer':
                if (gTriggerObserverRunsInBackground) {
                    gRunInBackground.setAttribute('checked', 'true');
                } else {
                    gRunInBackground.removeAttribute('checked');
                }
                break;
            case 'background':
                if (gTriggerGroup.selectedItem.id == 'trigger_observer') {
                    gTriggerObserverRunsInBackground = gRunInBackground.checked;
                }
        }
        if (!initializing && changed) {
            updateOK();
        }
    } catch (e) {
        log.exception(e);
    }
}


function update_icon(URI)
{
    try {
        if (URI == gDefaultPartIconURL) {
            document.getElementById('reseticon').setAttribute('disabled', 'true');
        } else {
            if (document.getElementById('reseticon').hasAttribute('disabled')) {
                document.getElementById('reseticon').removeAttribute('disabled');
            }
        }
        document.getElementById('keybindingtab_icon').setAttribute('src', URI);
        document.getElementById('propertiestab_icon').setAttribute('src', URI);
        document.getElementById('triggertab_icon').setAttribute('src', URI);
        if (URI.indexOf('_missing.png') != -1) {
            document.getElementById('propertiestab_icon').setAttribute('tooltiptext', bundle.GetStringFromName("The custom icon specified for this X is missing", [gPart.prettytype], 1));
        } else {
            document.getElementById('propertiestab_icon').removeAttribute('tooltiptext');
        }
    } catch (e) {
        log.exception(e);
    }
}

function selectTriggerObserver() {
    if (gTriggerGroup.selectedItem != document.getElementById("trigger_observer")) {
        gTriggerGroup.selectedItem = document.getElementById("trigger_observer");
        UpdateField('trigger_type', true);
    }
}

function pick_icon(useDefault /* false */)
{
    try {
        var URI
        if (! useDefault) {
            URI = ko.dialogs.pickIcon();
            if (!URI) return;
        } else {
            URI = gDefaultPartIconURL;
        }
        update_icon(URI);
        updateOK();
    } catch (e) {
        log.exception(e);
    }
}

function SwitchLanguage(language)
{
    try {
        gMacroContents.language = language;
    } catch (e) {
        log.exception(e);
    }
}

function setupTriggers() {
    // This function fills in the UI w.r.t. what triggers the macro
    // based on the part attributes.

    var rank = 100;
    if (gPart.hasAttribute('rank')) {
        rank = gPart.getLongAttribute('rank');
    }
    document.getElementById('rank').value = String(rank);
}
