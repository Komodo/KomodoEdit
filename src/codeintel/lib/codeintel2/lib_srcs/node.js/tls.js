/**
 * Use require('tls') to access this module.
 */
var tls = {};

/**
 * This is a constructor for the tls.Server class. The options object has
 * these possibilities:
 * @param options
 * @param secureConnectionListener
 * @returns tls.Server
 */
tls.createServer = function(options, secureConnectionListener) {}

/**
 * Creates a new client connection to the given port and host. (If host
 * defaults to localhost.) options should be an object which specifies
 * @param [host]
 * @param [options]
 * @param callback
 * @param port
 */
tls.connect = function(port, host, options, callback) {}

/**
 * This class is a subclass of net.Server and has the same methods on it.
 * Instead of accepting just raw TCP connections, this accepts encrypted
 * connections using TLS or SSL.
 */
tls.Server = function() {}
tls.Server.prototype = {}
/**
 * The number of concurrent connections on the server.
 */
tls.Server.prototype.connections = 0;
/**
 * Stops the server from accepting new connections. This function is
 * asynchronous, the server is finally closed when the server emits a
 * 'close' event.
 */
tls.Server.prototype.close = function() {}
/**
 * Set this property to reject connections when the server's connection
 * count gets high.
 */
tls.Server.prototype.maxConnections = 0;
/**
 * Begin accepting connections on the specified port and host. If the host
 * is omitted, the server will accept connections directed to any IPv4
 * address (INADDR_ANY).
 * @param [callback]
 * @param [host]
 * @param port
 */
tls.Server.prototype.listen = function(port, host, callback) {}


exports = tls;

