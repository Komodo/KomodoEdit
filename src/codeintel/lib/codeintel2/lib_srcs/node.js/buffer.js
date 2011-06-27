/**
 * Pure Javascript is Unicode friendly but not nice to binary data. When
 * dealing with TCP streams or the file system, it's necessary to handle
 * octet streams. Node has several strategies for manipulating, creating,
 * and consuming octet streams.
 */
var buffer = {};

/**
 * Allocates a new buffer of size octets.  Allocates a new buffer using an
 * array of octets.  Allocates a new buffer containing the given str.
 */
buffer.Buffer = function() {}
buffer.Buffer.prototype = {}
/**
 * Gives the actual byte length of a string. This is not the same as
 * String.prototype.length since that returns the number of characters in a
 * string.
 * @param encoding='utf8'
 * @param string
 */
buffer.Buffer.prototype.byteLength = function(string, encoding) {}
/**
 * Returns a new buffer which references the same memory as the old, but
 * offset and cropped by the start and end indexes.
 * @param end=buffer.length
 * @param start
 */
buffer.Buffer.prototype.slice = function(start, end) {}
/**
 * Writes string to the buffer at offset using the given encoding. Returns
 * number of octets written. If buffer did not contain enough space to fit
 * the entire string, it will write a partial amount of the string. The
 * method will not write partial characters.
 * @param encoding='utf8'
 * @param offset=0
 * @param string
 */
buffer.Buffer.prototype.write = function(string, offset, encoding) {}
/**
 * The size of the buffer in bytes. Note that this is not necessarily the
 * size of the contents. length refers to the amount of memory allocated
 * for the buffer object. It does not change when the contents of the
 * buffer are changed.
 */
buffer.Buffer.prototype.length = 0;
/**
 * Decodes and returns a string from buffer data encoded with encoding
 * beginning at start and ending at end.
 * @param encoding
 * @param end=buffer.length
 * @param start=0
 */
buffer.Buffer.prototype.toString = function(encoding, start, end) {}
/**
 * Does a memcpy() between buffers.
 * @param sourceEnd=buffer.length
 * @param sourceStart=0
 * @param targetBuffer
 * @param targetStart=0
 */
buffer.Buffer.prototype.copy = function(targetBuffer, targetStart, sourceStart, sourceEnd) {}
/**
 * Tests if obj is a Buffer.
 * @param obj
 */
buffer.Buffer.prototype.isBuffer = function(obj) {}


exports = buffer;

