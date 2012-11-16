if (typeof(ko) == 'undefined') {
    var ko = {};
}

ko.skinEvents = {};

(function() {
	
	var localCache = {};
	var buffer = {};
	
	var events = function() { return {
		window:
		{
			event: 'resize',
			elem: 	window,
			init: 	false
			/*
			,proxy: 	eventProxy,
			handle: 	handleResize,
			*/
		},
		workspace_left_area:
		{
			event: 	'resize',
			elem: 	document.getElementById('workspace_left_area')
		},
		workspace_right_area:
		{
			event: 	'resize',
			elem: 	document.getElementById('workspace_right_area')
		}
	} };
	
	var init = function()
	{
		var _e = events();
		for (var k in _e)
		{
			if ( ! _e.hasOwnProperty(k))
			{
				continue;
			}
			
			_proxy = _e[k].proxy ? _e[k].proxy : eventProxy
			_e[k].elem.addEventListener(_e[k].event, _proxy );
			
			_init = _e[k].init ? _e[k].init : eval('init' + _ucfirst(_e[k].event));
			if (_init != false)
			{
				_init(_e[k].elem);
			}
		}
	};
	
	var handleResize = function(e)
	{
		initResize(e.currentTarget ? e.currentTarget : e.target);
	};
	
	var initResize = function(target)
	{
		var name = _elemVarName(target);
		
		if ( ! name)
		{
			return;
		}
		
		_addToBuffer(name + "-width", 	target.width ? target.width : target.innerWidth);
		_addToBuffer(name + "-height", 	target.height ? target.height : target.innerHeight);
	};
	
	var eventProxy = function(e)
	{
		var handler = eval('handle' + _ucfirst(e.type));
		handler(e);
		
		setTimeout(processBuffer, 50);
	};
	
	var processBuffer = function()
	{
		if (buffer.length === undefined || buffer.length == 0)
		{
			return;
		}
		
		delete buffer.length;
		less.updateVariables(buffer);
		buffer = {};
	};
	
	var _addToBuffer = function(name, value)
	{
		if (localCache[name] !== undefined && value == localCache[name])
		{
			return;
		}
		
		if (buffer.length === undefined)
		{
			buffer.length = 0;
		}
		
		buffer[name] = value;
		localCache[name] = value;
		
		buffer.length++;
	};
	
	var _elemVarName = function(elem, suffix, prefix)
	{
		var identifier = prefix ? prefix + '-' : '';
		
		if (elem == window)
		{
			identifier += 'window';
		}
		else if (elem.hasAttribute && elem.hasAttribute("id"))
		{
			identifier += _normalize(elem.getAttribute("id"));
		}
		else if (elem.hasAttribute && elem.hasAttribute("class"))
		{
			if (elem.nodeName !== undefined)
			{
				identifier = _normalize(elem.nodeName);
			}
			
			identifier += "-" + _normalize(elem.getAttribute("class"));
		}
		else if (elem.nodeName !== undefined)
		{
			identifier += _normalize(elem.nodeName);
		}
		else
		{
			return false;
		}
		
		identifier += suffix ? '-' + suffix : '';
		
		return identifier;
	};
	
	var _normalize = function(string)
	{
		return string.replace(/[^a-zA-Z0-9_-]/,'');
	};
	
	var _ucfirst = function(string)
	{
		return string.charAt(0).toUpperCase() + string.slice(1)
	};
	
	window.addEventListener('load', init);
	
}).apply(ko.skinEvents);