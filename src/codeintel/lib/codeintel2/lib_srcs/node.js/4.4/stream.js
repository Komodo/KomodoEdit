/**
 * A stream is an abstract interface implemented by various objects in
 * Node.js. For example a [request to an HTTP server][http-incoming-
 * message] is a stream, as is [process.stdout][]. Streams are readable,
 * writable, or both. All streams are instances of [EventEmitter][].
 */
var stream = {};

/**
 * Duplex streams are streams that implement both the [Readable][] and
 * [Writable][] interfaces.
 * @constructor
 */
stream.Duplex = function() {}

/**
 * The Readable stream interface is the abstraction for a source of data
 * that you are reading from. In other words, data comes out of a Readable
 * stream.
 * @constructor
 */
stream.Readable = function() {}

/**
 * This method returns whether or not the readable has been explicitly
 * paused by client code (using [stream.pause()][stream-pause] without a
 * corresponding [stream.resume()][stream-resume]).
 */
stream.Readable.prototype.isPaused = function() {}

/**
 * This method will cause a stream in flowing mode to stop emitting
 * [&#39;data&#39;][] events, switching out of flowing mode. Any data that
 * becomes available will remain in the internal buffer.
 * @returns `this`
 */
stream.Readable.prototype.pause = function() {}

/**
 * This method pulls all the data out of a readable stream, and writes it
 * to the supplied destination, automatically managing the flow so that the
 * destination is not overwhelmed by a fast readable stream.
 * @param destination {stream.Writable}
 * @param options {Object}
 */
stream.Readable.prototype.pipe = function(destination, options) {}

/**
 * The read() method pulls some data out of the internal buffer and returns
 * it. If there is no data available, then it will return null.
 * @param size {Number}
 */
stream.Readable.prototype.read = function(size) {}

/**
 * This method will cause the readable stream to resume emitting
 * [&#39;data&#39;][] events.
 * @returns `this`
 */
stream.Readable.prototype.resume = function() {}

/**
 * Call this function to cause the stream to return strings of the
 * specified encoding instead of Buffer objects. For example, if you do
 * readable.setEncoding(&#39;utf8&#39;), then the output data will be
 * interpreted as UTF-8 data, and returned as strings. If you do
 * readable.setEncoding(&#39;hex&#39;), then the data will be encoded in
 * hexadecimal string format.
 * @param encoding {String}
 * @returns `this`
 */
stream.Readable.prototype.setEncoding = function(encoding) {}

/**
 * This method will remove the hooks set up for a previous
 * [stream.pipe()][] call.
 * @param destination {stream.Writable}
 */
stream.Readable.prototype.unpipe = function(destination) {}

/**
 * This is useful in certain cases where a stream is being consumed by a
 * parser, which needs to "un-consume" some data that it has optimistically
 * pulled out of the source, so that the stream can be passed on to some
 * other party.
 * @param chunk {Buffer|String}
 */
stream.Readable.prototype.unshift = function(chunk) {}

/**
 * Versions of Node.js prior to v0.10 had streams that did not implement
 * the entire Streams API as it is today. (See [Compatibility][] for more
 * information.)
 * @param stream {Stream}
 */
stream.Readable.prototype.wrap = function(stream) {}

/** @__local__ */ stream.Readable.__events__ = {};

/**
 * Emitted when the stream and any of its underlying resources (a file
 * descriptor, for example) have been closed. The event indicates that no
 * more events will be emitted, and no further computation will occur. Not
 * all streams will emit the &#39;close&#39; event.
 */
stream.Readable.__events__.close = function() {};

/**
 * Attaching a &#39;data&#39; event listener to a stream that has not been
 * explicitly paused will switch the stream into flowing mode. Data will
 * then be passed as soon as it is available. If you just want to get all
 * the data out of the stream as fast as possible, this is the best way to
 * do so.
 */
stream.Readable.__events__.data = function() {};

/**
 * This event fires when there will be no more data to read. Note that the
 * &#39;end&#39; event will not fire unless the data is completely
 * consumed. This can be done by switching into flowing mode, or by calling
 * [stream.read()][stream-read] repeatedly until you get to the end.
 */
stream.Readable.__events__.end = function() {};

/**
 * Emitted if there was an error receiving data.
 */
stream.Readable.__events__.error = function() {};

/**
 * When a chunk of data can be read from the stream, it will emit a
 * &#39;readable&#39; event. In some cases, listening for a
 * &#39;readable&#39; event will cause some data to be read into the
 * internal buffer from the underlying system, if it hadn&#39;t already.
 * Once the internal buffer is drained, a &#39;readable&#39; event will
 * fire again when more data is available. The &#39;readable&#39; event is
 * not emitted in the "flowing" mode with the sole exception of the last
 * one, on end-of-stream. The &#39;readable&#39; event indicates that the
 * stream has new information: either new data is available or the end of
 * the stream has been reached. In the former case, [stream.read()][stream-
 * read] will return that data. In the latter case, [stream.read()][stream-
 * read] will return null. For instance, in the following example, foo.txt
 * is an empty file: The output of running this script is:
 */
stream.Readable.__events__.readable = function() {};

/**
 * Transform streams are [Duplex][] streams where the output is in some way
 * computed from the input. They implement both the [Readable][] and
 * [Writable][] interfaces.
 * @constructor
 */
stream.Transform = function() {}

/**
 * The Writable stream interface is an abstraction for a destination that
 * you are writing data to.
 * @constructor
 */
stream.Writable = function() {}

/**
 * Forces buffering of all writes.
 */
stream.Writable.prototype.cork = function() {}

/**
 * Call this method when no more data will be written to the stream. If
 * supplied, the callback is attached as a listener on the
 * [&#39;finish&#39;][] event.
 * @param chunk {String|Buffer}
 * @param encoding {String}
 * @param callback {Function}
 */
stream.Writable.prototype.end = function(chunk, encoding, callback) {}

/**
 * Sets the default encoding for a writable stream.
 * @param encoding {String}
 */
stream.Writable.prototype.setDefaultEncoding = function(encoding) {}

/**
 * Flush all data, buffered since [stream.cork()][] call.
 */
stream.Writable.prototype.uncork = function() {}

/**
 * This method writes some data to the underlying system, and calls the
 * supplied callback once the data has been fully handled.
 * @param chunk {String|Buffer}
 * @param encoding {String}
 * @param callback {Function}
 * @returns `true` if the data was handled completely.
 */
stream.Writable.prototype.write = function(chunk, encoding, callback) {}

/** @__local__ */ stream.Writable.__events__ = {};

/**
 * If a [stream.write(chunk)][stream-write] call returns false, then the
 * &#39;drain&#39; event will indicate when it is appropriate to begin
 * writing more data to the stream.
 */
stream.Writable.__events__.drain = function() {};

/**
 * Emitted if there was an error when writing or piping data.
 */
stream.Writable.__events__.error = function() {};

/**
 * When the [stream.end()][stream-end] method has been called, and all data
 * has been flushed to the underlying system, this event is emitted.
 */
stream.Writable.__events__.finish = function() {};

/**
 * This is emitted whenever the [stream.pipe()][] method is called on a
 * readable stream, adding this writable to its set of destinations.
 */
stream.Writable.__events__.pipe = function() {};

/**
 * This is emitted whenever the [stream.unpipe()][] method is called on a
 * readable stream, removing this writable from its set of destinations.
 */
stream.Writable.__events__.unpipe = function() {};

var events = require('events');

exports = stream;

