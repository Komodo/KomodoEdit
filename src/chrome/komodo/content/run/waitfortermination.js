/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

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

