/**
 * Manages a TCP socket connection
 */
(function () {
    
    const {Cc, Ci}  = require("chrome");
    const tcpSocket = Cc["@mozilla.org/tcp-socket;1"].getService(Ci.nsIDOMTCPSocket);
    const log       = require("ko/logging").getLogger("socket-tcp");
    
    var connection = function(server, port)
    {
        var socket;
        var callbacks = [];
        var delimiter = "\u0000";
        
        var init = () =>
        {
            socket = tcpSocket.open(server, port);
            
            socket.ondrain = pushData;
            socket.ondata = onData;
        };
        
        this.setDelimiter = (value) => delimiter = value;
        this.getDelimiter = () => value;
        
        this.send = (data) =>
        {
            pushData.data += data + delimiter;
        };
        
        this.close = () =>
        {
            socket.close();
        };
        
        this.onData = (callback) =>
        {
            callbacks.push(callback);
        };
        
        var pushData = () =>
        {
            socket.send(pushData.data);
            pushData.data = "";
        };
        pushData.data = ""; // Cached data that will be send the next time we push
        
        var onData = (event) =>
        {
            if (typeof event.data != 'string')
            {
                log.error("Received unsupported data type: " + typeof event.data);
                if ("toString" in event.data)
                {
                    log.error("Data: " + event.data.toString());
                }
                return;
            }
            
            onData.data += event.data;
            
            // Pass data to callbacks
            var index = onData.data.indexOf(delimiter);
            while (index)
            {
                let data = onData.data.substr(0, index);
                for (let callback of callbacks)
                    callback(data);
                    
                onData.data = onData.data.substr(index+1);
                index = onData.data.indexOf(delimiter);
            }
        };
        onData.data = "";
        
        init();
    };
    
    this.open = (server, port) =>
    {
        return new connection(server, port);
    };
    
}).apply(module.exports);