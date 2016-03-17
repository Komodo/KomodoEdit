/**
 * Prior to the introduction of TypedArray in ECMAScript 2015 (ES6), the
 * JavaScript language had no mechanism for reading or manipulating streams
 * of binary data. The Buffer class was introduced as part of the Node.js
 * API to make it possible to interact with octet streams in the context of
 * things like TCP streams and file system operations.
 */
var buffer = {};

/**
 * The Buffer class is a global type for dealing with binary data directly.
 * @constructor
 */
buffer.Buffer = function() {}

/**
 * Returns the actual byte length of a string. This is not the same as
 * [String.prototype.length][] since that returns the number of characters
 * in a string.
 * @param string {String}
 * @param encoding=`'utf8'` {String}
 * @returns the actual byte length of a string
 */
buffer.Buffer.byteLength = function(string, encoding) {}

/**
 * Returns a new Buffer that references the same memory as the original,
 * but offset and cropped by the start and end indices.
 * @param start=0 {Number}
 * @param end=`buffer.length` {Number}
 * @returns {buffer.Buffer} a new Buffer that references the same memory as the original, but offset and cropped by the start and end indices
 */
buffer.Buffer.prototype.slice = function(start, end) {}

/**
 * Writes string to the Buffer at offset using the given encoding.
 * @param string {String}
 * @param offset=0 {Number}
 * @param length=buffer.length - offset {Number}
 * @param encoding=`'utf8'` {String}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.write = function(string, offset, length, encoding) {}

/**
 * Returns the amount of memory allocated for the Buffer in number of
 * bytes. Note that this does not necessarily reflect the amount of usable
 * data within the Buffer. For instance, in the example below, a Buffer
 * with 1234 bytes is allocated, but only 11 ASCII bytes are written.
 */
buffer.Buffer.prototype.length = 0;

/**
 * Decodes and returns a string from the Buffer data using the specified
 * character set encoding.
 * @param encoding=`'utf8'` {String}
 * @param start=0 {Number}
 * @param end=`buffer.length` {Number}
 */
buffer.Buffer.prototype.toString = function(encoding, start, end) {}

/**
 * Copies data from a region of this Buffer to a region in the target
 * Buffer even if the target memory region overlaps with the source.
 * @param targetBuffer {Buffer}
 * @param targetStart=0 {Number}
 * @param sourceStart=0 {Number}
 * @param sourceEnd=buffer.length {Number}
 * @returns The number of bytes copied.
 */
buffer.Buffer.prototype.copy = function(targetBuffer, targetStart, sourceStart, sourceEnd) {}

/**
 * Returns &#39;true&#39; if obj is a Buffer.
 * @param obj {Object}
 * @returns &#39;true&#39; if obj is a Buffer
 */
buffer.Buffer.isBuffer = function(obj) {}

/**
 * Compares two Buffer instances and returns a number indicating whether
 * buf comes before, after, or is the same as the otherBuffer in sort
 * order.
 * @param otherBuffer {Buffer}
 */
buffer.Buffer.prototype.compare = function(otherBuffer) {}

/**
 * Compares buf1 to buf2 typically for the purpose of sorting arrays of
 * Buffers. This is equivalent is calling [buf1.compare(buf2)][].
 * @param buf1 {Buffer}
 * @param buf2 {Buffer}
 */
buffer.Buffer.compare = function(buf1, buf2) {}

/**
 * Returns a new Buffer which is the result of concatenating all the
 * Buffers in the list together.
 * @param list {Array}
 * @param totalLength {Number}
 * @returns {buffer.Buffer} a new Buffer which is the result of concatenating all the Buffers in the list together
 */
buffer.Buffer.concat = function(list, totalLength) {}

/**
 * Creates and returns an [iterator][] of [index, byte] pairs from the
 * Buffer contents.
 * @returns and returns an iterator of [index, byte] pairs from the Buffer contents
 */
buffer.Buffer.prototype.entries = function() {}

/**
 * Returns a boolean indicating whether this and otherBuffer have exactly
 * the same bytes.
 * @param otherBuffer {Buffer}
 * @returns a boolean indicating whether this and otherBuffer have exactly the same bytes
 */
buffer.Buffer.prototype.equals = function(otherBuffer) {}

/**
 * Fills the Buffer with the specified value. If the offset (defaults to 0)
 * and end (defaults to buf.length) are not given the entire buffer will be
 * filled. The method returns a reference to the Buffer, so calls can be
 * chained.
 * @param value {String|Buffer|Number}
 * @param offset=0 {Number}
 * @param end=buf.length {Number}
 * @param encoding=`'utf8'` {String}
 */
buffer.Buffer.prototype.fill = function(value, offset, end, encoding) {}

/**
 * Operates similar to [Array#includes()][]. The value can be a String,
 * Buffer or Number. Strings are interpreted as UTF8 unless overridden with
 * the encoding argument. Buffers will use the entire Buffer (to compare a
 * partial Buffer use [buf.slice()][]). Numbers can range from 0 to 255.
 * @param value {String|Buffer|Number}
 * @param byteOffset=0 {Number}
 * @param encoding=`'utf8'` {String}
 */
buffer.Buffer.prototype.includes = function(value, byteOffset, encoding) {}

/**
 * Operates similar to [Array#indexOf()][] in that it returns either the
 * starting index position of value in Buffer or -1 if the Buffer does not
 * contain value. The value can be a String, Buffer or Number. Strings are
 * by default interpreted as UTF8. Buffers will use the entire Buffer (to
 * compare a partial Buffer use [buf.slice()][]). Numbers can range from 0
 * to 255.
 * @param value {String|Buffer|Number}
 * @param byteOffset=0 {Number}
 * @param encoding=`'utf8'` {String}
 */
buffer.Buffer.prototype.indexOf = function(value, byteOffset, encoding) {}

/**
 * Returns true if the encoding is a valid encoding argument, or false
 * otherwise.
 * @param encoding {String}
 * @returns true if the encoding is a valid encoding argument, or false otherwise
 */
buffer.Buffer.isEncoding = function(encoding) {}

/**
 * Creates and returns an [iterator][] of Buffer keys (indices).
 * @returns and returns an iterator of Buffer keys (indices)
 */
buffer.Buffer.prototype.keys = function() {}

/**
 * Reads a 64-bit double from the Buffer at the specified offset with
 * specified endian format (readDoubleBE() returns big endian,
 * readDoubleLE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readDoubleBE = function(offset, noAssert) {}

/**
 * Reads a 64-bit double from the Buffer at the specified offset with
 * specified endian format (readDoubleBE() returns big endian,
 * readDoubleLE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readDoubleLE = function(offset, noAssert) {}

/**
 * Reads a 32-bit float from the Buffer at the specified offset with
 * specified endian format (readFloatBE() returns big endian, readFloatLE()
 * returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readFloatBE = function(offset, noAssert) {}

/**
 * Reads a 32-bit float from the Buffer at the specified offset with
 * specified endian format (readFloatBE() returns big endian, readFloatLE()
 * returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readFloatLE = function(offset, noAssert) {}

/**
 * Reads a signed 16-bit integer from the Buffer at the specified offset
 * with the specified endian format (readInt16BE() returns big endian,
 * readInt16LE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readInt16BE = function(offset, noAssert) {}

/**
 * Reads a signed 16-bit integer from the Buffer at the specified offset
 * with the specified endian format (readInt16BE() returns big endian,
 * readInt16LE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readInt16LE = function(offset, noAssert) {}

/**
 * Reads a signed 32-bit integer from the Buffer at the specified offset
 * with the specified endian format (readInt32BE() returns big endian,
 * readInt32LE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readInt32BE = function(offset, noAssert) {}

/**
 * Reads a signed 32-bit integer from the Buffer at the specified offset
 * with the specified endian format (readInt32BE() returns big endian,
 * readInt32LE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readInt32LE = function(offset, noAssert) {}

/**
 * Reads a signed 8-bit integer from the Buffer at the specified offset.
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readInt8 = function(offset, noAssert) {}

/**
 * Reads byteLength number of bytes from the Buffer at the specified offset
 * and interprets the result as a two&#39;s complement signed value.
 * Supports up to 48 bits of accuracy. For example:
 * @param offset {Number}
 * @param byteLength {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readIntBE = function(offset, byteLength, noAssert) {}

/**
 * Reads byteLength number of bytes from the Buffer at the specified offset
 * and interprets the result as a two&#39;s complement signed value.
 * Supports up to 48 bits of accuracy. For example:
 * @param offset {Number}
 * @param byteLength {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readIntLE = function(offset, byteLength, noAssert) {}

/**
 * Reads an unsigned 16-bit integer from the Buffer at the specified offset
 * with specified endian format (readInt32BE() returns big endian,
 * readInt32LE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readUInt16BE = function(offset, noAssert) {}

/**
 * Reads an unsigned 16-bit integer from the Buffer at the specified offset
 * with specified endian format (readInt32BE() returns big endian,
 * readInt32LE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readUInt16LE = function(offset, noAssert) {}

/**
 * Reads an unsigned 32-bit integer from the Buffer at the specified offset
 * with specified endian format (readInt32BE() returns big endian,
 * readInt32LE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readUInt32BE = function(offset, noAssert) {}

/**
 * Reads an unsigned 32-bit integer from the Buffer at the specified offset
 * with specified endian format (readInt32BE() returns big endian,
 * readInt32LE() returns little endian).
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readUInt32LE = function(offset, noAssert) {}

/**
 * Reads an unsigned 8-bit integer from the Buffer at the specified offset.
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readUInt8 = function(offset, noAssert) {}

/**
 * Reads byteLength number of bytes from the Buffer at the specified offset
 * and interprets the result as an unsigned integer. Supports up to 48 bits
 * of accuracy. For example:
 * @param offset {Number}
 * @param byteLength {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readUIntBE = function(offset, byteLength, noAssert) {}

/**
 * Reads byteLength number of bytes from the Buffer at the specified offset
 * and interprets the result as an unsigned integer. Supports up to 48 bits
 * of accuracy. For example:
 * @param offset {Number}
 * @param byteLength {Number}
 * @param noAssert=false {Boolean}
 */
buffer.Buffer.prototype.readUIntLE = function(offset, byteLength, noAssert) {}

/**
 * Returns a JSON representation of the Buffer instance.
 * [JSON.stringify()][] implicitly calls this function when stringifying a
 * Buffer instance.
 * @returns a JSON representation of the Buffer instance
 */
buffer.Buffer.prototype.toJSON = function() {}

/**
 * Creates and returns an [iterator][] for Buffer values (bytes). This
 * function is called automatically when the Buffer is used in a for..of
 * statement.
 * @returns and returns an iterator for Buffer values (bytes)
 */
buffer.Buffer.prototype.values = function() {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeDoubleBE() writes big endian, writeDoubleLE() writes little
 * endian). The value argument must be a valid 64-bit double.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeDoubleBE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeDoubleBE() writes big endian, writeDoubleLE() writes little
 * endian). The value argument must be a valid 64-bit double.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeDoubleLE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeFloatBE() writes big endian, writeFloatLE() writes little
 * endian). Behavior is unspecified if value is anything other than a
 * 32-bit float.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeFloatBE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeFloatBE() writes big endian, writeFloatLE() writes little
 * endian). Behavior is unspecified if value is anything other than a
 * 32-bit float.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeFloatLE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeInt16BE() writes big endian, writeInt16LE() writes little
 * endian). The value must be a valid signed 16-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeInt16BE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeInt16BE() writes big endian, writeInt16LE() writes little
 * endian). The value must be a valid signed 16-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeInt16LE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeInt32BE() writes big endian, writeInt32LE() writes little
 * endian). The value must be a valid signed 32-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeInt32BE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeInt32BE() writes big endian, writeInt32LE() writes little
 * endian). The value must be a valid signed 32-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeInt32LE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset. The value must be a
 * valid signed 8-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeInt8 = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset and byteLength.
 * @param value {Number}
 * @param offset {Number}
 * @param byteLength {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeIntBE = function(value, offset, byteLength, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset and byteLength.
 * @param value {Number}
 * @param offset {Number}
 * @param byteLength {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeIntLE = function(value, offset, byteLength, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeUInt16BE() writes big endian, writeUInt16LE() writes little
 * endian). The value must be a valid unsigned 16-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeUInt16BE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeUInt16BE() writes big endian, writeUInt16LE() writes little
 * endian). The value must be a valid unsigned 16-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeUInt16LE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeUInt32BE() writes big endian, writeUInt32LE() writes little
 * endian). The value must be a valid unsigned 32-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeUInt32BE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset with specified endian
 * format (writeUInt32BE() writes big endian, writeUInt32LE() writes little
 * endian). The value must be a valid unsigned 32-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeUInt32LE = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset. The value must be a
 * valid unsigned 8-bit integer.
 * @param value {Number}
 * @param offset {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeUInt8 = function(value, offset, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset and byteLength.
 * @param value {Number}
 * @param offset {Number}
 * @param byteLength {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeUIntBE = function(value, offset, byteLength, noAssert) {}

/**
 * Writes value to the Buffer at the specified offset and byteLength.
 * @param value {Number}
 * @param offset {Number}
 * @param byteLength {Number}
 * @param noAssert=false {Boolean}
 * @returns Numbers of bytes written
 */
buffer.Buffer.prototype.writeUIntLE = function(value, offset, byteLength, noAssert) {}

/**
 * Returns an un-pooled Buffer.
 * @constructor
 */
buffer.SlowBuffer = function() {}

/**
 * Returns the maximum number of bytes that will be returned when
 * buffer.inspect() is called. This can be overridden by user modules. See
 * [util.inspect()][] for more details on buffer.inspect() behavior.
 */
buffer.INSPECT_MAX_BYTES = 50;

exports = buffer;

