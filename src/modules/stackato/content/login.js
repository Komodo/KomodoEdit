/* Copyright (c) 2003-2011 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Generic authentication dialog.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. All these arguments are optional.
 *      .prompt         a leading description
 *      .username          default value for the username textbox
 *      .title          the dialog title
 *
 *  On return window.arguments[0] has:
 *      .retval         "Login" or "Cancel" indicating how the dialog was exitted
 *  and iff .retval == "OK":
 *      .username       is the entered username
 *      .password       is the entered password
 *
 */

var widgets = {};
function onLoad() {
    widgets.username = document.getElementById("username");
    widgets.password = document.getElementById("password");
    var obj = window.arguments[0];
    widgets.username.value = obj.username || "";
    widgets.password.value = obj.password || "";
}

function onOk()
{
    try {
        window.arguments[0].retval = true;
        var username = widgets.username.value;
        var password = widgets.password.value;
        if (!username) {
            //TODO: Disable OK in this situation
            return false;
        }
        window.arguments[0].username = username;
        window.arguments[0].password = password;
        return true;
    } catch(ex) {
        log.exception(ex, "Error running 'onOk'.");
    }
    return false;
}

function onCancel()
{
    window.arguments[0].retval = false;
    return true;
}
