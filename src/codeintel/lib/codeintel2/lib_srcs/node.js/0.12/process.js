
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
 */
process.nextTick = function(callback) {}

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
 * Returns an object describing the memory usage of the Node process
 * measured in bytes.
 * @returns an object describing the memory usage of the Node process measured in bytes
 */
process.memoryUsage = function() {}

/**
 * Send a signal to a process. pid is the process id and signal is the
 * string describing the signal to send. Signal names are strings like
 * &#39;SIGINT&#39; or &#39;SIGHUP&#39;. If omitted, the signal will be
 * &#39;SIGTERM&#39;.
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
 * Getter/setter to set what is displayed in &#39;ps&#39;.
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
 * This causes node to emit an abort. This will cause node to exit and
 * generate a core file.
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
 * options that were used to compile the current node executable. This is
 * the same as the "config.gypi" file that was produced when running the
 * ./configure script.
 */
process.config = 0;

/**
 * This is the set of node-specific command line options from the
 * executable that started the process. These options do not show up in
 * process.argv, and do not include the node executable, the name of the
 * script, or any options following the script name. These options are
 * useful in order to spawn child processes with the same execution
 * environment as the parent.
 */
process.execArgv = 0;

/**
 * A number which will be the process exit code, when the process either
 * exits gracefully, or is exited via process.exit() without specifying a
 * code.
 * @type {Number}
 */
process.exitCode = 0;

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
 * Alternate way to retrieve require.main.
 */
process.mainModule = 0;

/**
 * Note: this function is only available on POSIX platforms (i.e. not
 * Windows, Android)
 * @param groups
 */
process.setgroups = function(groups) {}

/**
 * Number of seconds Node has been running.
 */
process.uptime = function() {}

/**
 * A property exposing version strings of node and its dependencies.
 */
process.versions = 0;

/** @__local__ */ process.__events__ = {};

/**
 * Emitted when the process is about to exit. There is no way to prevent
 * the exiting of the event loop at this point, and once all exit listeners
 * have finished running the process will exit. Therefore you must only
 * perform synchronous operations in this handler. This is a good hook to
 * perform checks on the module&#39;s state (like for unit tests). The
 * callback takes one argument, the code the process is exiting with.
 * Example of listening for exit:
 */
process.__events__.exit = function() {};

/**
 * This event is emitted when node empties it&#39;s event loop and has
 * nothing else to schedule. Normally, node exits when there is no work
 * scheduled, but a listener for &#39;beforeExit&#39; can make asynchronous
 * calls, and cause node to continue. &#39;beforeExit&#39; is not emitted
 * for conditions causing explicit termination, such as process.exit() or
 * uncaught exceptions, and should not be used as an alternative to the
 * &#39;exit&#39; event unless the intention is to schedule more work.
 */
process.__events__.beforeExit = function() {};

/**
 * Emitted when an exception bubbles all the way back to the event loop. If
 * a listener is added for this exception, the default action (which is to
 * print a stack trace and exit) will not occur. Example of listening for
 * uncaughtException: Note that uncaughtException is a very crude mechanism
 * for exception handling. Don&#39;t use it, use domains instead. If you do
 * use it, restart your application after every unhandled exception! Do not
 * use it as the node.js equivalent of On Error Resume Next. An unhandled
 * exception means your application - and by extension node.js itself - is
 * in an undefined state. Blindly resuming means anything could happen.
 * Think of resuming as pulling the power cord when you are upgrading your
 * system. Nine out of ten times nothing happens - but the 10th time, your
 * system is bust. You have been warned.
 * @param err {Error}
 */
process.__events__.uncaughtException = function(err) {};

/* required for stdin/stdout/stderr */
var tty = require('tty');

exports = process;

