/**
 * Manages a JSON-RPC interface over a socket
 */
(function() {
    
    const log       = require("ko/logging").getLogger("jsonrpc");
    
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
            }
            catch(e)
            {
                log.error("Failed serializing request for method: " + method);
                return;
            }
            
            return new Promise((resolve, reject) =>
            {
                log.debug(`Sending request: ${data}`);
                
                callbacks[reqid] = {};
                callbacks[reqid].resolve = resolve;
                callbacks[reqid].reject = reject;
                
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
            log.debug(`Received data: ${data}, length: ${data.length}`);
            
            try
            {
                data = JSON.parse(data.trim());
            }
            catch (e)
            {
                log.error("Failed parsing JSON: " + data);
                return;
            }
            
            for (let callback of callbacks.all)
                callback(data);

            if (data.id in callbacks)
            {
                if ("result" in data)
                    callbacks[data.id].resolve(data.result);
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
