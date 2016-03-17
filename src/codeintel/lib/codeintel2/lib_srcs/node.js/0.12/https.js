/**
 * HTTPS is the HTTP protocol over TLS/SSL. In Node this is implemented as
 * a separate module.
 */
var https = {};

/**
 * Returns a new HTTPS web server object. The options is similar to
 * [tls.createServer()][]. The requestListener is a function which is
 * automatically added to the &#39;request&#39; event.
 * @param options
 * @param requestListener
 * @returns {https.Server}
 */
https.createServer = function(options, requestListener) {}

/**
 * See [http.listen()][] for details.
 * @param handle
 * @param callback
 */
createServer.listen = function(handle, callback) {}

/**
 * See [http.listen()][] for details.
 * @param handle
 * @param callback
 */
createServer.listen = function(handle, callback) {}

/**
 * See [http.close()][] for details.
 * @param callback
 */
createServer.close = function(callback) {}

/**
 * Like http.get() but for HTTPS.
 * @param options
 * @param callback
 * @returns {http.ClientRequest}
 */
https.get = function(options, callback) {}

/**
 * Makes a request to a secure web server.
 * @param options
 * @param callback
 * @returns {http.ClientRequest}
 */
https.request = function(options, callback) {}

/**
 * Global instance of [https.Agent][] for all HTTPS client requests.
 * @type {https.Agent}
 */
https.globalAgent = 0;

/**
 * An Agent object for HTTPS similar to [http.Agent][]. See
 * [https.request()][] for more information.
 * @constructor
 */
https.Agent = function() {}
https.Agent.prototype = new http.Agent();

/**
 * This class is a subclass of tls.Server and emits events same as
 * http.Server. See http.Server for more information.
 * @constructor
 */
https.Server = function() {}
https.Server.prototype = new tls.Server();
https.Server.prototype = new http.Server();

/**
 * See [http.Server#setTimeout()][].
 * @param msecs
 * @param callback
 */
https.Server.prototype.setTimeout = function(msecs, callback) {}

/**
 * See [http.Server#timeout][].
 */
https.Server.prototype.timeout = 0;

var http = require('http');

exports = https;

