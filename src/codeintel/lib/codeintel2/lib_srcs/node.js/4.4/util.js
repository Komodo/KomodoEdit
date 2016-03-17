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
 * Inherit the prototype methods from one [constructor][] into another. The
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
 * Internal alias for [Array.isArray][].
 * @param object
 */
util.isArray = function(object) {}

/**
 * Returns true if the given "object" is a Boolean. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is a Boolean
 */
util.isBoolean = function(object) {}

/**
 * Returns true if the given "object" is a Buffer. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is a Buffer
 */
util.isBuffer = function(object) {}

/**
 * Returns true if the given "object" is a Date. Otherwise, returns false.
 * @param object
 * @returns true if the given "object" is a Date
 */
util.isDate = function(object) {}

/**
 * Returns true if the given "object" is an [Error][]. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is an Error
 */
util.isError = function(object) {}

/**
 * Returns true if the given "object" is a Function. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is a Function
 */
util.isFunction = function(object) {}

/**
 * Returns true if the given "object" is strictly null. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is strictly null
 */
util.isNull = function(object) {}

/**
 * Returns true if the given "object" is null or undefined. Otherwise,
 * returns false.
 * @param object
 * @returns true if the given "object" is null or undefined
 */
util.isNullOrUndefined = function(object) {}

/**
 * Returns true if the given "object" is a Number. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is a Number
 */
util.isNumber = function(object) {}

/**
 * Returns true if the given "object" is strictly an Object and not a
 * Function. Otherwise, returns false.
 * @param object
 * @returns true if the given "object" is strictly an Object and not a Function
 */
util.isObject = function(object) {}

/**
 * Returns true if the given "object" is a primitive type. Otherwise,
 * returns false.
 * @param object
 * @returns true if the given "object" is a primitive type
 */
util.isPrimitive = function(object) {}

/**
 * Returns true if the given "object" is a RegExp. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is a RegExp
 */
util.isRegExp = function(object) {}

/**
 * Returns true if the given "object" is a String. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is a String
 */
util.isString = function(object) {}

/**
 * Returns true if the given "object" is a Symbol. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is a Symbol
 */
util.isSymbol = function(object) {}

/**
 * Returns true if the given "object" is undefined. Otherwise, returns
 * false.
 * @param object
 * @returns true if the given "object" is undefined
 */
util.isUndefined = function(object) {}

/**
 * Deprecated predecessor of console.log.
 */
util.print = function() {}

/**
 * Deprecated predecessor of console.log.
 */
util.puts = function() {}

exports = util;

