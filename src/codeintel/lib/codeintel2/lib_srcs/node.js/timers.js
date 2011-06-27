/**
 * To schedule execution of callback after delay milliseconds. Returns a
 * timeoutId for possible use with clearTimeout(). Optionally, you can also
 * pass arguments to the callback.
 */
var timers = {};

/**
 * To schedule the repeated execution of callback every delay milliseconds.
 * Returns a intervalId for possible use with clearInterval(). Optionally,
 * you can also pass arguments to the callback.
 * @param [...]
 * @param [arg]
 * @param callback
 * @param delay
 */
timers.setInterval = function(callback, delay, arg) {}

/**
 * To schedule execution of callback after delay milliseconds. Returns a
 * timeoutId for possible use with clearTimeout(). Optionally, you can also
 * pass arguments to the callback.
 * @param [...]
 * @param [arg]
 * @param callback
 * @param delay
 */
timers.setTimeout = function(callback, delay, arg) {}

/**
 * Prevents a timeout from triggering.
 * @param timeoutId
 */
timers.clearTimeout = function(timeoutId) {}

/**
 * Stops a interval from triggering.
 * @param intervalId
 */
timers.clearInterval = function(intervalId) {}


exports = timers;

