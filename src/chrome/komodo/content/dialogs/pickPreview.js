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

/* Special dialog to choose how to preview a given file.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0].
 *      .url            The URL for which to chose a preview.
 *      .language       (optional) language of the given URL. If not specified
 *                      it will be guessed from the filename.
 *      .mode           One of "previewing" (default) or "setting" indicating
 *                      for what immediate purpose the preview path is
 *                      being sought.
 *
 *  On return window.arguments[0] has:
 *      .retval         "Preview"/"OK" or "Cancel" indicating how the
 *                      dialog was exitted.
 *  and iff .retval == "Preview":
 *      .preview        URL to preview.
 *      .remember       (iff mode=="previewing") a boolean indicating if
 *                      this setting should be remembered for this URL.
 */

//---- globals

var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/dialogs/pickPreview.properties");

var log = ko.logging.getLogger("dialogs.pickPreview");
var widgets = {}; // cache of DOM nodes for dialog.
var gURL = null; // the URL for which to pick a preview URL
var gBasename = null;
var gMode = null;


//---- interface routines for XUL

function OnLoad()
{
    try {
        gMode = window.arguments[0].mode;
        if (typeof gMode == "undefined" || gMode == null) gMode = "previewing";
        var browserType = window.arguments[0].browserType;

        var dialog = document.getElementById("dialog-pickpreview")
        widgets.okButton = dialog.getButton("accept");
        if (gMode == "previewing") {
            widgets.okButton.setAttribute("label",
                                          _bundle.GetStringFromName("previewButton.label"));
            widgets.okButton.setAttribute("accesskey",
                                          _bundle.GetStringFromName("previewButton.accesskey"));
        } else if (gMode == "setting") {
            widgets.okButton.setAttribute("label",
                                          _bundle.GetStringFromName("okButton.label"));
            widgets.okButton.setAttribute("accesskey",
                                          _bundle.GetStringFromName("okButton.accesskey"));
        } else {
            throw new Error("Invalid mode value: '"+gMode+"'");
        }
        widgets.cancelButton = dialog.getButton("cancel");
        widgets.cancelButton.setAttribute("label",
                                          _bundle.GetStringFromName("cancelButton.label"));
        widgets.cancelButton.setAttribute("accesskey",
                                          _bundle.GetStringFromName("cancelButton.accesskey"));

        widgets.promptDesc = document.getElementById("prompt");
        widgets.useWhichRadiogroup = document.getElementById("use-which-file");
        widgets.useThisRadio = document.getElementById("use-this-file");
        widgets.useAnotherRadio = document.getElementById("use-another-file");
        widgets.browseButton = document.getElementById("browse-button");
        widgets.otherFileTextbox = document.getElementById("other-file");
        widgets.browserMenulist = document.getElementById("browser-select-menulist");
        widgets.browserMenupopup = document.getElementById("browser-select-menupopup");
        widgets.rememberCheckbox = document.getElementById("remember");

        gURL = window.arguments[0].url;
        gBasename = opener.ko.uriparse.baseName(gURL);
        var language = window.arguments[0].language;
        if (typeof language == "undefined" || language == null) {
            var langRegistry = Components.classes["@activestate.com/koLanguageRegistryService;1"]
                    .getService(Components.interfaces.koILanguageRegistryService);
            language = langRegistry.suggestLanguageForFile(gBasename);
        }

        // Title
        document.title = _bundle.formatStringFromName("previewInBrowser", [gBasename], 1);

        // Prompt
        var prompt = _bundle.formatStringFromName("selectAFileOrUrlToUseToPreview", [gBasename], 1);
        widgets.promptDesc.appendChild(document.createTextNode(prompt));

        var mapped = ko.uriparse.getMappedPath(gURL);
        if (mapped != gURL) {
            widgets.otherFileTextbox.value = mapped;
        }
    
        // Language-dependent UI.
        if (language == "HTML" || language == "XML" /* ...others? */) {
            widgets.useWhichRadiogroup.selectedItem = widgets.useThisRadio;
            widgets.okButton.focus();
        } else {
            widgets.useWhichRadiogroup.selectedItem = widgets.useAnotherRadio;
            //widgets.useThisRadio.setAttribute("disabled", "true");
            widgets.otherFileTextbox.focus();
        }
        UpdateAnotherGroup();
        LoadAvailableBrowsers(browserType);

        if (gMode == "setting") {
            widgets.rememberCheckbox.setAttribute("collapsed", "true");
        }

        window.sizeToContent();
        if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
            dialog.centerWindowOnScreen();
        } else {
            dialog.moveToAlertPosition(); // requires a loaded opener
        }
    } catch(ex) {
        log.exception(ex, "Error loading pickPreview dialog.");
    }
}


function UpdateAnotherGroup()
{
    // Update the "Another File" group for a change in the radio buttons
    // selection.
    try {
        var useWhich = widgets.useWhichRadiogroup.value;
        if (useWhich == "use-this") {
            widgets.otherFileTextbox.setAttribute("disabled", "true");
            widgets.browseButton.setAttribute("disabled", "true");
            if (widgets.okButton.hasAttribute("disabled"))
                widgets.okButton.removeAttribute("disabled");
        } else /* useWhich == "use-another" */ {
            if (widgets.otherFileTextbox.hasAttribute("disabled"))
                widgets.otherFileTextbox.removeAttribute("disabled");
            if (widgets.browseButton.hasAttribute("disabled"))
                widgets.browseButton.removeAttribute("disabled");
            if (!widgets.otherFileTextbox.value) {
                widgets.okButton.setAttribute("disabled", "true");
            }
        }
    } catch(ex) {
        log.exception(ex, "Error updating 'another file' group.");
    }
}


function LoadAvailableBrowsers(browserType)
{
    try {
        var popup = widgets.browserMenupopup;
        // Only need to do this once.
        if (popup.childNodes.length > 0)
            return;

        // Load the menuitems, though we must remove the oncommand attribute.
        ko.uilayout.populatePreviewToolbarButton(popup);
        var menuitem = popup.firstChild;
        var selectedItem = null;
        while (menuitem) {
            if (browserType && menuitem.getAttribute("value") == browserType) {
                selectedItem = menuitem;
            }
            menuitem.removeAttribute("oncommand");
            menuitem = menuitem.nextSibling;
        }
        if (selectedItem) {
            widgets.browserMenulist.selectedItem = selectedItem;
        }
    } catch(ex) {
        log.exception(ex, "Error loading the browser selections.");
    }
}


function Browse()
{
    try {
        // Default to the current textbox entry, fallback to directory
        // of given URL.
        var defaultDir, defaultFile;
        if (widgets.otherFileTextbox.value) {
            defaultDir = null;
            defaultFile = widgets.otherFileTextbox.value;
        } else {
            var localPath = opener.ko.uriparse.URIToLocalPath(gURL);
            defaultDir = opener.ko.uriparse.dirName(localPath);
            defaultFile = null;
        }
        var path = ko.filepicker.browseForFile(
                    defaultDir, // default dir
                    defaultFile, // default filename
                    _bundle.formatStringFromName("selectFileToPreview", [gBasename], 1), // title
                    "HTML", // default filter name
                    ["HTML", "XML", "All"]); // allowed filters
        if (path != null) {
            widgets.otherFileTextbox.value = path;
            UpdateOtherFileTextbox();
            widgets.okButton.focus();
        } else {
            widgets.otherFileTextbox.focus();
        }
    } catch(ex) {
        log.exception(ex, "Error browsing for a preview file.");
    }
}


function UpdateOtherFileTextbox()
{
    // Update as required for a change in the "other file" textbox element.
    try {
        if (widgets.otherFileTextbox.value) {
            if (widgets.okButton.hasAttribute("disabled"))
                widgets.okButton.removeAttribute("disabled");
        } else {
            widgets.okButton.setAttribute("disabled", "true");
        }
    } catch(ex) {
        log.exception(ex, "Error updating for 'other file' textbox.");
    }
}


function Preview()
{
    try {
        window.arguments[0].retval = widgets.okButton.getAttribute("label");

        var preview;
        if (widgets.useWhichRadiogroup.value == "use-another") {
            preview = widgets.otherFileTextbox.value;

            var koFileEx = Components.classes["@activestate.com/koFileEx;1"]
                            .createInstance(Components.interfaces.koIFileEx);

            // If the preview is relative then prefix the dirname of the
            // given URL.
            // XXX koIFileEx doesn't provide this ability.
            koFileEx.URI = preview;
            if (koFileEx.isLocal) {
                var osPathSvc = Components.classes["@activestate.com/koOsPath;1"]
                                .createInstance(Components.interfaces.koIOsPath);
                if (! osPathSvc.isabs(preview)) {
                    preview = opener.ko.uriparse.dirName(gURL) + "/" + preview;
                    preview = osPathSvc.normpath(preview);
                }
            }

            // If the preview is a local file, ensure that it exists.
            koFileEx.URI = preview;
            if (koFileEx.isLocal && !koFileEx.exists) {
                ko.dialogs.alert(_bundle.formatStringFromName("doesNotExist", [preview], 1));
                widgets.otherFileTextbox.focus();
                return false;
            }
        } else {
            preview = gURL;
        }

        window.arguments[0].preview = preview;
        window.arguments[0].browserType = widgets.browserMenulist.value;
        if (gMode == "previewing") {
            window.arguments[0].remember = widgets.rememberCheckbox.checked;
        }
        return true;
    } catch(ex) {
        log.exception(ex, "Error running 'Login'.");
    }
    return false;
}


function Cancel()
{
    window.arguments[0].retval = "Cancel";
    return true;
}


