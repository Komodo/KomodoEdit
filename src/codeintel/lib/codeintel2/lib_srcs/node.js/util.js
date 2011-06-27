/**
 * These functions are in the module 'util'. Use require('util') to access
 * them.
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
 * Experimental
 * @param [callback]
 * @param readableStream
 * @param writableStream
 */
util.pump = function(readableStream, writableStream, callback) {}

/**
 * Return a string representation of object, which is useful for debugging.
 * @param depth=2
 * @param object
 * @param showHidden=false
 */
util.inspect = function(object, showHidden, depth) {}

/**
 * Output with timestamp on stdout.
 * @param string
 */
util.log = function(string) {}


exports = util;

