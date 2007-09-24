/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*-
 *
 * A quick dialog to ask the user for file association preferences. It is
 * intended to:
 *  - Encourage file associations to file types that Komodo excels at
 *  - Be automatically run once on first run of a Komodo version after this one
 *    (i.e. When the user installs Komodo 2.3 is will run once. If they upgrade
 *    later to, say, Komodo 3.0 this will NOT run again.
 *
 * Usage:
 *  All dialog interaction is done via an object passed in and out as the first
 *  window argument: window.arguments[0]. The input arguments are optional.
 *      .editAssocs     is a mapping of extensions to booleans, indicating if
 *                      an "Edit" association is wanted for that extension
 *      .editWithAssocs is a mapping of extensions to booleans, indicating if
 *                      an "Edit with Komodo" association is wanted for that
 *                      extension
 *  On return window.arguments[0] has:
 *      .retval         "OK" or "Cancel" indicating how the dialog was exitted
 *  and iff .retval == "OK":
 *      .editAssocs     is a mapping of extensions to booleans, indicating if
 *                      an "Edit" association is wanted for that extension
 *      .editWithAssocs is a mapping of extensions to booleans, indicating if
 *                      an "Edit with Komodo" association is wanted for that
 *                      extension
 *
 */

//---- interface routines for setupFileAssociations.xul

function OnLoad()
{
    var ext, id, checkbox;

    if (typeof window.arguments[0].editAssocs != "undefined" &&
        window.arguments[0].editAssocs != null) {
        var editAssocs = window.arguments[0].editAssocs;
        for (ext in editAssocs) {
            id = "edit-"+ext;
            checkbox = document.getElementById(id);
            if (checkbox) {
                checkbox.checked = editAssocs[ext];
            }
        }
    }

    if (typeof window.arguments[0].editWithAssocs != "undefined" &&
        window.arguments[0].editWithAssocs != null) {
        var editWithAssocs = window.arguments[0].editWithAssocs;
        for (ext in editWithAssocs) {
            id = "edit-with-"+ext;
            checkbox = document.getElementById(id);
            if (checkbox) {
                checkbox.checked = editWithAssocs[ext];
            }
        }
    }
}


function OnUnload()
{
    if (typeof window.arguments[0].retval == "undefined") {
        // This happens when "X" window close button is pressed.
        window.arguments[0].retval = "Cancel";
    } else {
        var i, ext, checkbox;

        window.arguments[0].editAssocs = {};
        var editCheckboxes = document.getElementById("edit-checkboxes")
                                     .getElementsByTagName("checkbox");
        for (i=0; i < editCheckboxes.length; i++) {
            checkbox = editCheckboxes[i];
            ext = checkbox.getAttribute("ext");
            window.arguments[0].editAssocs[ext] = checkbox.checked;
        }

        window.arguments[0].editWithAssocs = {};
        var editWithCheckboxes = document.getElementById("edit-with-checkboxes")
                                         .getElementsByTagName("checkbox");
        for (i=0; i < editWithCheckboxes.length; i++) {
            checkbox = editWithCheckboxes[i];
            ext = checkbox.getAttribute("ext");
            window.arguments[0].editWithAssocs[ext] = checkbox.checked;
        }
    }
}


function ToggleEditCheckbox()
{
    // Do the necessary updates when a user (un)checks the given checkbox.
    var groupSelectCheckbox = document.getElementById("edit-group-select");
    groupSelectCheckbox.setAttribute("checked", false);
}


function ToggleEditGroupSelectCheckbox()
{
    var checked = document.getElementById("edit-group-select").checked;
    var checkboxes = document.getElementById("edit-checkboxes")
                             .getElementsByTagName("checkbox");
    for (var i=0; i < checkboxes.length; i++) {
        checkboxes[i].setAttribute("checked", checked);
    }
}


function ToggleEditWithCheckbox()
{
    // Do the necessary updates when a user (un)checks the given checkbox.
    var groupSelectCheckbox = document.getElementById("edit-with-group-select");
    groupSelectCheckbox.setAttribute("checked", false);
}


function ToggleEditWithGroupSelectCheckbox()
{
    var checked = document.getElementById("edit-with-group-select").checked;
    var checkboxes = document.getElementById("edit-with-checkboxes")
                             .getElementsByTagName("checkbox");
    for (var i=0; i < checkboxes.length; i++) {
        checkboxes[i].setAttribute("checked", checked);
    }
}


function OK()
{
    window.arguments[0].retval = "OK";
    window.close();
}


function Cancel()
{
    window.arguments[0].retval = "Cancel";
    window.close();
}


