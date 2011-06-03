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

/* Undo a "Replace All in Files" operation.
 *
 * Usage:
 *  All input args are via an object passed in and out as the first window
 *  argument: window.arguments[0].
 *      .journal_id     Identifier for the journal (which has the info
 *                      necessary to perform the undo).
 *
 * On return, window.arguments[0] has:
 *      .retval         A boolean: "true" means undo was successful,
 *                      "false" means undo failed or was aborted.
 */

xtk.include("controller");

var log = ko.logging.getLogger("find.undorepl");
//log.setLevel(ko.logging.LOG_DEBUG);

var widgets = null; // object storing interesting XUL element references

var _g_find_svc = null;
var _g_controller = null;   // UndoReplaceController instance managing this dialog's UI.
var _g_undoer = null;


//---- interface routines for XUL

function on_load()
{
    try {
        _g_find_svc = Components.classes["@activestate.com/koFindService;1"]
                      .getService(Components.interfaces.koIFindService);

        _init_widgets();
        _init();

        window.sizeToContent();
        widgets.dialog.moveToAlertPosition();
    } catch (ex) {
        log.exception(ex);
    }
}


function accept()
{
    window.close();
    return false;
}



//---- internal support stuff
    
function _init_widgets()
{
    widgets = new Object();
    widgets.dialog = document.getElementById("dialog-undo-repl");
    widgets.accept_btn = widgets.dialog.getButton("accept");

    widgets.summary_desc = document.getElementById("summary-desc");
    widgets.repls = document.getElementById("repls");
    widgets.status_img = document.getElementById("status-img");
    widgets.status_desc = document.getElementById("status-desc");
}

function _init()
{
    widgets.accept_btn.setAttribute("label", "Close")
    widgets.accept_btn.setAttribute("accesskey", "s");
    widgets.accept_btn.setAttribute("disabled", true);

    var async_svc = Components.classes["@activestate.com/koAsyncService;1"]
            .getService(Components.interfaces.koIAsyncService);
    widgets.status_img.setAttribute("src", async_svc.asynchronous_icon_url);

    // Hook up and start the "Replace in Files" process.
    var args = window.arguments[0];
    _g_controller = new UndoReplaceController();
    _g_undoer = _g_find_svc.undoreplaceallinfiles(
        args.journal_id, _g_controller);
    widgets.repls.treeBoxObject.view = _g_undoer;
    _g_undoer.start();
}




function _disable_widget(widget) {
    widget.setAttribute("disabled", "true");
}
function _enable_widget(widget) {
    if (widget.hasAttribute("disabled")) {
        widget.removeAttribute("disabled");
    }
}

function _clear_desc(widget) {
    // Clear text nodes from the current panel <description>.
    while (widget.firstChild) {
        widget.removeChild(widget.firstChild);
    }
}
function _set_desc(widget, text) {
    _clear_desc(widget);
    widget.appendChild(document.createTextNode(text));
}


//---- Controller component for koIFindService to manage the UI.

function UndoReplaceController()
{
    this.log = log;
}
UndoReplaceController.prototype.constructor = xtk.Controller;

UndoReplaceController.prototype.QueryInterface = function(iid) {
    if (!iid.equals(Components.interfaces.koIUndoReplaceController) &&
        !iid.equals(Components.interfaces.nsISupports)) {
        throw Components.results.NS_ERROR_NO_INTERFACE;
    }
    return this;
}


UndoReplaceController.prototype.set_summary = function(summary)
{
    try {
        _set_desc(widgets.summary_desc, summary);
    } catch(ex) {
        this.log.exception(ex);
    }
}

UndoReplaceController.prototype.report = function(num_hits, num_paths)
{
    try {
        var hits_s_str = (num_hits == 1 ? "": "s");
        var paths_s_str = (num_paths == 1 ? "": "s");
        _set_desc(widgets.status_desc,
            num_hits + " replacement" + hits_s_str
            + " undone in " + num_paths
            + " file" + paths_s_str);
    } catch(ex) {
        this.log.exception(ex);
    }
}

UndoReplaceController.prototype.error = function(errmsg)
{
    try {
        widgets.status_img.setAttribute("src",
            "chrome://famfamfamsilk/skin/icons/exclamation.png");
        _set_desc(widgets.status_desc,
                  "The undo failed.\n"+errmsg);
        
        // Dev Note: *Want* to collapse the tree (widgets.repls) but that
        // just doesn't work. Don't know why <tree>'s are special.
        //_collapse_widget(widgets.repls);
        //_hide_widget(widgets.repls);

        window.arguments[0].retval = false;
        widgets.accept_btn.removeAttribute("disabled");
    } catch(ex) {
        this.log.exception(ex);
    }
}

UndoReplaceController.prototype.done = function()
{
    try {
        widgets.status_img.setAttribute("src",
            "chrome://famfamfamsilk/skin/icons/accept.png");

        window.arguments[0].retval = true;
        widgets.accept_btn.removeAttribute("disabled");
    } catch(ex) {
        this.log.exception(ex);
    }
}


