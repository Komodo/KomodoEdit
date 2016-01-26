var require = window.require;
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
    
})();