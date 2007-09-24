/* Copyright (c) 2003-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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


//---- interface routines for XUL

function OnLoad()
{
    try {
        var dialog = document.getElementById("dialog-authenticate")
        var loginButton = dialog.getButton("accept");
        var cancelButton = dialog.getButton("cancel");
        loginButton.setAttribute("label", "Login");
        loginButton.setAttribute("accesskey", "L");
        cancelButton.setAttribute("accesskey", "C");

        // .prompt
        var promptWidget = document.getElementById("prompt");
        var prompt = window.arguments[0].prompt;
        if (typeof prompt != "undefined" && prompt != null) {
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
            document.title = "Login As";
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
        username.value = "anonymous";
        username.setAttribute("disabled", "true");
        passwordLabel.setAttribute("value", "Email Address:");
        passwordLabel.setAttribute("accesskey", "E");
        password.setAttribute("type", "text");
        password.value = _gEmailCache || "anon@anon.org";
        password.focus();
    } else {
        if (username.hasAttribute("disabled"))
            username.removeAttribute("disabled");
        username.value = _gUsernameCache || "";
        passwordLabel.setAttribute("value", "Password:");
        passwordLabel.setAttribute("accesskey", "P");
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


