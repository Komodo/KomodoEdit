require.setRequirePath("breadcrumbs/", "chrome://breadcrumbs/content/sdk/");

(function() {
  
    var viewChanged = function(e)
    {
        var view = e.detail.view;
        if ( ! view && view._breadcrumbsInit) return;
        view._breadcrumbsInit = true;
        view._breadcrumbs = require("breadcrumbs/breadcrumbs").init(view);
    }
    
    window.addEventListener('editor_view_opened', viewChanged);
    
    var observer = (subject) =>
    {
        var info = subject.wrappedJSObject;
        if (info.command == "move" || info.command == "rename")
        {
            var views = ko.views.manager.topView.findViewsForDocument(info.newDocument);
            for (let view of views)
            {
                if ( ! view._breadcrumbsInit)
                    continue;
                view._breadcrumbs.reload();
            }
        }
    };

    var obs = Components.classes["@mozilla.org/observer-service;1"].getService(Components.interfaces.nsIObserverService);
    obs.addObserver(observer, "morekomodo_command", false);

})();