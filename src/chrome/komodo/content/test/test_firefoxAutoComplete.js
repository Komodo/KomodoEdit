/* Copyright (c) 2004-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* This is an internal test dialog to try out the new Firefox AutoComplete
 * functionality.
 *
 * c.f. http://xulplanet.com/references/elemref/ref_textboxFirefoxAutoComplete.html
 */

var log = ko.logging.getLogger("test_FFAC");
log.setLevel(ko.logging.LOG_DEBUG);

var widgets = null;

//---- interface routines for XUL

function OnLoad()
{
    log.debug("OnLoad()");
    try {
        widgets = new Object();
        widgets.complete = document.getElementById("complete");

        widgets.complete.focus();
    } catch(ex) {
        log.exception(ex);
    }
}

function UpdateBooleanCompleteAttribute(attrname, value)
{
    log.debug("UpdateBooleanCompleteAttribute('"+attrname+"', "+value+");");
    try {
        if (value) {
            widgets.complete.setAttribute(attrname, "true");
        } else {
            widgets.complete.removeAttribute(attrname);
        }
    } catch(ex) {
        log.exception(ex);
    }
}

function UpdateStringCompleteAttribute(attrname, value)
{
    log.debug("UpdateStringCompleteAttribute('"+attrname+"', '"+value+"');");
    try {
        widgets.complete.setAttribute(attrname, value);
    } catch(ex) {
        log.exception(ex);
    }
}

/*
function Foo()
{
    log.debug("Foo()");
    try {
    } catch(ex) {
        log.exception(ex);
    }
}
*/

