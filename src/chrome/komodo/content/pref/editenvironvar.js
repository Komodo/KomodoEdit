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

var obj = null; // window input/output

function SetWindowLocation()
{
   var gLocation = document.getElementById("location");
   if (gLocation)
   {
     var mainWindow = getMainWindow();
     window.screenX = Math.max(0, Math.min(mainWindow.screenX + Number(gLocation.getAttribute("offsetX")),
                                           screen.availWidth - window.outerWidth));
     window.screenY = Math.max(0, Math.min(mainWindow.screenY + Number(gLocation.getAttribute("offsetY")),
                                           screen.availHeight - window.outerHeight));
  }
}

function SaveWindowLocation()
{
   var gLocation = document.getElementById("location");
   if (gLocation)
   {
     var mainWindow = getMainWindow();
     var newOffsetX = window.screenX - mainWindow.screenX;
     var newOffsetY = window.screenY - mainWindow.screenY;
     gLocation.setAttribute("offsetX", window.screenX - mainWindow.screenX);
     gLocation.setAttribute("offsetY", window.screenY - mainWindow.screenY);
   }
}

/* General startup routine for preferences dialog.
 *  Place all necessary modifications to pref tree here.
 */
function Startup()
{
    var name = document.getElementById("VarName");
    var value = document.getElementById("VarValue");
    document.getElementById("VarPaths").init();
    // The following selects the default selection (see preftree.xul for the
    // ids of the treeitems to choose from) if an argument is passed in,
    // otherwise loads it from a preference.

    if (window.arguments && window.arguments[0] != null) {
        obj = window.arguments[0];
        name.setAttribute("value", obj.name);
        value.setAttribute("value", obj.value);
        if (obj.name == "") {
            name.select();
        } else {
            value.select();
        }
    }
    obj.res = "cancel";  // default response

    SetWindowLocation();
}

function doUnLoad()
{
    SaveWindowLocation();
}

function doOk()
{
    try {
        window.arguments[0].name = document.getElementById("VarName").value;
        var deck = document.getElementById("VarDeck");
        if (deck.selectedIndex == 0) {
            window.arguments[0].value = document.getElementById("VarValue").value;
        } else {
            window.arguments[0].value = document.getElementById("VarPaths").getData();
        }
        if (obj.name == "") {
            ko.dialogs.alert("You must specify a variable name.");
            document.getElementById("VarName").focus();
            return false;
        }
        window.arguments[0].res = "ok";
        return true;
    } catch (e) {
        dump(e);
        //log.exception(e);
    }
    return true;
}

function doCancel()
{
    obj.res = "cancel";
    //window.arguments[0] = obj;
    return true;
}

function doPathVar()
{
    var textField = document.getElementById("VarValue");
    var deck = document.getElementById("VarDeck");
    var list = document.getElementById("VarPaths");
    var pathButton = document.getElementById("pathButton");
    if (deck.selectedIndex == 0) {
        list.setAttribute('collapsed','false');
        list.setData(textField.value);
        deck.selectedIndex = 1;
        pathButton.setAttribute("class", "less-icon button-toolbar-a");
    } else {
        var data = list.getData();
        textField.setAttribute('value', data);
        textField.value = data;
        deck.selectedIndex = 0;
        list.setAttribute('collapsed','true');
        pathButton.setAttribute("class", "more-icon button-toolbar-a");
    }
    window.sizeToContent();
}


