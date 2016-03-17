/**
 * These functions are in the module &#39;util&#39;. Use
 * require(&#39;util&#39;) to access them.
 */
var util = {};

/**
 * A synchronous output function. Will block the process and output string
 * immediately to stderr.
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
 * Read the data from readableStream and send it to the writableStream.
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
 * Same as util.debug() except this will output all arguments immediately
 * to stderr.
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
 * Returns true if the given "object" is an Array. false otherwise.
 * @param object
 * @returns true if the given "object" is an Array
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
 * A synchronous output function. Will block the process, cast each
 * argument to a string then output to stdout. Does not place newlines
 * after each argument.
 */
util.print = function() {}

/**
 * A synchronous output function. Will block the process and output all
 * arguments to stdout with newlines after each argument.
 */
util.puts = function() {}

exports = util;

