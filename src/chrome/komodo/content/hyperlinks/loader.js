(function() {
    /**
     * Define the hyperlink controller and register it at startup.
     */
    function hyperlinksController() {
        ko.main.addWillCloseHandler(this.destructor, this);
    }
    hyperlinksController.prototype.destructor = function() {
        window.controllers.removeController(this);
    }
    hyperlinksController.prototype.is_cmd_invokeHyperlink_supported = function() {
        return ko.views.manager.currentView != null;
    }
    hyperlinksController.prototype.is_cmd_invokeHyperlink_enabled = function() {
        return ko.views.manager.currentView &&
               ko.views.manager.currentView.getAttribute('type') == 'editor';
    }
    hyperlinksController.prototype.do_cmd_invokeHyperlink = function() {
        var view = ko.views.manager.currentView;
        ko.hyperlinks.show(view, view.scimoz.currentPos, "manual");
        if (view._hyperlink) {
            view._hyperlink.jump(view);
        }
    }

    function initialize() {
        // Add a controller for the invoke hyperlink command.
        window.controllers.appendController(new hyperlinksController());
    }

    window.addEventListener("komodo-ui-started", initialize);
})();

// Lazily load hyperlinks namespace.
XPCOMUtils.defineLazyGetter(ko, "hyperlinks", function() {
    ko.hyperlinks = {};
    // The order of these hyperlink scripts is important, as it sets the
    // priority of the hyperlink handlers.
    Services.scriptloader.loadSubScript("chrome://komodo/content/hyperlinks/hyperlinks.js");
    Services.scriptloader.loadSubScript("chrome://komodo/content/hyperlinks/regexhandler.js");
    Services.scriptloader.loadSubScript("chrome://komodo/content/hyperlinks/filehandler.js");
    Services.scriptloader.loadSubScript("chrome://komodo/content/hyperlinks/csscolorpicker.js");
    Services.scriptloader.loadSubScript("chrome://komodo/content/hyperlinks/gotodefinition.js");
    return ko.hyperlinks;
});
