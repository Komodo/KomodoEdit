/**
 * The console module provides a simple debugging console that is similar
 * to the JavaScript console mechanism provided by web browsers.
 */
var console = {};

/**
 * The Console class can be used to create a simple logger with
 * configurable output streams and can be accessed using either
 * require(&#39;console&#39;).Console or console.Console:
 * @constructor
 */
console.Console = function() {}

/**
 * A simple assertion test that verifies whether value is truthy. If it is
 * not, an AssertionError is thrown. If provided, the error message is
 * formatted using [util.format()][] and used as the error message.
 * @param value
 * @param message
 */
console.Console.prototype.assert = function(value, message) {}

/**
 * Uses [util.inspect()][] on obj and prints the resulting string to
 * stdout.
 * @param obj
 * @param options
 */
console.Console.prototype.dir = function(obj, options) {}

/**
 * Prints to stderr with newline. Multiple arguments can be passed, with
 * the first used as the primary message and all additional used as
 * substitution values similar to printf(3) (the arguments are all passed
 * to [util.format()][]).
 * @param data
 */
console.Console.prototype.error = function(data) {}

/**
 * The console.info() function is an alias for [console.log()][].
 * @param data
 */
console.Console.prototype.info = function(data) {}

/**
 * Prints to stdout with newline. Multiple arguments can be passed, with
 * the first used as the primary message and all additional used as
 * substitution values similar to printf(3) (the arguments are all passed
 * to [util.format()][]).
 * @param data
 */
console.Console.prototype.log = function(data) {}

/**
 * Starts a timer that can be used to compute the duration of an operation.
 * Timers are identified by a unique label. Use the same label when you
 * call [console.timeEnd()][] to stop the timer and output the elapsed time
 * in milliseconds to stdout. Timer durations are accurate to the sub-
 * millisecond.
 * @param label
 */
console.Console.prototype.time = function(label) {}

/**
 * Stops a timer that was previously started by calling [console.time()][]
 * and prints the result to stdout:
 * @param label
 */
console.Console.prototype.timeEnd = function(label) {}

/**
 * Prints to stderr the string &#39;Trace :&#39;, followed by the
 * [util.format()][] formatted message and stack trace to the current
 * position in the code.
 * @param message
 */
console.Console.prototype.trace = function(message) {}

/**
 * The console.warn() function is an alias for [console.error()][].
 * @param data
 */
console.Console.prototype.warn = function(data) {}

exports = console;

