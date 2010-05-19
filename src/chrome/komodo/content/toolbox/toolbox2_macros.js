/* Copyright (c) 2000-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.toolbox2)=='undefined') {
    ko.toolbox2 = {};
}

(function() { // ko.toolbox2 continued
var log = ko.logging.getLogger('ko.toolbox2');
// log.setLevel(ko.logging.DEBUG);

this.executeMacro = function macro_executeMacro(part, async, observer_arguments)
{
    log.info("executeMacro part.id:"+part.id);
    if (ko.macros.recorder.mode == 'recording') {
        // See bug 79081 for why we can't have async macros while recording.
        async = false;
    }
    try {
        ko.macros.recordPartInvocation(part);
        var language = part.getStringAttribute('language').toLowerCase();
        if (typeof(async) == "undefined")
            async = part.getBooleanAttribute('async');
        if (async
            && (language == 'javascript'
                || typeof(observer_arguments) != "undefined")) {
            // Python notification observers use this technique.
            setTimeout(_executeMacro, 10,
                       part, false, observer_arguments);
        } else {
            return _executeMacro(part, async, observer_arguments);
        }
    } catch (e) {
        log.exception(e);
    }
    return false;
}

function _executeMacro(part, asynchronous, observer_arguments) {
    // Returns true if there was a problem running the macro
    // The synchronous flag is not used for JavaScript, since the timeout
    // has already occurred by the time we get called here.  JS execution
    // isn't in another thread, just on a timeout.
    if (typeof(observer_arguments) == "undefined") {
        observer_arguments = null;
    }
    try {
        ko.macros.recorder.suspendRecording();
        var language = part.getStringAttribute('language').toLowerCase();
        var retval = false;
        var exception = null;
        var view = null;
        
        if (observer_arguments
            && observer_arguments.subject
            && observer_arguments.subject.nodeName
            && observer_arguments.subject.nodeName == 'view') {
            view = observer_arguments.subject;
        }
        if (!view) {
            try {
                view = ko.views.manager.currentView;
            } catch(ex) {}
        }
        
        var editor = null;
        if (view && view.getAttribute('type') == 'editor' && view.scintilla && view.scintilla.scimoz) {
            editor = view.scintilla.scimoz;
        }
        switch (language) {
            case 'javascript':
                try {
                    retval = ko.macros.evalAsJavaScript(part.value, part,
                                                        observer_arguments, view);
                } catch (e) {
                    exception = String(e);
                }
                break;
            case 'python':
                try {
                    var koDoc = null;
                    if (view && view.koDoc) {
                        koDoc = view.koDoc;
                    }
                    editor = null;
                    if (view && view.getAttribute('type') == 'editor' && view.scimoz) {
                        editor = view.scimoz;
                    }
                    if (!observer_arguments) {
                        retval = part.evalAsPython(document, window, editor,
                                                   koDoc, view,
                                                   part.value, asynchronous);
                    } else {
                        retval = part.evalAsPythonObserver(document, window, editor,
                                                   koDoc, view,
                                                   part.value,
                                                   false,
                                                   observer_arguments['subject'],
                                                   observer_arguments['topic'],
                                                   observer_arguments['data']);
                    }
                } catch (e) {
                    log.exception(e);
                    var lastErrorSvc = Components.classes["@activestate.com/koLastErrorService;1"].
                                       getService(Components.interfaces.koILastErrorService);
                    exception = lastErrorSvc.getLastErrorMessage();
                }
                break;
            default:
                retval = "Macros written in '"+language+"' aren't supported."
        }
        if (exception) {
            ko.dialogs.alert("There was a problem executing the macro: " +
                         part.getStringAttribute('name'), exception);
            return true;
        } else {
            return retval;
        }
    } catch (e) {
        log.exception(e);
    } finally {
        ko.macros.recorder.resumeRecording();
    }
    return false;
}

}).apply(ko.toolbox2);



