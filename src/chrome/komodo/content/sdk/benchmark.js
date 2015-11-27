/**
 * @copyright (c) 2015 ActiveState Software Inc.
 * @license Mozilla Public License v. 2.0
 * @author ActiveState
 * @overview -
 */

/**
 * Benchmark APIs -- wraps around the XPCOM koIBenchmark service.
 */
const {Cc, Ci} = require("chrome");

var koBenchmark = Cc["@activestate.com/koBenchmark;1"].getService(Ci.koIBenchmark);

/**
 * Benchmarking methods helpful for debugging, this library is mostly
 * succeeded by the [console] SDK
 *
 * @module ko/benchmark
 */

/**
 * Records the start time for the given event name.
 *
 * @param {String} name
 */
exports.startTiming = function(name) {
    return koBenchmark.startTiming(name);
}

/**
 * Records the end time for the given event name. Must have a matching startTiming call.
 *
 * @param {String} name
 */
exports.endTiming = function(name) {
    return koBenchmark.endTiming(name)
}

/**
 * Reports that the given event took the given time duration.
 *
 * @param {String} name
 * @param {Int} duration
 */
exports.addTiming = function(name, duration) {
    return koBenchmark.addTiming(name, duration);
}

/**
 * Reports an event occurred (at the current time).
 *
 * @param {String} name
 */
exports.addEvent = function(name) {
    return koBenchmark.addEvent(name);
}

/**
 * Accumulate the number of calls and duration for this name.
 *
 * @param {String} name
 * @param {Int} duration
 */
exports.accumulate = function(name, duration) {
    return koBenchmark.accumulate(name, duration);
}

/**
 * Reports an event occurred at the given time.
 *
 * @param {String} name
 * @param {Int} t
 */
exports.addEventAtTime = function(name, t) {
    return koBenchmark.addEventAtTime(name, t);
}

/**
 * Dump current benchmark results to stdout.
 */
exports.display = function() {
    return koBenchmark.display();
}
