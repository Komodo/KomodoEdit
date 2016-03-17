/**
 * The child_process module provides the ability to spawn child processes
 * in a manner that is similar, but not identical, to [popen(3)][]. This
 * capability is primarily provided by the child_process.spawn() function:
 */
var child_process = {};

/**
 * Instances of the ChildProcess class are [EventEmitters][] that represent
 * spawned child processes.
 * @constructor
 */
child_process.ChildProcess = function() {}
child_process.ChildProcess.prototype = new events.EventEmitter();

/**
 * The child.kill() methods sends a signal to the child process. If no
 * argument is given, the process will be sent the &#39;SIGTERM&#39;
 * signal. See signal(7) for a list of available signals.
 * @param signal='SIGTERM' {String}
 */
child_process.ChildProcess.prototype.kill = function(signal) {}

/**
 * A Writable Stream that represents the child process&#39;s stdin.
 * @type {stream.WritableStream}
 */
child_process.ChildProcess.prototype.stdin = 0;

/**
 * Returns the process identifier (PID) of the child process.
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
 * The child.connected property indicates whether it is still possible to
 * send and receive messages from a child process. When child.connected is
 * false, it is no longer possible to send or receive messages.
 */
child_process.ChildProcess.prototype.connected = 0;

/**
 * Closes the IPC channel between parent and child, allowing the child to
 * exit gracefully once there are no other connections keeping it alive.
 * After calling this method the child.connected and process.connected
 * properties in both the parent and child (respectively) will be set to
 * false, and it will be no longer possible to pass messages between the
 * processes.
 */
child_process.ChildProcess.prototype.disconnect = function() {}

/**
 * When an IPC channel has been established between the parent and child (
 * i.e. when using [child_process.fork()][]), the child.send() method can
 * be used to send messages to the child process. When the child process is
 * a Node.js instance, these messages can be received via the
 * process.on(&#39;message&#39;) event.
 * @param message {Object}
 * @param sendHandle {Handle}
 * @param options {Object}
 * @param callback {Function}
 */
child_process.ChildProcess.prototype.send = function(message, sendHandle, options, callback) {}

/**
 * A sparse array of pipes to the child process, corresponding with
 * positions in the [stdio][] option passed to [child_process.spawn()][]
 * that have been set to the value &#39;pipe&#39;. Note that
 * child.stdio[0], child.stdio[1], and child.stdio[2] are also available as
 * child.stdin, child.stdout, and child.stderr, respectively.
 */
child_process.ChildProcess.prototype.stdio = 0;

/** @__local__ */ child_process.ChildProcess.__events__ = {};

/**
 * The &#39;close&#39; event is emitted when the stdio streams of a child
 * process have been closed. This is distinct from the &#39;exit&#39;
 * event, since multiple processes might share the same stdio streams.
 */
child_process.ChildProcess.__events__.close = function() {};

/**
 * The &#39;disconnect&#39; event is emitted after calling the
 * ChildProcess.disconnect() method in the parent or child process. After
 * disconnecting it is no longer possible to send or receive messages, and
 * the ChildProcess.connected property is false.
 */
child_process.ChildProcess.__events__.disconnect = function() {};

/**
 * The &#39;error&#39; event is emitted whenever: The process could not be
 * spawned, or The process could not be killed, or Sending a message to the
 * child process failed. Note that the &#39;exit&#39; event may or may not
 * fire after an error has occurred. If you are listening to both the
 * &#39;exit&#39; and &#39;error&#39; events, it is important to guard
 * against accidentally invoking handler functions multiple times. See also
 * [ChildProcess#kill()][] and [ChildProcess#send()][].
 */
child_process.ChildProcess.__events__.error = function() {};

/**
 * The &#39;exit&#39; event is emitted after the child process ends. If the
 * process exited, code is the final exit code of the process, otherwise
 * null. If the process terminated due to receipt of a signal, signal is
 * the string name of the signal, otherwise null. One of the two will
 * always be non-null. Note that when the &#39;exit&#39; event is
 * triggered, child process stdio streams might still be open. Also, note
 * that Node.js establishes signal handlers for SIGINT and SIGTERM and
 * Node.js processes will not terminate immediately due to receipt of those
 * signals. Rather, Node.js will perform a sequence of cleanup actions and
 * then will re-raise the handled signal. See waitpid(2).
 * @param code=null {Number}
 * @param signal=null {String}
 */
child_process.ChildProcess.__events__.exit = function(code, signal) {};

/**
 * The &#39;message&#39; event is triggered when a child process uses
 * process.send() to send messages.
 */
child_process.ChildProcess.__events__.message = function() {};

/* used for giving types to ChildProcess.std* */
var stream = require('stream');
var events = require('events');

exports = child_process;

