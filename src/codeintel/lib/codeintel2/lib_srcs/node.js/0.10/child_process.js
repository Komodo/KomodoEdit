/**
 * Node provides a tri-directional popen(3) facility through the
 * child_process module.
 */
var child_process = {};

/**
 * Launches a new process with the given command, with command line
 * arguments in args.
 * @param command {String}
 * @param args {Array}
 * @param options {Object}
 * @returns {child_process.ChildProcess}
 */
child_process.spawn = function(command, args, options) {}

/**
 * As a shorthand, the stdio argument may also be one of the following
 * strings:
 */
spawn.stdio = 0;

/**
 * If the detached option is set, the child process will be made the leader
 * of a new process group. This makes it possible for the child to continue
 * running  after the parent exits.
 */
spawn.detached = 0;

/**
 * There is a deprecated option called customFds which allows one to
 * specify specific file descriptors for the stdio of the child process.
 * This API was not portable to all platforms and therefore removed.
 */
spawn.customFds = 0;

/**
 * ChildProcess is an [EventEmitter][].
 * @constructor
 */
child_process.ChildProcess = function() {}
child_process.ChildProcess.prototype = new events.EventEmitter();

/**
 * Send a signal to the child process. If no argument is given, the process
 * will be sent &#39;SIGTERM&#39;. See signal(7) for a list of available
 * signals.
 * @param signal='SIGTERM' {String}
 */
child_process.ChildProcess.prototype.kill = function(signal) {}

/**
 * A Writable Stream that represents the child process&#39;s stdin.
 * @type {stream.WritableStream}
 */
child_process.ChildProcess.prototype.stdin = 0;

/**
 * The PID of the child process.
 */
child_process.ChildProcess.prototype.pid = 0;

/**
 * A Readable Stream that represents the child process&#39;s stderr.
 * @type {stream.ReadableStream}
 */
child_process.ChildProcess.prototype.stderr = 0;

/**
 * A Readable Stream that represents the child process&#39;s stdout.
 * @type {stream.ReadableStream}
 */
child_process.ChildProcess.prototype.stdout = 0;

/**
 * If .connected is false, it is no longer possible to send messages.
 */
child_process.ChildProcess.prototype.connected = 0;

/**
 * Close the IPC channel between parent and child, allowing the child to
 * exit gracefully once there are no other connections keeping it alive.
 * After calling this method the .connected flag will be set to false in
 * both the parent and child, and it is no longer possible to send
 * messages.
 */
child_process.ChildProcess.prototype.disconnect = function() {}

/**
 * When using child_process.fork() you can write to the child using
 * child.send(message, [sendHandle]) and messages are received by a
 * &#39;message&#39; event on the child.
 * @param message {Object}
 * @param sendHandle {Handle}
 */
child_process.ChildProcess.prototype.send = function(message, sendHandle) {}

/**
 * A sparse array of pipes to the child process, corresponding with
 * positions in the stdio option to spawn that have been set to
 * &#39;pipe&#39;.
 */
child_process.ChildProcess.prototype.stdio = 0;

/** @__local__ */ child_process.ChildProcess.__events__ = {};

/**
 * Emitted when: The process could not be spawned, or The process could not
 * be killed, or Sending a message to the child process failed for whatever
 * reason. Note that the exit-event may or may not fire after an error has
 * occured. If you are listening on both events to fire a function,
 * remember to guard against calling your function twice. See also
 * ChildProcess#kill() and ChildProcess#send().
 */
child_process.ChildProcess.__events__.error = function() {};

/**
 * This event is emitted after the child process ends. If the process
 * terminated normally, code is the final exit code of the process,
 * otherwise null. If the process terminated due to receipt of a signal,
 * signal is the string name of the signal, otherwise null. Note that the
 * child process stdio streams might still be open. Also, note that node
 * establishes signal handlers for &#39;SIGINT&#39; and &#39;SIGTERM&#39;,
 * so it will not terminate due to receipt of those signals, it will exit.
 * See waitpid(2).
 * @param code=null {Number}
 * @param signal=null {String}
 */
child_process.ChildProcess.__events__.exit = function(code, signal) {};

/**
 * This event is emitted when the stdio streams of a child process have all
 * terminated. This is distinct from &#39;exit&#39;, since multiple
 * processes might share the same stdio streams.
 */
child_process.ChildProcess.__events__.close = function() {};

/**
 * This event is emitted after calling the .disconnect() method in the
 * parent or in the child. After disconnecting it is no longer possible to
 * send messages, and the .connected property is false.
 */
child_process.ChildProcess.__events__.disconnect = function() {};

/**
 * Messages send by .send(message, [sendHandle]) are obtained using the
 * message event.
 */
child_process.ChildProcess.__events__.message = function() {};

/**
 * Runs a command in a shell and buffers the output.
 * @param command {String}
 * @param options {Object}
 * @param callback {Function}
 * @returns {child_process.ChildProcess} ChildProcess object
 */
child_process.exec = function(command, options, callback) {}

/**
 * This is similar to child_process.exec() except it does not execute a
 * subshell but rather the specified file directly. This makes it slightly
 * leaner than child_process.exec. It has the same options.
 * @param file {String}
 * @param args {Array}
 * @param options {Object}
 * @param callback {Function}
 * @returns {child_process.ChildProcess} ChildProcess object
 */
child_process.execFile = function(file, args, options, callback) {}

/**
 * This is a special case of the spawn() functionality for spawning Node
 * processes. In addition to having all the methods in a normal
 * ChildProcess instance, the returned object has a communication channel
 * built-in. See child.send(message, [sendHandle]) for details.
 * @param modulePath {String}
 * @param args {Array}
 * @param options {Object}
 * @returns {child_process.ChildProcess} ChildProcess object
 */
child_process.fork = function(modulePath, args, options) {}

/* used for giving types to ChildProcess.std* */
var stream = require('stream');
var events = require('events');

exports = child_process;

