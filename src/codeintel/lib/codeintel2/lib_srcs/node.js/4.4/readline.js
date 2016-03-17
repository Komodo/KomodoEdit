/**
 * To use this module, do require(&#39;readline&#39;). Readline allows
 * reading of a stream (such as [process.stdin][]) on a line-by-line basis.
 */
var readline = {};

/**
 * Clears current line of given TTY stream in a specified direction.
 * @param stream
 * @param dir
 */
readline.clearLine = function(stream, dir) {}

/**
 * Clears the screen from the current position of the cursor down.
 * @param stream
 */
readline.clearScreenDown = function(stream) {}

/**
 * Creates a readline Interface instance. Accepts an options Object that
 * takes the following values:
 * @param options
 * @returns {readline.Interface}
 */
readline.createInterface = function(options) {}

/**
 * Move cursor to the specified position in a given TTY stream.
 * @param stream
 * @param x
 * @param y
 */
readline.cursorTo = function(stream, x, y) {}

/**
 * Move cursor relative to it&#39;s current position in a given TTY stream.
 * @param stream
 * @param dx
 * @param dy
 */
readline.moveCursor = function(stream, dx, dy) {}

/**
 * The class that represents a readline interface with an input and output
 * stream.
 * @constructor
 */
readline.Interface = function() {}
readline.Interface.prototype = new events.EventEmitter();

/**
 * Closes the Interface instance, relinquishing control on the input and
 * output streams. The &#39;close&#39; event will also be emitted.
 */
readline.Interface.prototype.close = function() {}

/**
 * Pauses the readline input stream, allowing it to be resumed later if
 * needed.
 */
readline.Interface.prototype.pause = function() {}

/**
 * Readies readline for input from the user, putting the current setPrompt
 * options on a new line, giving the user a new spot to write. Set
 * preserveCursor to true to prevent the cursor placement being reset to 0.
 * @param preserveCursor
 */
readline.Interface.prototype.prompt = function(preserveCursor) {}

/**
 * Prepends the prompt with query and invokes callback with the user&#39;s
 * response. Displays the query to the user, and then invokes callback with
 * the user&#39;s response after it has been typed.
 * @param query
 * @param callback
 */
readline.Interface.prototype.question = function(query, callback) {}

/**
 * Resumes the readline input stream.
 */
readline.Interface.prototype.resume = function() {}

/**
 * Sets the prompt, for example when you run node on the command line, you
 * see &gt; , which is Node.js&#39;s prompt.
 * @param prompt
 */
readline.Interface.prototype.setPrompt = function(prompt) {}

/**
 * Writes data to output stream, unless output is set to null or undefined
 * when calling createInterface. key is an object literal to represent a
 * key sequence; available if the terminal is a TTY.
 * @param data
 * @param key
 */
readline.Interface.prototype.write = function(data, key) {}

var events = require('events');

exports = readline;

