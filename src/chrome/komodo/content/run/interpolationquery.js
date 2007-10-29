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

/* String interpolation query dialog (see interpolate.js)
 *
 * Used when a strings being interpolated include codes requiring that the user
 * be asked for information to place in the string.
 */

var gQueries = null;


function OnLoad()
{
    var dialog = document.getElementById("dialog-interpolationquery")
    var okButton = dialog.getButton("accept");
    var cancelButton = dialog.getButton("cancel");
    okButton.setAttribute("accesskey", "o");
    cancelButton.setAttribute("accesskey", "c");

    // Process input arguments.
    if (typeof window.arguments[0].title != "undefined" &&
        window.arguments[0].title != null) {
        document.title = window.arguments[0].title;
    } else {
        document.title = "Interpolation Query";
    }
    gQueries = window.arguments[0].queries;

    // Generate UI for the queries.
    var queryRows = document.getElementById("query-rows");
    var q, label, textbox, row, hbox, i;
    try {
        for (i = 0; i < gQueries.length; i++) {
            // Want the following XUL for each query:
            //    <row align="center">
            //        <label id="query0-label"
            //               value="QUESTION"
            //               control="query0-textbox"
            //               crop="end"
            //               flex="1"/>
            //        <textbox id="query<i>-textbox"
            //                 style="min-height: 1.8em;"
            //                 flex="1"
            //                 value="<answer>"
            //                 type="autocomplete"
            //                 autocompletepopup="popupTextboxAutoComplete"
            //                 autocompletesearch="mru"
            //                 autocompletesearchparam="dialog-interpolationquery-<mruName>Mru"
            //                 maxrows="10"
            //                 enablehistory="true"
            //                 completeselectedindex="true"
            //                 tabscrolling="true"
            //                 ontextentered="this.focus();"
            //                 onfocus="this.select();"/>
            //    </row>
            //
            // unless this is a password query (q.isPassword), then we want the
            // <textbox/> to be:
            //        ...
            //        <textbox id="query<i>-textbox"
            //                 style="min-height: 1.8em;"
            //                 flex="1"
            //                 value="<answer>"
            //                 type="password"
            //                 onfocus="this.select();"/>
            //        ...
            q = gQueries[i];

            row = document.createElement("row");
            row.setAttribute("align", "center");

            label = document.createElement("label");
            label.setAttribute("id", "query"+i+"-label");
            label.setAttribute("value", q.question+":");
            label.setAttribute("control", "query"+i+"-textbox");
            label.setAttribute("crop", "end");
            label.setAttribute("flex", "1");
            row.appendChild(label);

            textbox = document.createElement("textbox");
            textbox.setAttribute("id", "query"+i+"-textbox");
            textbox.setAttribute("style", "min-height: 1.8em;");
            textbox.setAttribute("flex", "1");
            if (q.answer) {
                textbox.setAttribute("value", q.answer);
            } else {
                textbox.setAttribute("value", "");
            }
            textbox.setAttribute("onfocus", "this.select();");

            if (q.isPassword) {
                textbox.setAttribute("type", "password");
            } else {
                textbox.setAttribute("type", "autocomplete");
                textbox.setAttribute("autocompletepopup", "popupTextboxAutoComplete");
                textbox.setAttribute("autocompletesearch", "mru");
                if (q.mruName) {
                    textbox.setAttribute("autocompletesearchparam", 
                        "dialog-interpolationquery-"+q.mruName+"Mru");
                    textbox.setAttribute("enablehistory", "true");
                } else {
                    // Disable autocomplete: no mruName given.
                    textbox.setAttribute("disableautocomplete", "true");
                    textbox.removeAttribute("enablehistory"); 
                }
                textbox.setAttribute("maxrows", "10");
                textbox.setAttribute("completeselectedindex", "true");
                textbox.setAttribute("tabscrolling", "true");
                textbox.setAttribute("ontextentered", "this.focus();");
            }

            row.appendChild(textbox); 
            queryRows.appendChild(row);
        }
    } catch(ex) {
        dump("error adding interpolation query rows: "+ex+"\n");
    }

    window.sizeToContent();
    dialog.moveToAlertPosition();
}



function OK()
{
    // Store users answers to query objects.
    for (var i = 0; i < gQueries.length; i++) {
        var q = gQueries[i];
        var id = "query"+i+"-textbox";
        var queryTextbox = document.getElementById(id);
        if (queryTextbox.value) {
            q.answer = queryTextbox.value;
            if (q.mruName) {
                ko.mru.addFromACTextbox(queryTextbox);
            }
        } else {
            q.answer = "";
        }
    }

    window.arguments[0].retval = "OK";
    return true;
}


function Cancel()
{
    window.arguments[0].retval = "Cancel";
    return true;
}

