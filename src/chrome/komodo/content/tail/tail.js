/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* -*- Mode: JavaScript; tab-width: 4; indent-tabs-mode: nil; c-basic-offset: 2 -*- */

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
    gDoc.releaseReference();
}





