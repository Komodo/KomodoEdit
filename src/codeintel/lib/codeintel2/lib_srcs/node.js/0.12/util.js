/**
 * These functions are in the module &#39;util&#39;. Use
 * require(&#39;util&#39;) to access them.
 */
var util = {};

/**
 * Deprecated predecessor of console.error.
 * @param string
 */
util.debug = function(string) {}

/**
 * Inherit the prototype methods from one constructor into another. The
 * prototype of constructor will be set to a new object created from
 * superConstructor.
 * @param constructor
 * @param superConstructor
 */
util.inherits = function(constructor, superConstructor) {}

/**
 * Deprecated predecessor of stream.pipe().
 * @param readableStream
 * @param writableStream
 * @param callback
 */
util.pump = function(readableStream, writableStream, callback) {}

/**
 * Return a string representation of object, which is useful for debugging.
 * @param object
 * @param options
 */
util.inspect = function(object, options) {}

/**
 * Output with timestamp on stdout.
 * @param string
 */
util.log = function(string) {}

/**
 * This is used to create a function which conditionally writes to stderr
 * based on the existence of a NODE_DEBUG environment variable. If the
 * section name appears in that environment variable, then the returned
 * function will be similar to console.error(). If not, then the returned
 * function is a no-op.
 * @param section {String}
 * @returns The logging function
 */
util.debuglog = function(section) {}

/**
 * Marks that a method should not be used any more.
 * @param function
 * @param string
 */
util.deprecate = function(function, string) {}

/**
 * Deprecated predecessor of console.error.
 */
util.error = function() {}

/**
 * Returns a formatted string using the first argument as a printf-like
 * format.
 * @param format
 * @returns a formatted string using the first argument as a printf-like format
 */
util.format = function(format) {}

/**
 * Internal alias for Array.isArray.
 * @param object
 */
util.isArray = function(object) {}

/**
 * Returns true if the given "object" is a Date. false otherwise.
 * @param object
 * @returns true if the given "object" is a Date
 */
util.isDate = function(object) {}

/**
 * Returns true if the given "object" is an Error. false otherwise.
 * @param object
 * @returns true if the given "object" is an Error
 */
util.isError = function(object) {}

/**
 * Returns true if the given "object" is a RegExp. false otherwise.
 * @param object
 * @returns true if the given "object" is a RegExp
 */
util.isRegExp = function(object) {}

/**
 * Deprecated predecessor of console.log.
 */
util.print = function() {}

/**
 * Deprecated predecessor of console.log.
 */
util.puts = function() {}

exports = util;

