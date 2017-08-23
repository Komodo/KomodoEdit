/**
 * Manages a TCP socket connection
 */
(function () {
    
    const {Cc, Ci}  = require("chrome");
    const tcpSocket = Cc["@mozilla.org/tcp-socket;1"].getService(Ci.nsIDOMTCPSocket);
    const log       = require("ko/logging").getLogger("socket-tcp");
    const legacy    = require("ko/windows").getMain().ko;
    
    var connection = function(server, port)
    {
        var socket;
        var callbacks = [];
        var delimiter = "\u0000";
        var closing = false;
        
        var init = () =>
        {
            socket = tcpSocket.open(server, port);
            
            log.debug(`Opened socket connection to ${server}:${port}, state: ${socket.readyState}`);
            
            socket.onopen = onOpen;
            socket.onerror = onError;
            socket.onclose = onClose;
            socket.ondrain = onDrain;
            socket.ondata = onData;
        };
        
        this.setDelimiter = (value) => delimiter = value;
        this.getDelimiter = () => value;
        
        this.send = (data) =>
        {
            pushData.data += data + delimiter;
            pushData();
        };
        
        this.close = () =>
        {
            closing = true;
            socket.close();
        };
        
        this.onData = (callback) =>
        {
            callbacks.push(callback);
        };
        
        var pushData = () =>
        {
            if (closing)
            {
                log.debug("pushData called while closing");
                return;
            }

            if (socket.readyState == "connecting")
                return setTimeout(pushData, 100);
            
            if (socket.readyState == "closed")
                return log.error("Cannot push data over a closed socket connection");
            
            log.debug(`Sending data: ${pushData.data}`);
            socket.send(pushData.data);
            pushData.data = "";
        };
        pushData.data = ""; // Cached data that will be send the next time we push
        
        var onDrain = () =>
        {
            log.debug("onDrain");
            pushData();
        };
        
        var onOpen = () =>
        {
            log.debug("onOpen");
        };
        
        var onClose = () =>
        {
            closing = true;
            log.debug("onClose");
        };
        
        var onError = (event) =>
        {
            log.debug("onError");

            var data = event.data;
            if (typeof data == "object")
                data = data.name || data;

            var msg = `Error occurred: ${event.type || event._type} : ${data}`;

            if (closing || legacy.main.windowIsClosing)
                log.debug(msg);
            else
                log.error(msg);
        };
        
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
            
            log.debug(`Received data: ${event.data}`);
            
            onData.data += event.data;
            
            // Pass data to callbacks
            var index = onData.data.indexOf(delimiter);
            while (index != -1)
            {
                let data = onData.data.substr(0, index);
                for (let callback of callbacks)
                {
                    try
                    {
                        callback(data);
                    } catch (e)
                    {
                        log.exception("Exception occurred while performing callback", e);
                    }
                }
                    
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