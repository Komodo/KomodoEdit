/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * The Ajax SDK, allows you to easily send HTTP requests
 *
 * @module ko/ajax
 */
(function() {
    
    const log       = require("ko/logging").getLogger("sdk-ajax");
    const {Cc, Ci}  = require("chrome");
    
    /**
     * Query the given path/uri via a GET request
     * 
     * @param   {String}    path        The path
     * @param   {Function}  callback    Callback function
     * 
     * @returns {Void}
     */
    this.get = function(path, callback)
    {
        return this.request({url: path, method: 'GET'}, callback);
    }
    
    /**
     * Query the given path/uri via a POST request
     * 
     * @param   {String}    path        The path
     * @param   {Function}  callback    Callback function
     * 
     * @returns {Void}
     */
    this.post = function(path, callback)
    {
        return this.request({url: path, method: 'POST'}, callback);
    }

    /**
     * Manually construct a HTTP request
     * 
     * @param   {String}    params          url, method, headers, body, withCredentials
     * @param   {Function}  callback        Callback function
     * 
     * @returns {Void}
     */
    this.request = function(params, callback)
    {
        if (typeof params == 'string') params = { url: params };
        
        var headers = params.headers || {};
        var body = params.body;

        // Todo: use common js module - the one in our current moz version is broken
        // var req = new require("sdk/net/xhr").XMLHttpRequest;
        var req = new _window().XMLHttpRequest({mozSystem: true});
        req.withCredentials = params.withCredentials || false;

        req.onreadystatechange = function() {
            if (req.readyState == 4 && callback)
                callback(req.status, req.responseText, req);
        }

        var defaultHeaders = {
            'X-Requested-With': 'XMLHttpRequest',
            'Content-Type': 'application/x-www-form-urlencoded',
            'Content-Length': body ? body.length : 0,
            'Connection': 'close'
        }
        
        var _headers = {};
        for (let k in defaultHeaders)
            _headers = headers[k] || defaultHeaders[k];

        req.open(params.method || (body ? 'POST' : 'GET'), params.url, true);

        for (var field in _headers)
            req.setRequestHeader(field, _headers[field]);

        req.send(body);
    }
    
    var _window = function()
    {
        var w;
        try
        {
            w = winUtils.getToplevelWindow(window);
        }
        catch (e)
        {
            log.debug("getTopLevelWindow failed, falling back on window mediator");
            
            var wm = Cc["@mozilla.org/appshell/window-mediator;1"].getService(Ci.nsIWindowMediator);
            let windows = wm.getEnumerator("Komodo");
            while (windows.hasMoreElements())
                w = windows.getNext().QueryInterface(Ci.nsIDOMWindow);
        }
        
        return w;
    }
    
}).apply(module.exports);