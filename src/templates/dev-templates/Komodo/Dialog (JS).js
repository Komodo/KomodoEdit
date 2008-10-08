/* Copyright (C) 2004-[[%date:%Y]] ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* ...description of dialog...
 *
 */

var log = getLoggingMgr().getLogger("[[%tabstop:loggerName]]");
//log.setLevel(LOG_DEBUG);


//---- interface routines for XUL

function OnLoad()
{
    var dialog = document.getElementById("dialog");
    var okButton = dialog.getButton("accept");
    okButton.setAttribute("accesskey", "o");
    var cancelButton = dialog.getButton("cancel");
    cancelButton.setAttribute("accesskey", "c");
    
    //...
    //window.sizeToContent();
    //dialog.moveToAlertPosition();
}


function OK()
{
    [[%tabstop://...]]
    return true;
}

function Cancel()
{
    [[%tabstop://...]]
    return true;
}

