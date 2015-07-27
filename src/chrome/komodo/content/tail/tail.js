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

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

xtk.include("domutils");

var tail;
var intervalId = -1;
var mydata = new Object();
mydata.wcreator = null;
mydata.url = null;
var taillog = ko.logging.getLogger('tail');
var fileEx;
var gDoc;
var gView;

function TailOnLoad() {
    try {
        scintillaOverlayOnLoad();
        taillog.debug('TailOnLoad\n');
        if (!  window.arguments && !window.arguments[0]) {
            alert("Error in TailOnLoad: should have argument to OnLoad!");
        }
        gView = document.getElementById("view");
        var url = window.arguments[0];
        var documentService = Components.classes["@activestate.com/koDocumentService;1"].getService();
        gDoc = documentService.createDocumentFromURI(url);
        gDoc.addReference();
        //gDoc.addView(gView);
        if (!gDoc) alert('no doc');
        gDoc.load();
        var buffer = gDoc.buffer;
        gView.initWithBuffer(buffer, gDoc.language);
        gView.scimoz.gotoLine(gView.scimoz.lineCount-1);
        var filepath = ko.uriparse.URIToLocalPath(url);
        document.title = 'Watch: '+ko.uriparse.baseName(url) + ' ('+ko.uriparse.dirName(filepath)+')';
        var dh = document.getElementById('dialogheader');
        dh.setAttribute('value',filepath);
        window.setInterval('CheckFile()', 200);
        // On Mac OSX, ensure the Scintilla view is visible by forcing a repaint.
        // TODO: investigate why this happens and come up with a better solution.
        // NOTE: repainting a Scintilla view by itself is not sufficient;
        // Mozilla needs to repaint the entire window.
        if (navigator.platform.match(/^Mac/)) {
            window.setTimeout(function() {
                window.resizeBy(1, 0);
                window.resizeBy(-1, 0);
            }, 10);
        }
    } catch(e) {
        log.error(e);
    }
}

function CheckFile()
{
    try {
        if (gDoc.differentOnDisk()) {
            gDoc.load()
            gView.scimoz.text =gDoc.buffer;
            gView.scimoz.gotoLine(gView.scimoz.lineCount-1);
        }
    } catch (e) {
        log.exception(e);
    }
}

function TailOnBlur() {
}

function TailOnFocus() {
}

function TailOnUnload () {
    //gDoc.releaseView(gView);
    // The "close" method ensures the scintilla view is properly cleaned up.
    gView.close();
    gDoc.releaseReference();
    scintillaOverlayOnUnload();
}





