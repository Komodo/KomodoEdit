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


