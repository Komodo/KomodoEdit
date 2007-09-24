/* Copyright (c) 2002-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* A diff viewer window.
 *
 * Arguments to be passed into window.arguments[0]:
 *
 *  .diff: the diff content
 *  .title: a window title to use
 *  .message: (optional) message text to display in the view's status area
 */

//
// Globals
//
var _dw_log = ko.logging.getLogger("diff");
var _diffWindow = null;

//
// Diff window object
//
function DiffWindow()
{
    var _document = null;
    scintillaOverlayOnLoad();

    document.title = window.arguments[0].title;
    var view = document.getElementById('view');
    view.init();

    var diff;
    if (!'diff' in window.arguments[0] || !window.arguments[0].diff) {
        _dw_log.error('The diff was not specified for diff.xul');
        diff = '';
    } else {
        diff = window.arguments[0].diff;
    }
    try {
        _document = view.docSvc.createUntitledDocument("Diff"); // koIDocument
        _dw_log.debug("_document = "+_document);
        _document.addView(view);
        _document.buffer = diff;
        view.initWithBuffer(diff, "Diff");
        view.encoding = _document.encoding.python_encoding_name;
        view.scimoz.codePage = _document.codePage;
        // Force scintilla buffer to readonly mode, bug:
        //   http://bugs.activestate.com/show_bug.cgi?id=27910
        view.scimoz.readOnly = true;
        //this._languageObj = this._document.languageObj;
        view.setFocus();
    } catch(e) {
        _dw_log.exception(e);
    }

    if (window.arguments[0].message) {
        view.message = window.arguments[0].message;
    }
    window.controllers.appendController(this);
}

//
// Controller related code - handling of commands
//
DiffWindow.prototype.isCommandEnabled = function(cmdName) {
    if (cmdName == "cmd_bufferClose") {
        return true;
    }
    return false;
}

DiffWindow.prototype.supportsCommand = DiffWindow.prototype.isCommandEnabled;

DiffWindow.prototype.doCommand = function(cmdName) {
    if (cmdName == "cmd_bufferClose") {
        window.close();
        return true;
    }
    return false;
}


//
// Main loading and unloading of the diff window
//
function OnLoad() {
    try {
        _diffWindow = new DiffWindow();
    } catch(ex) {
        _dw_log.exception(ex, "error loading diff window dialog.");
    }
}

function OnUnload()
{
    window.controllers.removeController(_diffWindow);
}

