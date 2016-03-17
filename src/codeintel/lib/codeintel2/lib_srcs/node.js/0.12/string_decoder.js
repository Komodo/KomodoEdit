/**
 * To use this module, do require(&#39;string_decoder&#39;). StringDecoder
 * decodes a buffer to a string. It is a simple interface to
 * buffer.toString() but provides additional support for utf8.
 */
var stringdecoder = {};

/**
 * Accepts a single argument, encoding which defaults to utf8.
 * @constructor
 */
stringdecoder.StringDecoder = function() {}

/**
 * Returns a decoded string.
 * @param buffer
 * @returns a decoded string
 */
stringdecoder.StringDecoder.prototype.write = function(buffer) {}

/**
 * Returns any trailing bytes that were left in the buffer.
 * @returns any trailing bytes that were left in the buffer
 */
stringdecoder.StringDecoder.prototype.end = function() {}

exports = string_decoder;

