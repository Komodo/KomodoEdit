(function() {

	if (typeof less !== 'undefined') return false;
	
	if (window.parent != window && window.parent.less)
	{
		window.parent.less.setContext(window);
		window.parent.less.refresh();
		window.parent.less.restoreContext();
	}
	else
	{
		if (typeof lessPath == 'undefined')
		{
			var loader = document.getElementById('lessLoader');
			if ( ! loader)
			{
				throw "Could not detect path of less.js as the lessPath variable is undefined and no lessLoader element id exists";
			}
			
			lessPath = loader.getAttribute('src').replace(/(.*\/).*/, '$1less.js');
		}
		
		Components.classes["@mozilla.org/moz/jssubscript-loader;1"]
		.getService(Components.interfaces.mozIJSSubScriptLoader).loadSubScript(lessPath);
	}
	
})();