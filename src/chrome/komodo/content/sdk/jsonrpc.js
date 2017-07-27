/**
 * Manages a JSON-RPC interface over a socket
 */
(function() {
    
    const log       = require("ko/logging").getLogger("jsonrpc");
    const KoPromise = require("ko/promise");
    const base64    = require("sdk/base64");
    //log.setLevel(10);
    
    this.ERROR_PARSING = -32700;
    this.ERROR_INVALID_REQUEST = -32600;
    this.ERROR_METHOD_NOT_FOUND = -32601;
    this.ERROR_INVALID_PARAMS = -32602;
    this.ERROR_INTERNAL = -32603;
    
    var instance = function(socket)
    {
        var reqid = 0;
        var callbacks = { all: [], errors: [] };
        
        var init = () =>
        {
            socket.onData(onData);
            
            log.debug("Created new JSONRPC Instance");
        };
        
        this.request = (method, args) =>
        {
            if (typeof method != "string")
            {
                log.error("Invalid method name, method name must be a string");
                return;
            }
            
            if (typeof args == "function")
            {
                callback = args;
                args = undefined;
            }
            
            var data = {
                "jsonrpc": "2.0",
                "method": method,
                "id": ++reqid,
                "params": []
            };
            
            if (args)
                data.params = args;
                
            try
            {
                data = JSON.stringify(data);
                log.debug(`Sending request: ${data}`);
                data = base64.encode(data);
            }
            catch(e)
            {
                log.exception(e, "Failed serializing request for method: " + method);
                return;
            }
            
            return new KoPromise((resolve, reject, each) =>
            {
                callbacks[reqid] = {};
                callbacks[reqid].resolve = resolve;
                callbacks[reqid].reject = reject;
                callbacks[reqid].each = each;
                
                socket.send(data);
            });
        };
        
        this.onData = (callback) =>
        {
            callbacks.all.push(callback);
        };
        
        this.onError = (callback) =>
        {
            callbacks.errors.push(callback);
        };
        
        var onData = (data) =>
        {
            log.debug(`Receiving data`);
            
            try
            {
                data = base64.decode(data.trim());
                log.debug(`Received data: ${data}, length: ${data.length}`);
                data = JSON.parse(data);
            }
            catch (e)
            {
                log.exception(e, "Failed parsing JSON: " + data);
                return;
            }
            
            for (let callback of callbacks.all)
                callback(data);

            if (data.id in callbacks)
            {
                if ("result" in data)
                {
                    if ( ! data.complete)
                        callbacks[data.id].each(data.result);
                    else
                        callbacks[data.id].resolve(data.result);
                }

                if ("error" in data)
                    callbacks[data.id].reject(data.error);
                    
                if (data.complete)
                    delete callbacks[data.id];
            }
        };
        
        init();
    };
    
    this.create = (socket) =>
    {
        return new instance(socket);
    };
    
}).apply(module.exports);
