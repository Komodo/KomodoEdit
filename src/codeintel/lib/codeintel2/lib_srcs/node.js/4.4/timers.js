/**
 * All of the timer functions are globals. You do not need to require()
 * this module in order to use them.
 */
var timers = {};

/**
 * To schedule the repeated execution of callback every delay milliseconds.
 * @param callback
 * @param delay
 * @param arg
 */
timers.setInterval = function(callback, delay, arg) {}

/**
 * To schedule execution of a one-time callback after delay milliseconds.
 * @param callback
 * @param delay
 * @param arg
 */
timers.setTimeout = function(callback, delay, arg) {}

/**
 * Prevents a timeout from triggering.
 * @param timeoutObject
 */
timers.clearTimeout = function(timeoutObject) {}

/**
 * Stops an interval from triggering.
 * @param intervalObject
 */
timers.clearInterval = function(intervalObject) {}

/**
 * Stops an immediate from triggering.
 * @param immediateObject
 */
timers.clearImmediate = function(immediateObject) {}

/**
 * If you had previously unref()d a timer you can call ref() to explicitly
 * request the timer hold the program open. If the timer is already refd
 * calling ref again will have no effect.
 */
timers.ref = function() {}

/**
 * To schedule the "immediate" execution of callback after I/O events
 * callbacks and before [setTimeout][] and [setInterval][]. Returns an
 * immediateObject for possible use with clearImmediate(). Optionally you
 * can also pass arguments to the callback.
 * @param callback
 * @param arg
 * @returns an immediateObject for possible use with clearImmediate()
 */
timers.setImmediate = function(callback, arg) {}

/**
 * The opaque value returned by [setTimeout][] and [setInterval][] also has
 * the method timer.unref() which will allow you to create a timer that is
 * active but if it is the only item left in the event loop, it won&#39;t
 * keep the program running. If the timer is already unrefd calling unref
 * again will have no effect.
 */
timers.unref = function() {}

exports = timers;

