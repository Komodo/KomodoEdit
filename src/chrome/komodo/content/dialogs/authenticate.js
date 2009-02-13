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

/* Generic authentication dialog.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      .prompt         a leading description
 *      .server         server URI
 *      .username       default value for the username textbox
 *      .title          the dialog title
 *      .login          A callable object to do the login.  It will be
 *                      called with the current value and should return
 *                      true iff the value is acceptable.
 *
 *  On return window.arguments[0] has:
 *      .retval         "Login" or "Cancel" indicating how the dialog was exitted
 *  and iff .retval == "OK":
 *      .username       is the entered username
 *      .password       is the entered password
 *
 */

//---- globals

var log = ko.logging.getLogger("dialogs.authenticate");

var _gLogin = null; // Function to attempt the login.
var _gServer = null;
var _gUsingMRU = false;
var _gUsernameCache = null;
var _gEmailCache = null;
var _gPasswordCache = null;
var _bundle = Components.classes["@mozilla.org/intl/stringbundle;1"]
      .getService(Components.interfaces.nsIStringBundleService)
      .createBundle("chrome://komodo/locale/dialogs/authenticate.properties");


//---- interface routines for XUL

function OnLoad()
{
    try {
        var dialog = document.getElementById("dialog-authenticate")
        var loginButton = dialog.getButton("accept");
        var cancelButton = dialog.getButton("cancel");
        loginButton.setAttribute("label", _bundle.GetStringFromName("login.label"));
        loginButton.setAttribute("accesskey", _bundle.GetStringFromName("login.accesskey"));
        cancelButton.setAttribute("accesskey", _bundle.GetStringFromName("cancel.accesskey"));

        // .prompt
        var promptWidget = document.getElementById("prompt");
        var prompt = window.arguments[0].prompt;
        if (typeof prompt != "undefined" && prompt != null) {
            var textUtils = Components.classes["@activestate.com/koTextUtils;1"]
                                .getService(Components.interfaces.koITextUtils);
            prompt = textUtils.break_up_words(prompt, 50);
            var textNode = document.createTextNode(prompt);
            promptWidget.appendChild(textNode);
        } else {
            promptWidget.setAttribute("collapsed", "true");
        }

        // .server
        _gServer = window.arguments[0].server;
        if (typeof _gServer == "undefined") _gServer = null;
        if (_gServer) {
            document.getElementById("server-box").removeAttribute("collapsed");
            document.getElementById("server").setAttribute("value", _gServer);
        }

        // .username
        var username = window.arguments[0].username;
        if (typeof username == "undefined" || username == null) {
            username = "";
        }
        var usernameWidget = document.getElementById("username");
        usernameWidget.setAttribute("value", username);
        if (_gServer) {
            usernameWidget.setAttribute("autocompletesearchparam",
                                        "authentication_username_mru_"+_gServer);
            usernameWidget.removeAttribute("disableautocomplete");
            usernameWidget.setAttribute("enablehistory", "true");
            _gUsingMRU = true;
        }

        // .title
        if (typeof window.arguments[0].title != "undefined" &&
            window.arguments[0].title != null) {
            document.title = window.arguments[0].title;
        } else {
            document.title = _bundle.GetStringFromName("loginAs.title");
        }

        // .allowAnonymous
        if (typeof window.arguments[0].allowAnonymous != "undefined" &&
            window.arguments[0].allowAnonymous) {
            document.getElementById("anonymous").removeAttribute("collapsed");
        }

        // .validator
        var login = window.arguments[0].login;
        if (typeof login != "undefined" && login != null) {
            _gValidator = login;
        }

        window.sizeToContent();
        if (opener.innerHeight == 0) { // indicator that opener hasn't loaded yet
            dialog.centerWindowOnScreen();
        } else {
            dialog.moveToAlertPosition(); // requires a loaded opener
        }
        document.getElementById("username").focus();
    } catch(ex) {
        log.exception(ex, "Error loading authentication dialog.");
    }
    window.getAttention();
}


function ToggleAnonymous()
{
    var checked = document.getElementById("anonymous").checked;
    var passwordLabel = document.getElementById("password-label");
    var username = document.getElementById("username");
    var password = document.getElementById("password");
    if (checked) {
        _gUsernameCache = username.value;
        _gPasswordCache = password.value;
        username.value = _bundle.GetStringFromName("anonymous.value");
        username.setAttribute("disabled", "true");
        passwordLabel.setAttribute("value", _bundle.GetStringFromName("emailAddress.label"));
        passwordLabel.setAttribute("accesskey", _bundle.GetStringFromName("emailAddress.accesskey"));
        password.setAttribute("type", "text");
        password.value = _gEmailCache || "anon@anon.org";
        password.focus();
    } else {
        if (username.hasAttribute("disabled"))
            username.removeAttribute("disabled");
        username.value = _gUsernameCache || "";
        passwordLabel.setAttribute("value", _bundle.GetStringFromName("password.label"));
        passwordLabel.setAttribute("accesskey", _bundle.GetStringFromName("password.accesskey"));
        password.setAttribute("type", "password");
        _gEmailCache = password.value;
        password.value = _gPasswordCache || "";
        username.focus();
    }
}



function Login()
{
    try {
        window.arguments[0].retval = "Login";
        var usernameWidget = document.getElementById("username");
        var passwordWidget = document.getElementById("password");
        if (!_gLogin
            || _gLogin(_gServer, usernameWidget.value, passwordWidget.value)) {
            window.arguments[0].username = usernameWidget.value;
            window.arguments[0].password = passwordWidget.value;
            if (_gUsingMRU) {
                ko.mru.addFromACTextbox(usernameWidget);
            }
            return true;
        } else {
            usernameWidget.focus();
        }
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


