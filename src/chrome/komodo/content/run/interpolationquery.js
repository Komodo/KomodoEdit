/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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

