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
 * Wait for command termination.
 *
 * Used when a command is being run synchronously, e.g. when the output is
 * being captured to insert into the current buffer.
 */

//---- globals

var log = ko.logging.getLogger("dialogs.waitfortermination");

var gProcess = null;
var gObserverSvc = null;
var gTermObserver = null;



//---- interface routines for waitfortermination.xul

function OnLoad()
{
    try {
        var dialog = document.getElementById("dialog-waitfortermination")
        var acceptButton = dialog.getButton("accept");
        acceptButton.setAttribute("label", "Kill");

        // A command part is expected as the first window argument.
        gProcess = window.arguments[0].process;
        var command = window.arguments[0].command;
    
        var commandTextbox = document.getElementById('command-textbox');
        commandTextbox.setAttribute("value", command);
    
        // Setup listener for termination.
        gTermObserver = new TermObserver(command);
        gObserverSvc = Components.classes["@mozilla.org/observer-service;1"]
                       .getService(Components.interfaces.nsIObserverService);
        gObserverSvc.addObserver(gTermObserver, 'run_terminated',false);
    
        // Check if the process has terminated before the observer was setup.
        try {
            gProcess.wait(0);
            TerminatedCleanly();
        } catch (ex) {
            // Do nothing, the wait timed out (or failed, which we probably
            // *should* look for).
        }
    } catch(ex) {
        log.exception(ex, "Error loading prompt dialog.");
    }
}


function OnUnload()
{
}


function TerminatedCleanly()
{
    //dump("XXX waitfortermination: terminated cleanly\n");
    // Clean up observer.
    if (gTermObserver) {
        gObserverSvc.removeObserver(gTermObserver, 'run_terminated');
        gTermObserver = null;
    }

    window.arguments[0].retval = "terminated cleanly";
    window.close();
}

function Cancel()
{
    if (gProcess == null) {
        dump("We are running this dialog from the Test menu so will allow "
             +"it to be cancelled.");
        return true;
    } else {
        // Normally don't allow this dialog to be cancelled. Either:
        // - the process finishes and the dialog closes automatically
        // - or you click "Kill" and it closes.
        return false;
    }
}

function Kill()
{
    //dump("XXX waitfortermination: killed\n");
    // Stop observer. Must do this before killing the process, else the
    // TermObserver will mistakenly think the termination was clean.
    if (gTermObserver) {
        gObserverSvc.removeObserver(gTermObserver, 'run_terminated');
        gTermObserver = null;
    }

    // Terminate the process and return.
    gProcess.kill(-1);

    window.arguments[0].retval = "killed";
    window.close();
}


function TermObserver(command) { this._command = command; };
TermObserver.prototype.observe = function(child, topic, command)
{
    //dump("XXX waitfortermination: TermObserver observed topic='"+topic+"'.\n");
    switch (topic) {
    case 'run_terminated':
        if (command == this._command) {
            TerminatedCleanly();
        } else {
            log.warn("observed termination of unexpected command: "
                     +"expected='"+this._command+"' observed='"+command+"'");
        }
        break;
    }
}

