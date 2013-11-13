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
 * Portions created by ActiveState Software Inc are Copyright (C) 2000-2011
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
        .createBundle("chrome://komodo/locale/pref/file-properties.properties");
var data = {};
var gEncodingSvc = Components.classes["@activestate.com/koEncodingServices;1"].
                   getService(Components.interfaces.koIEncodingServices);
const XUL_NS = "http://www.mozilla.org/keymaster/gatekeeper/there.is.only.xul";
var g_isProject;
var log = ko.logging.getLogger("pref.file-properties");
xtk.include("domutils");

function OnPreferencePageLoading(prefset) {
    try {
        g_isProject = (parent.part && parent.part.type == "project");
        data.readonly = document.getElementById("readonly");
        data.permissions_label = document.getElementById("file_permissions_label");
        data.permissions_button = document.getElementById("file_permissions_button");
        data.encoding = document.getElementById("encoding");
        data.language = document.getElementById("language");
        data.lineEndings = document.getElementById("lineEndings");
        data.bom = document.getElementById("bom");
        data.preserveLineEndings = document.getElementById("preserveLineEndings");
        data.mixedLineEndings = document.getElementById("mixedLineEndings");
        data.resetButton = document.getElementById("btn-reset");
        data.changedFields = {};
    
        if (parent.part) {
            /**
             * @type {Components.interfaces.koIFileEx}
             */
            data.file = parent.part.getFile();
        } else {
            data.file = parent.view.koDoc.file;
        }
        if (data.file && !data.file_permissions && data.file.isRemoteFile) {
            // This is a bit of a hack for remote files. Forces the file to update
            // it's stats, otherwise the permissions will not have yet been loaded,
            // making the file incorrectly look as if it has no permissions set.
            // This is occurs when the file contents have not been loaded, such as
            // for a remote file in the project tree.
            data.file.open("r");
            data.file.close();
        }
        data.file_permissions = data.file ? data.file.permissions : 0;
    
        data.prefset = prefset;
    
        initViewDependentUI();
        initFileProperties();
    
        var lang = null;
        if (parent.view) {
            lang = _getMarkupLanguage();
            if (lang) {
                data.declPrefName = "default"+lang+"Decl";
                data.nsPrefName = "default"+lang+"Namespace";
                initDocumentType(prefset);
            }
        }
        if (!lang) {
            var el = document.getElementById("markupSettings");
            el.parentNode.removeChild(el);
        }
        if (g_isProject) {
            pfi_OnPreferencePageLoading(prefset);
        }
    } catch (e) {
        log.exception(e);
    }
}

function _getMarkupLanguage() {
    var domLanguages = ["XML", "HTML", "XHTML", "XSLT"];
    var langSvc = parent.view.koDoc.languageObj;
    var found = domLanguages.indexOf(langSvc.name) >= 0 ? langSvc.name:null;
    if (!found) {
        var languages = langSvc.getSubLanguages(new Object());
        for (var i=0; i < languages.length; i++) {
            if (domLanguages.indexOf(languages[i]) >= 0) {
                found = languages[i];
                break;
            }
        }
        if (!found) return null;
    }
    return found;
}

function initDocumentType(prefset) {
    try {
        var catSvc = Components.classes["@activestate.com/koXMLCatalogService;1"].
                           getService(Components.interfaces.koIXMLCatalogService);

        catSvc.getPublicIDList(function (result, idlist) {
            try {
                var decl = null;
                if (prefset.hasPrefHere(data.declPrefName)) {
                    decl = prefset.getStringPref(data.declPrefName);
                }
                _initTypePopup(idlist, "doctypePopup", decl, /\/\/DTD/);
            } catch(e) {
                log.exception(e);
            }
        });

        catSvc.getNamespaceList(function (result, idlist) {
            try {
                var decl = null;
                if (prefset.hasPrefHere(data.nsPrefName)) {
                    decl = prefset.getStringPref(data.nsPrefName);
                }
                _initTypePopup(idlist, "namespacePopup", decl, null);
            } catch(e) {
                log.exception(e);
            }
        });
    } catch(e) {
        log.exception(e);
    }
}

function _initTypePopup(list, popupId, defaultSetting, matchRx) {
    var popup = document.getElementById(popupId);
    var selected = popup.firstChild;
    for (var i =0 ; i < list.length; i++) {
        if (matchRx && !list[i].match(matchRx)) continue;
        var el = document.createElement("menuitem");
        el.setAttribute("label", list[i]);
        popup.appendChild(el);
        if (list[i] == defaultSetting) selected = el;
    }
    popup.parentNode.selectedItem = selected;
}

function OnPreferencePageOK(prefset) {

    /**
     * Do not change anything on the view.prefs in OnPreferencePageOK, as it
     * may be erased when "prefset" is copied to view.prefs.
     *
     * Anything modifying view.prefs must be done in OnPreferencePageClosing,
     * which is after the prefset has been copied - bug 99822.
     */

    if (g_isProject) {
        pfi_OnPreferencePageOK(prefset);
    }
    try {
        var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                           getService(Components.interfaces.koILastErrorService);
        var observerSvc = Components.classes["@mozilla.org/observer-service;1"].
                          getService(Components.interfaces.nsIObserverService);

        var field, value;
        for (field in data.changedFields) {
            value = data.changedFields[field];
            log.info("updating changed field '"+field+"' to '"+value+"'\n");
            switch(field) {
            case "readonly":
                if (value != data.file.isReadOnly) {
                    var osSvc = Components.classes["@activestate.com/koOs;1"].
                                 getService(Components.interfaces.koIOs);
                    var path = data.file.displayPath;
                    try {
                        osSvc.setWriteability(path, !value);
                    } catch(ex) {
                        ko.dialogs.alert(
                            bundle.formatStringFromName("errorSettingReadonlyModeFor.message",
                            [parent.view.title, lastErrorSvc.getLastErrorMessage()], 2));
                        data.readonly.focus();
                        return false;
                    }
                    observerSvc.notifyObservers(null, "file_status_now",
                                                data.file.URI);
                }
                break;

            case "file_permissions":
                if (value != data.file.permissions) {
                    data.file.chmod(value);
                    observerSvc.notifyObservers(null, "file_status_now",
                                                data.file.URI);
                }
                break;

            case "encoding_and_or_bom":
                var encodingName = data.encoding.getAttribute("data");
                var useBOM = ((!data.bom.getAttribute("disabled") || data.bom.getAttribute("disabled") == "false")
                           && data.bom.checked);
                if (!encodingIsOK(encodingName, useBOM)) return false;
                break;

            case "language":
            case "lineEndings":
                // These are handled when the page is closing.
                break;

            default:
                log.error("Don't know how to update changed field '"+field+"'.");
            }
        }

        return true;
    } catch (ex) {
        log.exception(ex, "Error OK'ing dialog.");
    }
    return false;
}

function OnPreferencePageClosing(prefset, ok) {
    if (!ok) {
        return;
    }

    try {
        var field, value;
        for (field in data.changedFields) {
            value = data.changedFields[field];
            log.info("propogating changed field '"+field+"' to '"+value+"'\n");
            switch(field) {
            case "language":
                if (value == "" || value != parent.view.koDoc.language) {
                    parent.view.koDoc.language = value;
                    xtk.domutils.fireEvent(parent.view, 'current_view_language_changed');
                }
                break;

            case "lineEndings":
                var le;
                if (value == "EOL_LF") {
                    le = parent.view.koDoc.EOL_LF;
                } else if (value == "EOL_CR") {
                    le = parent.view.koDoc.EOL_CR;
                } else if (value == "EOL_CRLF") {
                    le = parent.view.koDoc.EOL_CRLF;
                }
                // If we've changed things, save it as a pref.
                if (parent.view.koDoc.new_line_endings != le) {
                    var eolpref = '';
                    switch (le) {
                        case parent.view.koDoc.EOL_LF: eolpref = 'LF'; break;
                        case parent.view.koDoc.EOL_CR: eolpref = 'CR'; break;
                        case parent.view.koDoc.EOL_CRLF: eolpref = 'CRLF'; break;
                        default:
                            log.error("unknown line ending: " + le);
                    }
                    if (eolpref) {
                        parent.view.prefs.setStringPref('endOfLine', eolpref);
                        if (parent.view.minimap) {
                            parent.view.minimap.prefs.setStringPref('endOfLine', eolpref);
                        }
                    }
                }
                // Make the change even if 'le' is unchanged to allow a
                // change to "Preserve Line Endings" on EOL_MIXED files to
                // correct the file.
                parent.view.koDoc.new_line_endings = le;
                if (! data.preserveLineEndings.checked) {
                    // This changes the current document's line endings.
                    parent.view.koDoc.existing_line_endings = le;
                }
                break;

            case "encoding_and_or_bom":
                var encodingName = data.encoding.getAttribute("data");
                var useBOM = ((!data.bom.getAttribute("disabled") || data.bom.getAttribute("disabled") == "false")
                           && data.bom.checked);
                applyEncodingAndBOM(encodingName, useBOM);
                xtk.domutils.fireEvent(window, 'current_view_encoding_changed');
                break;

            default:
                log.error("Don't know how to update changed field '"+field+"'.");
            }
        }

        var popup = document.getElementById("doctypePopup");
        if (popup) {
            var decl;
            if (popup.parentNode.selectedItem != popup.firstChild) {
                decl = popup.parentNode.selectedItem.getAttribute("label");
                prefset.setStringPref(data.declPrefName, decl);
            } else if (prefset.hasPrefHere(data.declPrefName)) {
                prefset.deletePref(data.declPrefName);
                if (parent.view.prefs.hasPrefHere(parent.view.prefs))
                    parent.view.prefs.deletePref(data.declPrefName);
            }
        }
        popup = document.getElementById("namespacePopup");
        if (popup) {
            if (popup.parentNode.selectedItem != popup.firstChild) {
                decl = popup.parentNode.selectedItem.getAttribute("label");
                prefset.setStringPref(data.nsPrefName, decl);
            } else if (prefset.hasPrefHere(data.nsPrefName)) {
                prefset.deletePref(data.nsPrefName);
                if (parent.view.prefs.hasPrefHere(parent.view.prefs))
                    parent.view.prefs.deletePref(data.nsPrefName);
            }
        }
    } catch (ex) {
        log.exception(ex, "Error OnPreferencePageClosing.");
    }
}

function setField(name, value)
{
    data.changedFields[name] = value;
}

function setLineEnding(value) {
    if (data.originalLineEnding != "EOL_MIXED") {
        var attrValue = (value == data.originalLineEnding).toString();
        data.preserveLineEndings.setAttribute("disabled", attrValue);
    }
    setField('lineEndings', value);
}

// This function handles the disabled/enabled state of UI elements
// depending on the language (or other view attributes).
function initViewDependentUI()  {
    if (!parent.view) {
        var el = document.getElementById("file-settings");
        el.parentNode.removeChild(el);
    } else {
        initDocumentSettings();
    }
}

function initFileProperties()
{
    try {
        var name, dirname, size, ctime, mtime, atime, readonly;

        if (!data.file) {
            name = parent.view.title;
            dirname = size = ctime = mtime = atime = "N/A";
            readonly = null; // means disabled (N/A)
        } else {
            name = data.file.baseName;

            dirname = data.file.dirName;
            size = bundle.formatStringFromName("bytes.message", [data.file.fileSize], 1);

            // Time info.
            var timeSvc = Components.classes["@activestate.com/koTime;1"].
                            getService(Components.interfaces.koITime);
            var prefSvc = Components.classes['@activestate.com/koPrefService;1'].
                            getService(Components.interfaces.koIPrefService);
            var format = data.prefset.getStringPref("defaultDateFormat");
            var timeTuple;
            timeTuple = timeSvc.localtime(data.file.createdTime, new Object());
            ctime = timeSvc.strftime(format, timeTuple.length, timeTuple);
            timeTuple = timeSvc.localtime(data.file.lastModifiedTime, new Object());
            mtime = timeSvc.strftime(format, timeTuple.length, timeTuple);
            timeTuple = timeSvc.localtime(data.file.lastAccessedTime, new Object());
            atime = timeSvc.strftime(format, timeTuple.length, timeTuple);

            // Determine read-only status.
            readonly = data.file.isReadOnly;
        }

        // Update UI with data.
        document.getElementById("properties-name").value = name;
        document.getElementById("location").value = dirname;
        document.getElementById("size").value = size;
// #if PLATFORM == "win"
        document.getElementById("created").value = ctime;
// #endif
        document.getElementById("modified").value = mtime;
        document.getElementById("accessed").value = atime;
        if (readonly == null) { // i.e. N/A
            data.readonly.checked = false;
            data.readonly.setAttribute("tooltiptext",
                    bundle.GetStringFromName("notApplicable.message"));
            data.readonly.setAttribute("disabled", "true");
            data.permissions_label.setAttribute("hidden", "true");
            data.permissions_button.setAttribute("hidden", "true");
        } else {
            if (!data.file.isRemoteFile && navigator.platform.substr(0, 3).toLowerCase() == "win") {
                /* Windows only gets to change the readonly attribute. */
                data.readonly.setAttribute("hidden", "false");
                data.permissions_label.setAttribute("hidden", "true");
                data.permissions_button.setAttribute("hidden", "true");
                data.readonly.checked = readonly;
                if (data.readonly.hasAttribute("disabled"))
                    data.readonly.removeAttribute("disabled");
                if (data.readonly.hasAttribute("tooltiptext"))
                    data.readonly.removeAttribute("tooltiptext");
            } else {
                /* Linux/Mac and remote files get to change all permissions. */
                data.readonly.setAttribute("hidden", "true");
                data.permissions_label.setAttribute("hidden", "false");
                data.permissions_button.setAttribute("hidden", "false");
                displayFilePermissions();
            }
        }
    } catch(ex) {
        log.exception(ex, "Error updating file properties.");
    }
}


function displayFilePermissions()
{
    try {
        var koIFileEx = Components.interfaces.koIFileEx;
        var label = "";
        var mode = data.file_permissions;
        label += koIFileEx.isDirectory ? "d" : "-";

        /* User permissions */
        label += mode & koIFileEx.PERM_IRUSR ? "r" : "-";
        label += mode & koIFileEx.PERM_IWUSR ? "w" : "-";
        if (mode & koIFileEx.PERM_ISUID) {
            label += mode & koIFileEx.PERM_IXUSR ? "s" : "S";
        } else {
            label += mode & koIFileEx.PERM_IXUSR ? "x" : "-";
        }

        /* Group permissions */
        label += mode & koIFileEx.PERM_IRGRP ? "r" : "-";
        label += mode & koIFileEx.PERM_IWGRP ? "w" : "-";
        if (mode & koIFileEx.PERM_ISGID) {
            label += mode & koIFileEx.PERM_IXGRP ? "s" : "S";
        } else {
            label += mode & koIFileEx.PERM_IXGRP ? "x" : "-";
        }

        /* Other permissions */
        label += mode & koIFileEx.PERM_IROTH ? "r" : "-";
        label += mode & koIFileEx.PERM_IWOTH ? "w" : "-";
        if (mode & koIFileEx.PERM_ISVTX) {
            label += mode & koIFileEx.PERM_IXOTH ? "t" : "T";
        } else {
            label += mode & koIFileEx.PERM_IXOTH ? "x" : "-";
        }
        data.permissions_label.setAttribute("value", label);
    } catch(ex) {
        log.exception(ex, "Error updating file attributes.");
    }
}


function changeFilePermissions()
{
    try {
        var args = {
            "permissions": data.file_permissions,
            "retval": 0
        };
        ko.windowManager.openDialog(
                "chrome://komodo/content/pref/file-permissions.xul",
                "Komodo:FilePermissions",
                "chrome,modal,resizable,close,centerscreen",
                args);
        if (args.retval == Components.interfaces.nsIFilePicker.returnOK) {
            setField('file_permissions', args.permissions);
            data.file_permissions = args.permissions;
            displayFilePermissions();
        }
    } catch(ex) {
        log.exception(ex, "Error updating file attributes.");
    }
}


function initDocumentSettings()
{
    if (!parent.view) return;
    try {
        // Language
        data.language.selection = parent.view.koDoc.language;

        // Encoding
        initEncoding();

        // Line endings
        var nle = parent.view.koDoc.new_line_endings;
        var lineEndingVal;
        if (nle == parent.view.koDoc.EOL_LF) {
            lineEndingVal = "EOL_LF";
        } else if (nle == parent.view.koDoc.EOL_CR) {
            lineEndingVal = "EOL_CR";
        } else if (nle == parent.view.koDoc.EOL_CRLF) {
            lineEndingVal = "EOL_CRLF";
        } else {
            lineEndingVal = null;
        }

        if (parent.view.koDoc.existing_line_endings == parent.view.koDoc.EOL_MIXED) {
            if (data.mixedLineEndings.hasAttribute("collapsed")) {
                data.mixedLineEndings.removeAttribute("collapsed");
            }
            data.originalLineEnding = "EOL_MIXED";
            // Leave data.lineEndings undefined.
            data.preserveLineEndings.setAttribute("disabled", "false");
        } else {
            data.mixedLineEndings.setAttribute("collapsed", "true");
            data.originalLineEnding = data.lineEndings.value = lineEndingVal;
            data.preserveLineEndings.setAttribute("disabled", "true");
        }
        // Always preserve the current document by default.
        data.preserveLineEndings.checked = true;

    } catch(ex) {
        log.exception(ex, "Error updating settings.");
    }
}


function resetLanguage() {
    try {
        var registry = Components.classes["@activestate.com/koLanguageRegistryService;1"].
                       getService(Components.interfaces.koILanguageRegistryService);
        var language = registry.suggestLanguageForFile(parent.view.title);
        data.language.selection = language;
        setField("language", "");  // empty string means to reset
    } catch(ex) {
        log.exception(ex, "Error resetting language.");
    }
}


function initEncoding()  {
    var enc = parent.view.koDoc.encoding;  // koIEncoding object
    var encIndex = gEncodingSvc.get_encoding_index(enc.python_encoding_name);

    // Build the menupopup.
    var menupopup = ko.widgets.getEncodingPopup(gEncodingSvc.encoding_hierarchy,
                                                true,
                                                'changeEncoding(this)'); // action
    if (encIndex == -1) {
        // Current encoding is not in the std encoding list -- prepend it.
        var menuitem = document.createElementNS(XUL_NS, 'menuitem');
        menuitem.setAttribute('data', enc.python_encoding_name);
        menuitem.setAttribute('label', enc.friendly_encoding_name);
        menuitem.setAttribute('oncommand', 'changeEncoding(this)');
        menupopup.insertBefore(menuitem, menupopup.childNodes[0]);
    }
    data.encoding.appendChild(menupopup);

    // Make sure current is selected.
    var currentItem = (encIndex == -1
                       ? menupopup.childNodes[0]
                       : document.getElementsByAttribute('data', enc.python_encoding_name)[0]);
    data.encoding.setAttribute('label', currentItem.getAttribute('label'));
    data.encoding.setAttribute('data', currentItem.getAttribute('data'));

    // Init BOM checkbox.
    data.bom.checked = enc.use_byte_order_marker;
    updateBOM(enc.encoding_info);
}


function updateBOM(encodingInfo)
{
    if (encodingInfo.byte_order_marker) {
        if (data.bom.hasAttribute("disabled"))
            data.bom.removeAttribute("disabled");
    } else {
        data.bom.setAttribute('disabled', 'true');
        data.bom.checked = false;
    }
}


function changeEncoding(item)
{
    data.encoding.setAttribute('label', item.getAttribute('label'));
    data.encoding.setAttribute('data', item.getAttribute('data'));
    var encodingName = item.getAttribute("data");
    updateBOM(gEncodingSvc.get_encoding_info(encodingName));
    setField("encoding_and_or_bom", encodingName);
}

// Called from OnPreferencePageOK, check to see if the proposed encoding
// is acceptable.
function encodingIsOK(encodingName, useBOM)
{
    if (encodingName == parent.view.koDoc.encoding.python_encoding_name) {
        // Nothing changed here, so there should be no reason to complain.
        return true;
    }
    var enc = Components.classes["@activestate.com/koEncoding;1"].
                     createInstance(Components.interfaces.koIEncoding);
    enc.python_encoding_name = encodingName;
    enc.use_byte_order_marker = useBOM;
    var question, errno, errmsg;
    var warning = parent.view.koDoc.languageObj.getEncodingWarning(enc);
    if (warning) {
        question = bundle.formatStringFromName("areYouSureThatYouWantToChangeTheEncoding.message", [warning], 1);
        if (ko.dialogs.yesNo(question, "No") != "Yes") {
            return false;
        }
    }
    try {
        if (parent.view.koDoc.canBeEncodedWithEncoding(enc)) {
            return true;
        }
        // koIDocument.canBeEncodedWithEncoding sets an error message
        // if it returns failure.
        let lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                           getService(Components.interfaces.koILastErrorService);
        errno = lastErrorSvc.getLastErrorCode();
        errmsg = lastErrorSvc.getLastErrorMessage();
    } catch(ex) {
        errno = Components.results.NS_ERROR_UNEXPECTED;
        errmsg = ex.message;
    }
    if (errno == Components.results.NS_ERROR_UNEXPECTED) {
        // koDocument.canBeEncodedWithEncoding() says this is an internal error
        var err = bundle.formatStringFromName("internalErrorSettingTheEncoding.message",
                    [parent.view.koDoc.displayPath, encodingName], 2);
        ko.dialogs.internalError(err, err+"\n\n"+errmsg, ex);
        return false;
    } else {
        question = bundle.formatStringFromName("force.conversion.message", [errmsg], 1);
        var choice = ko.dialogs.customButtons(question,
                        [bundle.GetStringFromName("force.message.one"),
                         bundle.GetStringFromName("cancel.message")],
                        bundle.GetStringFromName("cancel.message")); // default
        // If 'force conversion' is chosen, try it in applyEncodingAndBOM
        return choice == bundle.GetStringFromName("force.message.two");
    }
}

// Apply the given encoding and BOM changes to the current document.
//
function applyEncodingAndBOM(encodingName, useBOM)
{
    // Short-circuit if the encoding name is the same.
    if (encodingName == parent.view.koDoc.encoding.python_encoding_name) {
        return;
    }
    var enc = Components.classes["@activestate.com/koEncoding;1"].
                     createInstance(Components.interfaces.koIEncoding);
    enc.python_encoding_name = encodingName;
    enc.use_byte_order_marker = useBOM;
    parent.view.koDoc.encoding.use_byte_order_marker = useBOM;
    try {
        parent.view.koDoc.encoding = enc;
    } catch(ex) {
        // Try to force the encoding
        try {
            parent.view.koDoc.forceEncodingFromEncodingName(encodingName);
        } catch (ex2) {
            let err = bundle.formatStringFromName(
                              "internalErrorSettingTheEncoding.message",
                              [parent.view.koDoc.baseName, encodingName], 2);
            let errmsg = lastErrorSvc.getLastErrorMessage();
            ko.dialogs.internalError(err, err+"\n\n"+errmsg, ex2);
            return;
        }
    }
    parent.view.lintBuffer.request();
    parent.view.koDoc.isDirty = true;
}
