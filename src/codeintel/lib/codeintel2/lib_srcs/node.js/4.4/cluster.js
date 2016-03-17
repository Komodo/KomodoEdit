/**
 * A single instance of Node.js runs in a single thread. To take advantage
 * of multi-core systems the user will sometimes want to launch a cluster
 * of Node.js processes to handle the load.
 * @base {events.EventEmitter}
 */
var cluster = {};

/**
 * Calls .disconnect() on each worker in cluster.workers.
 * @param callback {Function}
 */
cluster.disconnect = function(callback) {}

/**
 * Spawn a new worker process.
 * @param env {Object}
 */
cluster.fork = function(env) {}

/**
 * setupMaster is used to change the default &#39;fork&#39; behavior. Once
 * called, the settings will be present in cluster.settings.
 * @param settings {Object}
 */
cluster.setupMaster = function(settings) {}

/**
 * A Worker object contains all public information and method about a
 * worker.
 * @constructor
 */
cluster.Worker = function() {}
cluster.Worker.prototype = new events.EventEmitter();

/**
 * In a worker, this function will close all servers, wait for the
 * &#39;close&#39; event on those servers, and then disconnect the IPC
 * channel.
 */
cluster.Worker.prototype.disconnect = function() {}

/**
 * This function returns true if the worker is connected to its master via
 * its IPC channel, false otherwise. A worker is connected to its master
 * after it&#39;s been created. It is disconnected after the
 * &#39;disconnect&#39; event is emitted.
 */
cluster.Worker.prototype.isConnected = function() {}

/**
 * This function returns true if the worker&#39;s process has terminated
 * (either because of exiting or being signaled). Otherwise, it returns
 * false.
 */
cluster.Worker.prototype.isDead = function() {}

/**
 * This function will kill the worker. In the master, it does this by
 * disconnecting the worker.process, and once disconnected, killing with
 * signal. In the worker, it does it by disconnecting the channel, and then
 * exiting with code 0.
 * @param signal {String}
 */
cluster.Worker.prototype.kill = function(signal) {}

/**
 * Send a message to a worker or master, optionally with a handle.
 * @param message {Object}
 * @param sendHandle {Handle}
 * @param callback {Function}
 * @returns Boolean
 */
cluster.Worker.prototype.send = function(message, sendHandle, callback) {}

/**
 * Each new worker is given its own unique id, this id is stored in the id.
 */
cluster.Worker.prototype.id = 0;

/**
 * All workers are created using [child_process.fork()][], the returned
 * object from this function is stored as .process. In a worker, the global
 * process is stored.
 */
cluster.Worker.prototype.process = 0;

/**
 * Set by calling .kill() or .disconnect(), until then it is undefined.
 */
cluster.Worker.prototype.suicide = 0;

/** @__local__ */ cluster.Worker.__events__ = {};

/**
 * Similar to the cluster.on(&#39;disconnect&#39;) event, but specific to
 * this worker.
 */
cluster.Worker.__events__.disconnect = function() {};

/**
 * This event is the same as the one provided by [child_process.fork()][].
 * In a worker you can also use process.on(&#39;error&#39;).
 */
cluster.Worker.__events__.error = function() {};

/**
 * Similar to the cluster.on(&#39;exit&#39;) event, but specific to this
 * worker.
 */
cluster.Worker.__events__.exit = function() {};

/**
 * Similar to the cluster.on(&#39;listening&#39;) event, but specific to
 * this worker. It is not emitted in the worker.
 */
cluster.Worker.__events__.listening = function() {};

/**
 * Similar to the cluster.on(&#39;message&#39;) event, but specific to this
 * worker. This event is the same as the one provided by
 * [child_process.fork()][]. In a worker you can also use
 * process.on(&#39;message&#39;). As an example, here is a cluster that
 * keeps count of the number of requests in the master process using the
 * message system:
 */
cluster.Worker.__events__.message = function() {};

/**
 * Similar to the cluster.on(&#39;online&#39;) event, but specific to this
 * worker. It is not emitted in the worker.
 */
cluster.Worker.__events__.online = function() {};

/**
 * True if the process is a master. This is determined by the
 * process.env.NODE_UNIQUE_ID. If process.env.NODE_UNIQUE_ID is undefined,
 * then isMaster is true.
 */
cluster.isMaster = 0;

/**
 * True if the process is not a master (it is the negation of
 * cluster.isMaster).
 */
cluster.isWorker = 0;

/**
 * The scheduling policy, either cluster.SCHED_RR for round-robin or
 * cluster.SCHED_NONE to leave it to the operating system. This is a global
 * setting and effectively frozen once you spawn the first worker or call
 * cluster.setupMaster(), whatever comes first.
 */
cluster.schedulingPolicy = 0;

/**
 * After calling .setupMaster() (or .fork()) this settings object will
 * contain the settings, including the default values.
 */
cluster.settings = 0;

/**
 * A reference to the current worker object. Not available in the master
 * process.
 */
cluster.worker = 0;

/**
 * A hash that stores the active worker objects, keyed by id field. Makes
 * it easy to loop through all the workers. It is only available in the
 * master process.
 */
cluster.workers = 0;

var events = require('events');

exports = cluster;

