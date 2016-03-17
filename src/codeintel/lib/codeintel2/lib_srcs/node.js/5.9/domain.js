/**
 * This module is pending deprecation. Once a replacement API has been
 * finalized, this module will be fully deprecated. Most end users should
 * not have cause to use this module. Users who absolutely must have the
 * functionality that domains provide may rely on it for the time being but
 * should expect to have to migrate to a different solution in the future.
 */
var domain = {};

/**
 * Returns a new Domain object.
 * @returns {domain.Domain} a new Domain object
 */
domain.create = function() {}

/**
 * The Domain class encapsulates the functionality of routing errors and
 * uncaught exceptions to the active Domain object.
 * @constructor
 */
domain.Domain = function() {}

/**
 * Run the supplied function in the context of the domain, implicitly
 * binding all event emitters, timers, and lowlevel requests that are
 * created in that context. Optionally, arguments can be passed to the
 * function.
 * @param fn {Function}
 * @param arg
 */
domain.Domain.prototype.run = function(fn, arg) {}

/**
 * Explicitly adds an emitter to the domain. If any event handlers called
 * by the emitter throw an error, or if the emitter emits an
 * &#39;error&#39; event, it will be routed to the domain&#39;s
 * &#39;error&#39; event, just like with implicit binding.
 * @param emitter {EventEmitter|Timer}
 */
domain.Domain.prototype.add = function(emitter) {}

/**
 * The opposite of [domain.add(emitter)][]. Removes domain handling from
 * the specified emitter.
 * @param emitter {EventEmitter|Timer}
 */
domain.Domain.prototype.remove = function(emitter) {}

/**
 * The returned function will be a wrapper around the supplied callback
 * function. When the returned function is called, any errors that are
 * thrown will be routed to the domain&#39;s &#39;error&#39; event.
 * @param callback {Function}
 * @returns The bound function
 */
domain.Domain.prototype.bind = function(callback) {}

/**
 * This method is almost identical to [domain.bind(callback)][]. However,
 * in addition to catching thrown errors, it will also intercept [Error][]
 * objects sent as the first argument to the function.
 * @param callback {Function}
 * @returns The intercepted function
 */
domain.Domain.prototype.intercept = function(callback) {}

/**
 * The enter method is plumbing used by the run, bind, and intercept
 * methods to set the active domain. It sets domain.active and
 * process.domain to the domain, and implicitly pushes the domain onto the
 * domain stack managed by the domain module (see [domain.exit()][] for
 * details on the domain stack). The call to enter delimits the beginning
 * of a chain of asynchronous calls and I/O operations bound to a domain.
 */
domain.Domain.prototype.enter = function() {}

/**
 * The exit method exits the current domain, popping it off the domain
 * stack.
 */
domain.Domain.prototype.exit = function() {}

/**
 */
domain.Domain.prototype.dispose = function() {}

/**
 * An array of timers and event emitters that have been explicitly added to
 * the domain.
 */
domain.Domain.prototype.members = 0;

exports = domain;

