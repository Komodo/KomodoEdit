var require = window.require;
require.setRequirePath("breadcrumbs/", "chrome://breadcrumbs/content/sdk/");

(function() {
  
    var viewChanged = function()
    {
        var view = require("ko/views").current().get();
        if ( ! view || view._breadcrumbsInit) return;
        view._breadcrumbsInit = true;
        
        require("breadcrumbs/breadcrumbs").init(view);
    }
    
    window.addEventListener('current_view_changed', viewChanged);
    window.addEventListener('workspace_restored', viewChanged);
    window.addEventListener('project_opened', viewChanged);
    
})();