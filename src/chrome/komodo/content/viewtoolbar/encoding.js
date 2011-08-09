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

/**
 * View toolbar handling.
 */

if (typeof(ko) == 'undefined') {
    var ko = {};
}
if (typeof(ko.viewtoolbar)=='undefined') {
    ko.viewtoolbar = {};
}
if (typeof(ko.viewtoolbar.encoding)!='undefined') {
    ko.logging.getLogger('').warn("ko.viewtoolbar.encoding was already loaded, re-creating it.\n");
}
ko.viewtoolbar.encoding = {};

(function() {

    //---- Private variables.

    var log = ko.logging.getLogger("viewtoolbar:encoding");
    //log.setLevel(ko.logging.LOG_DEBUG);

    var viewtoolbarController;

    //---- Private routines.


    //---- Public routines.

    /**
     * Initialize the encoding menu for the given view.
     * @param {Components.interfaces.koIView} view
     * @param {DOMElement} encodingMenupopup
     */
    this.initializeMenu = function viewtoolbar_encoding_initialzeMenu(view, encodingMenupopup)
    {
        if (!view.koDoc) {
            return;
        }
        if (!encodingMenupopup.hasAttribute("encoding_menu_initialized")) {
            var encodingSvc = Components.classes["@activestate.com/koEncodingServices;1"].
                               getService(Components.interfaces.koIEncodingServices);
            // Build the menupopup.
            var tempMenupopup = ko.widgets.getEncodingPopup(encodingSvc.encoding_hierarchy,
                                                            true /* toplevel */,
                                                            'ko.viewtoolbar.encoding.change(this)'); // action
            while (tempMenupopup.childNodes.length > 0) {
                encodingMenupopup.appendChild(tempMenupopup.removeChild(tempMenupopup.firstChild));
            }
            encodingMenupopup.setAttribute("encoding_menu_initialized", "true");
        }
    }

    /**
     * Set the encoding menu for the current view.
     * @param {DOMElement} menupopup
     */
    this.change = function viewtoolbar_encoding_change(menuitem)
    {
        var view = ko.views.manager.currentView;
        if (typeof(view)=='undefined' || !view || !view.koDoc) {
            return;
        }

        var encodingName = menuitem.getAttribute("data");
        if (encodingName == view.koDoc.encoding.python_encoding_name) {
            // No change.
            return;
        }

        var enc = Components.classes["@activestate.com/koEncoding;1"].
                         createInstance(Components.interfaces.koIEncoding);
        enc.python_encoding_name = encodingName;
        enc.use_byte_order_marker = view.koDoc.encoding.use_byte_order_marker;

        var file_pref_bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
                .getService(Components.interfaces.nsIStringBundleService)
                .createBundle("chrome://komodo/locale/pref/file-properties.properties");

        var warning = view.koDoc.languageObj.getEncodingWarning(enc);
        var question = file_pref_bundle.formatStringFromName(
            "areYouSureThatYouWantToChangeTheEncoding.message", [warning], 1);
        if (warning == "" || ko.dialogs.yesNo(question, "No") == "Yes") {
            try {
                view.koDoc.encoding = enc;
                // and reset the linting
                view.lintBuffer.request();
            } catch(ex) {
                var err;
                var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                   getService(Components.interfaces.koILastErrorService);
                var errno = lastErrorSvc.getLastErrorCode();
                var errmsg = lastErrorSvc.getLastErrorMessage();
                if (errno == 0) {
                    // koDocument.set_encoding() says this is an internal error
                    err = file_pref_bundle.formatStringFromName("internalErrorSettingTheEncoding.message",
                            [view.koDoc.displayPath, encodingName], 2);
                    ko.dialogs.internalError(err, err+"\n\n"+errmsg, ex);
                } else {
                    question = file_pref_bundle.formatStringFromName("force.conversion.message", [errmsg], 1);
                    var choice = ko.dialogs.customButtons(question,
                            [file_pref_bundle.GetStringFromName("force.message.one"),
                             file_pref_bundle.GetStringFromName("cancel.message")],
                             file_pref_bundle.GetStringFromName("cancel.message")); // default
                    if (choice == file_pref_bundle.GetStringFromName("force.message.two")) {
                        try {
                            view.koDoc.forceEncodingFromEncodingName(encodingName);
                        } catch (ex2) {
                            err = file_pref_bundle.formatStringFromName(
                                    "theSampleProjectCouldNotBeFound.message",
                                    [view.koDoc.baseName, encodingName], 2);
                            ko.dialogs.internalError(err, err+"\n\n"+errmsg, ex);
                        }
                    }
                }
            }
        }
    }

    /**
     * Update the 'encoding' label in the view's toolbar.
     * @param {Components.interfaces.koIView} view
     */
    this.updateLabel = function viewtoolbar_encoding_updateLabel(view) {
        var encodingWidget;
        try {
            log.debug("update()");
            encodingWidget = view.toolbar_encoding;
            if (!encodingWidget)
                return;
            if (!view.koDoc) {
                encodingWidget.removeAttribute("label");
                return;
            }
            var encoding = view.koDoc.encoding.short_encoding_name;
            encodingWidget.setAttribute("label", encoding);
        } catch(ex) {
            log.exception(ex);
            if (encodingWidget) {
                encodingWidget.removeAttribute("label");
            }
        }
    }

    //---- end View encoding namespace.


    this.initialize = function viewtoolbar_initialize()
    {
        log.debug("initialize()");
        try {
            ko.main.addWillCloseHandler(ko.viewtoolbar.finalize);
            //window.addEventListener('current_view_changed', ko.viewtoolbar.update, false);
            //var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
            //                getService(Components.interfaces.nsIObserverService);
            //obsSvc.addObserver(ko.viewtoolbar, 'codeintel_buffer_scanned',false);
            //viewtoolbarController = new ViewToolbarController();
            //window.controllers.appendController(viewtoolbarController);
        } catch(ex) {
            log.exception(ex);
        }
    }

    this.finalize = function viewtoolbar_finalize()
    {
        log.debug("finalize()");
        try {
            //window.removeEventListener('current_view_changed', ko.viewtoolbar.update, false);
            //var obsSvc = Components.classes["@mozilla.org/observer-service;1"].
            //                getService(Components.interfaces.nsIObserverService);
            //obsSvc.removeObserver(ko.viewtoolbar, 'codeintel_buffer_scanned');
            //window.controllers.removeController(viewtoolbarController);
        } catch(ex) {
            log.exception(ex);
        }
    }

    //---- The controller for the sectionlist commands.

    function ViewToolbarController() {
    }
    // The following two lines ensure proper inheritance (see Flanagan, p. 144).
    ViewToolbarController.prototype = new xtk.Controller();
    ViewToolbarController.prototype.constructor = ViewToolbarController;

    //ViewToolbarController.prototype.is_cmd_showviewtoolbar_supported = function() {
    //    return ko.prefs.getBooleanPref("codeintel_enabled");
    //}
    //ViewToolbarController.prototype.is_cmd_showviewtoolbar_enabled = function() {
    //    var view = ko.views.manager.currentView;
    //    return view && view.getAttribute("type") == "editor";
    //}
    //ViewToolbarController.prototype.do_cmd_showSectionList = function() {
    //    var view = ko.views.manager.currentView;
    //    if (view) {
    //        view.sectionlist.open();
    //    }
    //}

}).apply(ko.viewtoolbar.encoding);

//window.addEventListener("load", ko.viewtoolbar.encoding.initialize, false);
