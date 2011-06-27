/**
 * Node provides a tri-directional popen(3) facility through the
 * ChildProcess class.
 */
var child_process = {};

/**
 * Launches a new process with the given command, with command line
 * arguments in args. If omitted, args defaults to an empty Array.
 * @param [options]
 * @param args=[]
 * @param command
 * @return child_process.ChildProcess
 */
child_process.spawn = function(command, args, options) {}

child_process.ChildProcess = function() {}
child_process.ChildProcess.prototype = {}
/**
 * Send a signal to the child process. If no argument is given, the process
 * will be sent 'SIGTERM'. See signal(7) for a list of available signals.
 * @param signal='SIGTERM'
 */
child_process.ChildProcess.prototype.kill = function(signal) {}
/**
 * A Writable Stream that represents the child process's stdin. Closing
 * this stream via end() often causes the child process to terminate.
 * @type stream.WritableStream
 */
child_process.ChildProcess.prototype.stdin = 0;
/**
 * The PID of the child process.
 */
child_process.ChildProcess.prototype.pid = 0;
/**
 * A Readable Stream that represents the child process's stderr.
 * @type stream.ReadableStream
 */
child_process.ChildProcess.prototype.stderr = 0;
/**
 * A Readable Stream that represents the child process's stdout.
 * @type stream.ReadableStream
 */
child_process.ChildProcess.prototype.stdout = 0;

/**
 * High-level way to execute a command as a child process, buffer the
 * output, and return it all in a callback.
 * @param [options]
 * @param callback
 * @param command
 * @return child_process.ChildProcess
 */
child_process.exec = function(command, options, callback) {}


                /* used for giving types to ChildProcess.std* */
                var stream = require('stream');
                exports = child_process;

