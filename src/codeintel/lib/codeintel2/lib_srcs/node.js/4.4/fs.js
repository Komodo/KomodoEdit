/**
 * File I/O is provided by simple wrappers around standard POSIX functions.
 * To use this module do require(&#39;fs&#39;). All the methods have
 * asynchronous and synchronous forms.
 */
var fs = {};

/**
 * Asynchronous rename(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param oldPath
 * @param newPath
 * @param callback
 */
fs.rename = function(oldPath, newPath, callback) {}

/**
 * Synchronous versions of [fs.write()][]. Returns the number of bytes
 * written.
 * @param fd
 * @param data
 * @param position
 * @param encoding
 * @returns {Number} the number of bytes written
 */
fs.writeSync = function(fd, data, position, encoding) {}

/**
 * Synchronous versions of [fs.write()][]. Returns the number of bytes
 * written.
 * @param fd
 * @param data
 * @param position
 * @param encoding
 * @returns {Number} the number of bytes written
 */
fs.writeSync = function(fd, data, position, encoding) {}

/**
 * WriteStream is a [Writable Stream][].
 * @constructor
 */
fs.WriteStream = function() {}

/**
 * The number of bytes written so far. Does not include data that is still
 * queued for writing.
 */
fs.WriteStream.prototype.bytesWritten = 0;

/**
 * The path to the file the stream is writing to.
 */
fs.WriteStream.prototype.path = 0;

/** @__local__ */ fs.WriteStream.__events__ = {};

/**
 * Emitted when the WriteStream&#39;s file is opened.
 * @param fd {Number}
 */
fs.WriteStream.__events__.open = function(fd) {};

/**
 * Synchronous chmod(2). Returns undefined.
 * @param path
 * @param mode
 * @returns undefined
 */
fs.chmodSync = function(path, mode) {}

/**
 * Objects returned from [fs.stat()][], [fs.lstat()][] and [fs.fstat()][]
 * and their synchronous counterparts are of this type.
 * @constructor
 */
fs.Stats = function() {}

/**
 * Asynchronous chmod(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param path
 * @param mode
 * @param callback
 */
fs.chmod = function(path, mode, callback) {}

/**
 * Synchronous readdir(3). Returns an array of filenames excluding
 * &#39;.&#39; and &#39;..&#39;.
 * @param path
 * @returns {Array} an array of filenames excluding &#39;.&#39; and &#39;..&#39;
 */
fs.readdirSync = function(path) {}

/**
 * Synchronous readlink(2). Returns the symbolic link&#39;s string value.
 * @param path
 * @returns {String} the symbolic link&#39;s string value
 */
fs.readlinkSync = function(path) {}

/**
 * Synchronous close(2). Returns undefined.
 * @param fd
 * @returns undefined
 */
fs.closeSync = function(fd) {}

/**
 * Asynchronous close(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param fd
 * @param callback
 */
fs.close = function(fd, callback) {}

/**
 * Asynchronous file open. See open(2). flags can be:
 * @param path
 * @param flags
 * @param mode
 * @param callback
 */
fs.open = function(path, flags, mode, callback) {}

/**
 * Synchronous lstat(2). Returns an instance of fs.Stats.
 * @param path
 * @returns {fs.Stats} an instance of fs.Stats
 */
fs.lstatSync = function(path) {}

/**
 * Synchronous link(2). Returns undefined.
 * @param srcpath
 * @param dstpath
 * @returns undefined
 */
fs.linkSync = function(srcpath, dstpath) {}

/**
 * Synchronous stat(2). Returns an instance of [fs.Stats][].
 * @param path
 * @returns {fs.Stats} an instance of fs.Stats
 */
fs.statSync = function(path) {}

/**
 * Asynchronous mkdir(2). No arguments other than a possible exception are
 * given to the completion callback. mode defaults to 0o777.
 * @param path
 * @param mode=0o777 {Number}
 * @param callback
 */
fs.mkdir = function(path, mode, callback) {}

/**
 * Asynchronously reads the entire contents of a file. Example:
 * @param file {String | Integer}
 * @param options {Object | String}
 * @param callback {Function}
 */
fs.readFile = function(file, options, callback) {}

/**
 * Write buffer to the file specified by fd.
 * @param fd
 * @param buffer
 * @param offset
 * @param length
 * @param position
 * @param callback
 */
fs.write = function(fd, buffer, offset, length, position, callback) {}

/**
 * Write data to the file specified by fd. If data is not a Buffer instance
 * then the value will be coerced to a string.
 * @param fd
 * @param data
 * @param position
 * @param encoding
 * @param callback
 */
fs.write = function(fd, data, position, encoding, callback) {}

/**
 * Synchronous realpath(2). Returns the resolved path. cache is an object
 * literal of mapped paths that can be used to force a specific path
 * resolution or avoid additional fs.stat calls for known real paths.
 * @param path
 * @param cache
 * @returns the resolved path
 */
fs.realpathSync = function(path, cache) {}

/**
 * Asynchronously writes data to a file, replacing the file if it already
 * exists.
 * @param file {String | Integer}
 * @param data {String | Buffer}
 * @param options {Object | String}
 * @param callback {Function}
 */
fs.writeFile = function(file, data, options, callback) {}

/**
 * Asynchronous rmdir(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param path
 * @param callback
 */
fs.rmdir = function(path, callback) {}

/**
 * Stop watching for changes on filename. If listener is specified, only
 * that particular listener is removed. Otherwise, all listeners are
 * removed and you have effectively stopped watching filename.
 * @param filename
 * @param listener
 */
fs.unwatchFile = function(filename, listener) {}

/**
 * Asynchronous fstat(2). The callback gets two arguments (err, stats)
 * where stats is a fs.Stats object. fstat() is identical to [stat()][],
 * except that the file to be stat-ed is specified by the file descriptor
 * fd.
 * @param fd
 * @param callback
 */
fs.fstat = function(fd, callback) {}

/**
 * ReadStream is a [Readable Stream][].
 * @constructor
 */
fs.ReadStream = function() {}

/**
 * The path to the file the stream is reading from.
 */
fs.ReadStream.prototype.path = 0;

/** @__local__ */ fs.ReadStream.__events__ = {};

/**
 * Emitted when the ReadStream&#39;s file is opened.
 * @param fd {Number}
 */
fs.ReadStream.__events__.open = function(fd) {};

/**
 * Asynchronous realpath(2). The callback gets two arguments (err,
 * resolvedPath). May use process.cwd to resolve relative paths. cache is
 * an object literal of mapped paths that can be used to force a specific
 * path resolution or avoid additional fs.stat calls for known real paths.
 * @param path
 * @param cache
 * @param callback
 */
fs.realpath = function(path, cache, callback) {}

/**
 * Asynchronous stat(2). The callback gets two arguments (err, stats) where
 * stats is a [fs.Stats][] object. See the [fs.Stats][] section for more
 * information.
 * @param path
 * @param callback
 */
fs.stat = function(path, callback) {}

/**
 * Synchronous version of [fs.read()][]. Returns the number of bytesRead.
 * @param fd
 * @param buffer
 * @param offset
 * @param length
 * @param position
 * @returns {Number} the number of bytesRead
 */
fs.readSync = function(fd, buffer, offset, length, position) {}

/**
 * Asynchronous truncate(2). No arguments other than a possible exception
 * are given to the completion callback. A file descriptor can also be
 * passed as the first argument. In this case, fs.ftruncate() is called.
 * @param path
 * @param len
 * @param callback
 */
fs.truncate = function(path, len, callback) {}

/**
 * Asynchronous lstat(2). The callback gets two arguments (err, stats)
 * where stats is a fs.Stats object. lstat() is identical to stat(), except
 * that if path is a symbolic link, then the link itself is stat-ed, not
 * the file that it refers to.
 * @param path
 * @param callback
 */
fs.lstat = function(path, callback) {}

/**
 * Synchronous fstat(2). Returns an instance of fs.Stats.
 * @param fd
 * @returns {fs.Stats} an instance of fs.Stats
 */
fs.fstatSync = function(fd) {}

/**
 * The synchronous version of [fs.writeFile()][]. Returns undefined.
 * @param file
 * @param data
 * @param options
 * @returns undefined
 */
fs.writeFileSync = function(file, data, options) {}

/**
 * Asynchronous symlink(2). No arguments other than a possible exception
 * are given to the completion callback.
 * @param target
 * @param path
 * @param type
 * @param callback
 */
fs.symlink = function(target, path, type, callback) {}

/**
 * Synchronous symlink(2). Returns undefined.
 * @param target
 * @param path
 * @param type
 * @returns undefined
 */
fs.symlinkSync = function(target, path, type) {}

/**
 * Synchronous rmdir(2). Returns undefined.
 * @param path
 * @returns undefined
 */
fs.rmdirSync = function(path) {}

/**
 * Asynchronous link(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param srcpath
 * @param dstpath
 * @param callback
 */
fs.link = function(srcpath, dstpath, callback) {}

/**
 * Asynchronous readdir(3). Reads the contents of a directory.
 * @param path
 * @param callback
 */
fs.readdir = function(path, callback) {}

/**
 * Returns a new [ReadStream][] object. (See [Readable Stream][]).
 * @param path
 * @param options
 * @returns {stream.ReadableStream}
 */
fs.createReadStream = function(path, options) {}

/**
 * Synchronous version of [fs.readFile][]. Returns the contents of the
 * file.
 * @param file
 * @param options
 * @returns the contents of the file
 */
fs.readFileSync = function(file, options) {}

/**
 * Asynchronous unlink(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param path
 * @param callback
 */
fs.unlink = function(path, callback) {}

/**
 * Synchronous truncate(2). Returns undefined.
 * @param path
 * @param len
 * @returns undefined
 */
fs.truncateSync = function(path, len) {}

/**
 * Read data from the file specified by fd.
 * @param fd
 * @param buffer
 * @param offset
 * @param length
 * @param position
 * @param callback
 */
fs.read = function(fd, buffer, offset, length, position, callback) {}

/**
 * Synchronous rename(2). Returns undefined.
 * @param oldPath
 * @param newPath
 * @returns undefined
 */
fs.renameSync = function(oldPath, newPath) {}

/**
 * Synchronous mkdir(2). Returns undefined.
 * @param path
 * @param mode
 * @returns undefined
 */
fs.mkdirSync = function(path, mode) {}

/**
 * Watch for changes on filename. The callback listener will be called each
 * time the file is accessed.
 * @param filename
 * @param options
 * @param listener
 */
fs.watchFile = function(filename, options, listener) {}

/**
 * Returns a new [WriteStream][] object. (See [Writable Stream][]).
 * @param path
 * @param options
 * @returns {stream.WritableStream}
 */
fs.createWriteStream = function(path, options) {}

/**
 * Synchronous version of [fs.open()][]. Returns an integer representing
 * the file descriptor.
 * @param path
 * @param flags
 * @param mode
 * @returns an integer representing the file descriptor
 */
fs.openSync = function(path, flags, mode) {}

/**
 * Asynchronous readlink(2). The callback gets two arguments (err,
 * linkString).
 * @param path
 * @param callback
 */
fs.readlink = function(path, callback) {}

/**
 * Synchronous unlink(2). Returns undefined.
 * @param path
 * @returns undefined
 */
fs.unlinkSync = function(path) {}

/**
 * Tests a user&#39;s permissions for the file specified by path. mode is
 * an optional integer that specifies the accessibility checks to be
 * performed. The following constants define the possible values of mode.
 * It is possible to create a mask consisting of the bitwise OR of two or
 * more values.
 * @param path
 * @param mode
 * @param callback
 */
fs.access = function(path, mode, callback) {}

/**
 * Synchronous version of [fs.access()][]. This throws if any accessibility
 * checks fail, and does nothing otherwise.
 * @param path
 * @param mode
 */
fs.accessSync = function(path, mode) {}

/**
 * Asynchronously append data to a file, creating the file if it does not
 * yet exist.
 * @param file {String|Number}
 * @param data {String|Buffer}
 * @param options {Object|String}
 * @param callback {Function}
 */
fs.appendFile = function(file, data, options, callback) {}

/**
 * The synchronous version of [fs.appendFile()][]. Returns undefined.
 * @param file
 * @param data
 * @param options
 * @returns undefined
 */
fs.appendFileSync = function(file, data, options) {}

/**
 * Asynchronous chown(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param path
 * @param uid
 * @param gid
 * @param callback
 */
fs.chown = function(path, uid, gid, callback) {}

/**
 * Synchronous chown(2). Returns undefined.
 * @param path
 * @param uid
 * @param gid
 * @returns undefined
 */
fs.chownSync = function(path, uid, gid) {}

/**
 * Test whether or not the given path exists by checking with the file
 * system.
 * @param path
 * @param callback
 */
fs.exists = function(path, callback) {}

/**
 * Synchronous version of [fs.exists()][].
 * @param path
 */
fs.existsSync = function(path) {}

/**
 * Asynchronous fchmod(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param fd
 * @param mode
 * @param callback
 */
fs.fchmod = function(fd, mode, callback) {}

/**
 * Synchronous fchmod(2). Returns undefined.
 * @param fd
 * @param mode
 * @returns undefined
 */
fs.fchmodSync = function(fd, mode) {}

/**
 * Asynchronous fchown(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param fd
 * @param uid
 * @param gid
 * @param callback
 */
fs.fchown = function(fd, uid, gid, callback) {}

/**
 * Synchronous fchown(2). Returns undefined.
 * @param fd
 * @param uid
 * @param gid
 * @returns undefined
 */
fs.fchownSync = function(fd, uid, gid) {}

/**
 * Objects returned from fs.watch() are of this type.
 * @constructor
 */
fs.FSWatcher = function() {}
fs.FSWatcher.prototype = new events.EventEmitter();

/**
 * Stop watching for changes on the given fs.FSWatcher.
 */
fs.FSWatcher.prototype.close = function() {}

/** @__local__ */ fs.FSWatcher.__events__ = {};

/**
 * Emitted when something changes in a watched directory or file. See more
 * details in [fs.watch()][].
 * @param event {String}
 * @param filename {String}
 */
fs.FSWatcher.__events__.change = function(event, filename) {};

/**
 * Emitted when an error occurs.
 * @param exception {Error}
 */
fs.FSWatcher.__events__.error = function(exception) {};

/**
 * Asynchronous fsync(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param fd
 * @param callback
 */
fs.fsync = function(fd, callback) {}

/**
 * Synchronous fsync(2). Returns undefined.
 * @param fd
 * @returns undefined
 */
fs.fsyncSync = function(fd) {}

/**
 * Asynchronous ftruncate(2). No arguments other than a possible exception
 * are given to the completion callback.
 * @param fd
 * @param len
 * @param callback
 */
fs.ftruncate = function(fd, len, callback) {}

/**
 * Synchronous ftruncate(2). Returns undefined.
 * @param fd
 * @param len
 * @returns undefined
 */
fs.ftruncateSync = function(fd, len) {}

/**
 * Change the file timestamps of a file referenced by the supplied file
 * descriptor.
 * @param fd
 * @param atime
 * @param mtime
 * @param callback
 */
fs.futimes = function(fd, atime, mtime, callback) {}

/**
 * Synchronous version of [fs.futimes()][]. Returns undefined.
 * @param fd
 * @param atime
 * @param mtime
 * @returns undefined
 */
fs.futimesSync = function(fd, atime, mtime) {}

/**
 * Asynchronous lchmod(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param path
 * @param mode
 * @param callback
 */
fs.lchmod = function(path, mode, callback) {}

/**
 * Synchronous lchmod(2). Returns undefined.
 * @param path
 * @param mode
 * @returns undefined
 */
fs.lchmodSync = function(path, mode) {}

/**
 * Asynchronous lchown(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param path
 * @param uid
 * @param gid
 * @param callback
 */
fs.lchown = function(path, uid, gid, callback) {}

/**
 * Synchronous lchown(2). Returns undefined.
 * @param path
 * @param uid
 * @param gid
 * @returns undefined
 */
fs.lchownSync = function(path, uid, gid) {}

/**
 * Change file timestamps of the file referenced by the supplied path.
 * @param path
 * @param atime
 * @param mtime
 * @param callback
 */
fs.utimes = function(path, atime, mtime, callback) {}

/**
 * Synchronous version of [fs.utimes()][]. Returns undefined.
 * @param path
 * @param atime
 * @param mtime
 * @returns undefined
 */
fs.utimesSync = function(path, atime, mtime) {}

/**
 * Watch for changes on filename, where filename is either a file or a
 * directory. The returned object is a [fs.FSWatcher][].
 * @param filename
 * @param options
 * @param listener
 * @returns {fs.FSWatcher}
 */
fs.watch = function(filename, options, listener) {}

/* see http://nodejs.org/docs/v0.6.12/api/fs.html#fs.Stats */
fs.Stats.prototype = {
    isFile: function() {},
    isDirectory: function() {},
    isBlockDevice: function() {},
    isCharacterDevice: function() {},
    isSymbolicLink: function() {},
    isFIFO: function() {},
    isSocket: function() {},
};
/* required for createReadStream() / createWriteStream() */
var stream = require('stream');
var events = require('events');

exports = fs;

