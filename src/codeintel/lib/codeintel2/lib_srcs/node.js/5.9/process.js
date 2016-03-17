
/**
 * The process object is a global object and can be accessed from anywhere.
 * @type {Object}
 */
var process = {};
process.__proto__ = events.EventEmitter;

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 * @param id
 */
process.setuid = function(id) {}

/**
 * Once the current event loop turn runs to completion, call the callback
 * function.
 * @param callback {Function}
 * @param arg
 */
process.nextTick = function(callback, arg) {}

/**
 * A Writable Stream to stdout (on fd 1).
 * @type {tty.WriteStream}
 */
process.stdout = 0;

/**
 * The PID of the process.
 */
process.pid = 0;

/**
 * Returns an object describing the memory usage of the Node.js process
 * measured in bytes.
 * @returns an object describing the memory usage of the Node.js process measured in bytes
 */
process.memoryUsage = function() {}

/**
 * Send a signal to a process. pid is the process id and signal is the
 * string describing the signal to send. Signal names are strings like
 * SIGINT or SIGHUP. If omitted, the signal will be SIGTERM.
 * @param pid
 * @param signal='SIGTERM' {String}
 */
process.kill = function(pid, signal) {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 */
process.getgid = function() {}

/**
 * Getter/setter to set what is displayed in ps.
 */
process.title = 0;

/**
 * Sets or reads the process&#39;s file mode creation mask. Child processes
 * inherit the mask from the parent process. Returns the old mask if mask
 * argument is given, otherwise returns the current mask.
 * @param mask
 * @returns the old mask if mask argument is given, otherwise returns the current mask
 */
process.umask = function(mask) {}

/**
 * What platform you&#39;re running on:
 */
process.platform = 0;

/**
 * A compiled-in property that exposes NODE_VERSION.
 */
process.version = 0;

/**
 * Ends the process with the specified code. If omitted, exit uses the
 * &#39;success&#39; code 0.
 * @param code=0 {Number}
 */
process.exit = function(code) {}

/**
 * An object containing the user environment. See environ(7).
 */
process.env = 0;

/**
 * Returns the current working directory of the process.
 * @returns the current working directory of the process
 */
process.cwd = function() {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 * @param id
 */
process.setgid = function(id) {}

/**
 * An array containing the command line arguments. The first element will
 * be &#39;node&#39;, the second element will be the name of the JavaScript
 * file. The next elements will be any additional command line arguments.
 */
process.argv = 0;

/**
 * Changes the current working directory of the process or throws an
 * exception if that fails.
 * @param directory
 */
process.chdir = function(directory) {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 */
process.getuid = function() {}

/**
 * A Readable Stream for stdin (on fd 0).
 * @type {tty.ReadStream}
 */
process.stdin = 0;

/**
 * A writable stream to stderr (on fd 2).
 * @type {tty.WriteStream}
 */
process.stderr = 0;

/**
 * This is the absolute pathname of the executable that started the
 * process.
 */
process.execPath = 0;

/**
 * This causes Node.js to emit an abort. This will cause Node.js to exit
 * and generate a core file.
 */
process.abort = function() {}

/**
 * What processor architecture you&#39;re running on: &#39;arm&#39;,
 * &#39;ia32&#39;, or &#39;x64&#39;.
 * @type {String}
 */
process.arch = 0;

/**
 * An Object containing the JavaScript representation of the configure
 * options that were used to compile the current Node.js executable. This
 * is the same as the config.gypi file that was produced when running the
 * ./configure script.
 */
process.config = 0;

/**
 * If process.connected is false, it is no longer possible to send
 * messages.
 */
process.connected = 0;

/**
 * Close the IPC channel to the parent process, allowing this child to exit
 * gracefully once there are no other connections keeping it alive.
 */
process.disconnect = function() {}

/**
 * This is the set of Node.js-specific command line options from the
 * executable that started the process. These options do not show up in
 * process.argv, and do not include the Node.js executable, the name of the
 * script, or any options following the script name. These options are
 * useful in order to spawn child processes with the same execution
 * environment as the parent.
 */
process.execArgv = 0;

/**
 * A number which will be the process exit code, when the process either
 * exits gracefully, or is exited via [process.exit()][] without specifying
 * a code.
 * @type {Number}
 */
process.exitCode = 0;

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 */
process.getegid = function() {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 */
process.geteuid = function() {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 */
process.getgroups = function() {}

/**
 * Returns the current high-resolution real time in a [seconds,
 * nanoseconds] tuple Array. It is relative to an arbitrary time in the
 * past. It is not related to the time of day and therefore not subject to
 * clock drift. The primary use is for measuring performance between
 * intervals.
 * @returns the current high-resolution real time in a [seconds, nanoseconds] tuple Array
 */
process.hrtime = function() {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 * @param user
 * @param extra_group
 */
process.initgroups = function(user, extra_group) {}

/**
 * Alternate way to retrieve [require.main][]. The difference is that if
 * the main module changes at runtime, require.main might still refer to
 * the original main module in modules that were required before the change
 * occurred. Generally it&#39;s safe to assume that the two refer to the
 * same module.
 */
process.mainModule = 0;

/**
 * An Object containing metadata related to the current release, including
 * URLs for the source tarball and headers-only tarball.
 */
process.release = 0;

/**
 * When Node.js is spawned with an IPC channel attached, it can send
 * messages to its parent process using process.send(). Each will be
 * received as a [&#39;message&#39;][] event on the parent&#39;s
 * ChildProcess object.
 * @param message {Object}
 * @param sendHandle {Handle}
 * @param options {Object}
 * @param callback {Function}
 */
process.send = function(message, sendHandle, options, callback) {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 * @param id
 */
process.setegid = function(id) {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 * @param id
 */
process.seteuid = function(id) {}

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 * @param groups
 */
process.setgroups = function(groups) {}

/**
 * Number of seconds Node.js has been running.
 */
process.uptime = function() {}

/**
 * A property exposing version strings of Node.js and its dependencies.
 */
process.versions = 0;

/** @__local__ */ process.__events__ = {};

/**
 * This event is emitted when Node.js empties its event loop and has
 * nothing else  to schedule. Normally, Node.js exits when there is no work
 * scheduled, but a  listener for &#39;beforeExit&#39; can make
 * asynchronous calls, and cause Node.js to  continue. &#39;beforeExit&#39;
 * is not emitted for conditions causing explicit termination, such  as
 * [process.exit()][] or uncaught exceptions, and should not be used as an
 * alternative to the &#39;exit&#39; event unless the intention is to
 * schedule more work.
 */
process.__events__.beforeExit = function() {};

/**
 * Emitted when the process is about to exit. There is no way to prevent
 * the exiting of the event loop at this point, and once all &#39;exit&#39;
 * listeners have finished running the process will exit. Therefore you
 * must only perform synchronous operations in this handler. This is a good
 * hook to perform checks on the module&#39;s state (like for unit tests).
 * The callback takes one argument, the code the process is exiting with.
 * This event is only emitted when Node.js exits explicitly by
 * process.exit() or implicitly by the event loop draining. Example of
 * listening for &#39;exit&#39;:
 */
process.__events__.exit = function() {};

/**
 * Messages sent by [ChildProcess.send()][] are obtained using the
 * &#39;message&#39; event on the child&#39;s process object.
 */
process.__events__.message = function() {};

/**
 * Emitted whenever a Promise was rejected and an error handler was
 * attached to it (for example with .catch()) later than after an event
 * loop turn. This event is emitted with the following arguments: p the
 * promise that was previously emitted in an &#39;unhandledRejection&#39;
 * event, but which has now gained a rejection handler. There is no notion
 * of a top level for a promise chain at which rejections can always be
 * handled. Being inherently asynchronous in nature, a promise rejection
 * event loop turn it takes for the &#39;unhandledRejection&#39; event to
 * be emitted. Another way of stating this is that, unlike in synchronous
 * code where there is an ever-growing list of unhandled exceptions, with
 * promises there is a growing-and-shrinking list of unhandled rejections.
 * In synchronous code, the &#39;uncaughtException&#39; event tells you
 * when the list of unhandled exceptions grows. And in asynchronous code,
 * the &#39;unhandledRejection&#39; event tells you when the list of
 * unhandled rejections grows, while the &#39;rejectionHandled&#39; event
 * tells you when the list of unhandled rejections shrinks. For example
 * using the rejection detection hooks in order to keep a map of all the
 * rejected promise reasons at a given time: This map will grow and shrink
 * over time, reflecting rejections that start unhandled and then become
 * handled. You could record the errors in some error log, either
 * periodically (probably best for long-running programs, allowing you to
 * clear the map, which in the case of a very buggy program could grow
 * indefinitely) or upon process exit (more convenient for scripts).
 */
process.__events__.rejectionHandled = function() {};

/**
 * The &#39;uncaughtException&#39; event is emitted when an exception
 * bubbles all the way back to the event loop. By default, Node.js handles
 * such exceptions by  printing the stack trace to stderr and exiting.
 * Adding a handler for the &#39;uncaughtException&#39; event overrides
 * this default behavior. For example:
 * @param err {Error}
 */
process.__events__.uncaughtException = function(err) {};

/**
 * Emitted whenever a Promise is rejected and no error handler is attached
 * to the promise within a turn of the event loop. When programming with
 * promises exceptions are encapsulated as rejected promises. Such promises
 * can be caught and handled using [promise.catch(...)][] and rejections
 * are propagated through a promise chain. This event is useful for
 * detecting and keeping track of promises that were rejected whose
 * rejections were not handled yet. This event is emitted with the
 * following arguments: reason the object with which the promise was
 * rejected (usually an  [Error][] instance). p the promise that was
 * rejected. Here is an example that logs every unhandled rejection to the
 * console For example, here is a rejection that will trigger the
 * &#39;unhandledRejection&#39; event: Here is an example of a coding
 * pattern that will also trigger &#39;unhandledRejection&#39;: In cases
 * like this, you may not want to track the rejection as a developer error
 * like you would for other &#39;unhandledRejection&#39; events. To address
 * this, you can either attach a dummy .catch(() =&gt; { }) handler to
 * resource.loaded, preventing the &#39;unhandledRejection&#39; event from
 * being emitted, or you can use the [&#39;rejectionHandled&#39;][] event.
 */
process.__events__.unhandledRejection = function() {};

/* required for stdin/stdout/stderr */
var tty = require('tty');

exports = process;

