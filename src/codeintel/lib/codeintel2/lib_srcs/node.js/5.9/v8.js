/**
 * This module exposes events and interfaces specific to the version of
 * [V8][] built with Node.js. These interfaces are subject to change by
 * upstream and are therefore not covered under the stability index.
 */
var v8 = {};

/**
 * Returns an object with the following properties
 * @returns an object with the following properties
 */
v8.getHeapStatistics = function() {}

/**
 * Returns statistics about the V8 heap spaces, i.e. the segments which
 * make up the V8 heap. Order of heap spaces nor availability of a heap
 * space can be guaranteed as the statistics are provided via the V8
 * GetHeapSpaceStatistics function.
 * @returns statistics about the V8 heap spaces, i.e
 */
v8.getHeapSpaceStatistics = function() {}

/**
 * Set additional V8 command line flags. Use with care; changing settings
 * after the VM has started may result in unpredictable behavior, including
 * crashes and data loss. Or it may simply do nothing.
 * @param string
 */
v8.setFlagsFromString = function(string) {}

exports = v8;

