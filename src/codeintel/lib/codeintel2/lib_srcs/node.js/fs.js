/**
 * File I/O is provided by simple wrappers around standard POSIX functions.
 * To use this module do require('fs'). All the methods have asynchronous
 * and synchronous forms.
 */
var fs = {};

/**
 * Asynchronous rename(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param [callback]
 * @param path1
 * @param path2
 */
fs.rename = function(path1, path2, callback) {}

/**
 * Synchronous version of string-based fs.write(). Returns the number of
 * bytes written.
 * @param encoding='utf8'
 * @param fd
 * @param position
 * @param str
 */
fs.writeSync = function(fd, str, position, encoding) {}

/**
 * WriteStream is a Writable Stream.
 */
fs.WriteStream = function() {}
fs.WriteStream.prototype = {}

/**
 * Synchronous chmod(2).
 * @param mode
 * @param path
 */
fs.chmodSync = function(path, mode) {}

/**
 * Objects returned from fs.stat() and fs.lstat() are of this type.
 */
fs.Stats = function() {}
fs.Stats.prototype = {}

/**
 * Asynchronous chmod(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param [callback]
 * @param mode
 * @param path
 */
fs.chmod = function(path, mode, callback) {}

/**
 * Synchronous readdir(3). Returns an array of filenames excluding '.' and
 * '..'.
 * @param path
 */
fs.readdirSync = function(path) {}

/**
 * Synchronous readlink(2). Returns the resolved path.
 * @param path
 */
fs.readlinkSync = function(path) {}

/**
 * Synchronous close(2).
 * @param fd
 */
fs.closeSync = function(fd) {}

/**
 * Asynchronous close(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param [callback]
 * @param fd
 */
fs.close = function(fd, callback) {}

/**
 * Asynchronous file open. See open(2). Flags can be 'r', 'r+', 'w', 'w+',
 * 'a', or 'a+'. mode defaults to 0666. The callback gets two arguments
 * (err, fd).
 * @param [callback]
 * @param [mode]
 * @param flags
 * @param path
 */
fs.open = function(path, flags, mode, callback) {}

/**
 * Synchronous lstat(2). Returns an instance of fs.Stats.
 * @param path
 * @returns Stats
 */
fs.lstatSync = function(path) {}

/**
 * Synchronous link(2).
 * @param dstpath
 * @param srcpath
 */
fs.linkSync = function(srcpath, dstpath) {}

/**
 * Synchronous stat(2). Returns an instance of fs.Stats.
 * @param path
 * @returns Stats
 */
fs.statSync = function(path) {}

/**
 * Asynchronous mkdir(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param [callback]
 * @param mode
 * @param path
 */
fs.mkdir = function(path, mode, callback) {}

/**
 * Asynchronously reads the entire contents of a file. Example:
 * @param [callback]
 * @param [encoding]
 * @param filename
 */
fs.readFile = function(filename, encoding, callback) {}

/**
 * Write buffer to the file specified by fd.
 * @param [callback]
 * @param buffer
 * @param fd
 * @param length
 * @param offset
 * @param position
 */
fs.write = function(fd, buffer, offset, length, position, callback) {}

/**
 * Synchronous realpath(2). Returns the resolved path.
 * @param path
 */
fs.realpathSync = function(path) {}

/**
 * Asynchronously writes data to a file, replacing the file if it already
 * exists. data can be a string or a buffer.
 * @param [callback]
 * @param data
 * @param encoding='utf8'
 * @param filename
 */
fs.writeFile = function(filename, data, encoding, callback) {}

/**
 * Asynchronous rmdir(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param [callback]
 * @param path
 */
fs.rmdir = function(path, callback) {}

/**
 * Stop watching for changes on filename.
 * @param filename
 */
fs.unwatchFile = function(filename) {}

/**
 * Asynchronous fstat(2). The callback gets two arguments (err, stats)
 * where stats is a fs.Stats object.
 * @param [callback]
 * @param fd
 */
fs.fstat = function(fd, callback) {}

/**
 * ReadStream is a Readable Stream.
 */
fs.ReadStream = function() {}
fs.ReadStream.prototype = {}

/**
 * Asynchronous realpath(2). The callback gets two arguments (err,
 * resolvedPath).
 * @param [callback]
 * @param path
 */
fs.realpath = function(path, callback) {}

/**
 * Asynchronous stat(2). The callback gets two arguments (err, stats) where
 * stats is a `fs.Stats` object. It looks like this:
 * @param [callback]
 * @param path
 */
fs.stat = function(path, callback) {}

/**
 * Synchronous version of string-based fs.read. Returns the number of
 * bytesRead.
 * @param encoding
 * @param fd
 * @param length
 * @param position
 */
fs.readSync = function(fd, length, position, encoding) {}

/**
 * Asynchronous ftruncate(2). No arguments other than a possible exception
 * are given to the completion callback.
 * @param [callback]
 * @param fd
 * @param len
 */
fs.truncate = function(fd, len, callback) {}

/**
 * Asynchronous lstat(2). The callback gets two arguments (err, stats)
 * where stats is a fs.Stats object. lstat() is identical to stat(), except
 * that if path is a symbolic link, then the link itself is stat-ed, not
 * the file that it refers to.
 * @param [callback]
 * @param path
 */
fs.lstat = function(path, callback) {}

/**
 * Synchronous fstat(2). Returns an instance of fs.Stats.
 * @param fd
 * @returns Stats
 */
fs.fstatSync = function(fd) {}

/**
 * The synchronous version of fs.writeFile.
 * @param data
 * @param encoding='utf8'
 * @param filename
 */
fs.writeFileSync = function(filename, data, encoding) {}

/**
 * Asynchronous symlink(2). No arguments other than a possible exception
 * are given to the completion callback.
 * @param [callback]
 * @param linkdata
 * @param path
 */
fs.symlink = function(linkdata, path, callback) {}

/**
 * Synchronous symlink(2).
 * @param linkdata
 * @param path
 */
fs.symlinkSync = function(linkdata, path) {}

/**
 * Synchronous rmdir(2).
 * @param path
 */
fs.rmdirSync = function(path) {}

/**
 * Asynchronous link(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param [callback]
 * @param dstpath
 * @param srcpath
 */
fs.link = function(srcpath, dstpath, callback) {}

/**
 * Asynchronous readdir(3). Reads the contents of a directory. The callback
 * gets two arguments (err, files) where files is an array of the names of
 * the files in the directory excluding '.' and '..'.
 * @param [callback]
 * @param path
 */
fs.readdir = function(path, callback) {}

/**
 * Returns a new ReadStream object (See Readable Stream).
 * @param [options]
 * @param path
 * @returns stream.ReadableStream
 */
fs.createReadStream = function(path, options) {}

/**
 * Synchronous version of fs.readFile. Returns the contents of the
 * filename.
 * @param [encoding]
 * @param filename
 */
fs.readFileSync = function(filename, encoding) {}

/**
 * Asynchronous unlink(2). No arguments other than a possible exception are
 * given to the completion callback.
 * @param [callback]
 * @param path
 */
fs.unlink = function(path, callback) {}

/**
 * Synchronous ftruncate(2).
 * @param fd
 * @param len
 */
fs.truncateSync = function(fd, len) {}

/**
 * Read data from the file specified by fd.
 * @param [callback]
 * @param buffer
 * @param fd
 * @param length
 * @param offset
 * @param position
 */
fs.read = function(fd, buffer, offset, length, position, callback) {}

/**
 * Synchronous rename(2).
 * @param path1
 * @param path2
 */
fs.renameSync = function(path1, path2) {}

/**
 * Synchronous mkdir(2).
 * @param mode
 * @param path
 */
fs.mkdirSync = function(path, mode) {}

/**
 * Watch for changes on filename. The callback listener will be called each
 * time the file is accessed.
 * @param [options]
 * @param filename
 * @param listener
 */
fs.watchFile = function(filename, options, listener) {}

/**
 * Returns a new WriteStream object (See Writable Stream).
 * @param [options]
 * @param path
 * @returns stream.WritableStream
 */
fs.createWriteStream = function(path, options) {}

/**
 * Synchronous open(2).
 * @param [mode]
 * @param flags
 * @param path
 */
fs.openSync = function(path, flags, mode) {}

/**
 * Asynchronous readlink(2). The callback gets two arguments (err,
 * resolvedPath).
 * @param [callback]
 * @param path
 */
fs.readlink = function(path, callback) {}

/**
 * Synchronous unlink(2).
 * @param path
 */
fs.unlinkSync = function(path) {}


                /* see http://nodejs.org/docs/v0.4.2/api/fs.html#fs.Stats */
                fs.Stats.prototype = {
                    isFile: function() {},
                    isDirectory: function() {},
                    isBlockDevice: function() {},
                    isCharacterDevice: function() {},
                    isSymbolicLink: function() {},
                    isFIFO: function() {},
                    isSocket: function() {}
                };
                /* required for createReadStream() / createWriteStream() */
                var stream = require('stream');
                exports = fs;

