/* Copyright (c) 2003-2006 ActiveState Software Inc.
   See the file LICENSE.txt for licensing information. */

/* Functions for use less common dialogs (common dialog helpers go in
 * dialogs.js).
 *
 * Summary of Dialogs:
 *  ko.dialogs.pickPreview      Select a URL to preview the given file.
 *  ko.dialogs.progress         Provide a progress (and cancel) UI for
 *                          process that will take a while.
 *
 */

//---- public methods
if (typeof(ko)=='undefined') {
    var ko = {};
}
if (typeof(ko.dialogs)=='undefined') {
    ko.dialogs = {};
}
(function() {

// Pick a preview File/URL for the given file.
//
//  "url" indicate the file to preview.
//  "language" is the language of the current file. If this is not specified it
//      will be automaticxally determined from the URL.
//  "mode" is one of "previewing" or "setting". The UI is slightly different
//      depending on whether the preview file/URL is being sought to
//      immediately _use_ it or to just set it. The default is "previewing".
//
// If the dialog is cancelled it returns null. Otherwise it returns an object
// with the following attributes:
//      .preview    The file or URL to use to preview the given URL. Note
//                  that this may be the given URL itself.
//      .remember   A boolean indicating if the current setting should be
//                  remembered so this picker need not be called again.
//
this.pickPreview = function dialog_pickPreview(url, language /*=null*/, mode /*="previewing"*/)
{
    if (typeof(url) == 'undefined' || url == null)
        throw("Must specify 'url' argument to ko.dialogs.pickPreview().");
    if (typeof(language) == 'undefined') language = null;
    if (typeof(mode) == 'undefined' || mode == null) mode = "previewing";

    // Show the dialog.
    var obj = new Object();
    obj.url = url;
    obj.language = language;
    obj.mode = mode;
    window.openDialog("chrome://komodo/content/dialogs/pickPreview.xul",
                      "_blank",
                      "chrome,modal,titlebar",
                      obj);
    if (obj.retval == "Cancel") {
        return null
    } else {
        return obj;
    }
}


// Show progress for (and provide the ability to cancel) some long process.
//
//  "processor" is a object implementing koIShowsProgress. The progress
//      controller (koIProgressController) will be passed to this object.
//  "prompt" is a short description of the process that will be carried out.
//  "title" is the dialog title.
//  "is_cancellable" is a boolean (default true) indicating if this process
//      can be cancelled.
//  "cancel_warning" is a message that will be displayed warning the user of
//      consequences of cancelling. If not specified no confirmation of
//      cancel will be done.
//  "modal" is a boolean (default true) indicating if the dialog should be
//      modal. If this is false then there is no return value.
//
// How interaction works:
// - processor.set_controller(<controller>) is called when the progress
//   dialog opens.
// - <controller> is an object with that implements koIProgressController.
//   See the IDL for how the processor should use that to report results.
//   Most importantly the process *must* call controller.done() to close the
//   progress dialog.
// - If the dialog is cancelled by the user processor.cancel() will be
//   called. The processor should abort as soon as possible and can
//   controller.done().
//
// If modal=true, returns one of the following:
//  "cancel"        The process was cancelled.
//  "error"         The process failed.
//  "ok"            The process completed successfully.
//  undefined       The dialog was forcefully cancelled.
//
this.progress = function dialog_progress(processor,
                         prompt /*=null*/,
                         title /*=null*/,
                         is_cancellable /*=true*/,
                         cancel_warning /*=null*/,
                         modal /*=true*/)
{
    if (typeof(prompt) == 'undefined') prompt = null;
    if (typeof(title) == 'undefined') title = null;
    if (typeof(is_cancellable) == 'undefined') is_cancellable = true;
    if (typeof(cancel_warning) == 'undefined') cancel_warning = null;
    if (typeof(modal) == 'undefined') modal = true;

    // Show the dialog.
    var obj = {
        processor: processor,
        prompt: prompt,
        title: title,
        is_cancellable: is_cancellable,
        cancel_warning: cancel_warning
    };
    var features;
    if (modal) {
        features = "chrome,modal,titlebar";
    } else {
        features = "chrome,titlebar";
    }
    window.openDialog("chrome://komodo/content/dialogs/progress.xul",
                      "_blank", features, obj);
    if (modal) {
        return obj.retval;
    } else {
        return null;
    }
}

}).apply(ko.dialogs);

var dialog_progress = ko.dialogs.progress;
var dialog_pickPreview = ko.dialogs.pickPreview;
