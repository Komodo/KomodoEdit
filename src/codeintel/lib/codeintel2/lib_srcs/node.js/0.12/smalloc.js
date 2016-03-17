/**
 */
var smalloc = {};

/**
 * Buffers are backed by a simple allocator that only handles the
 * assignation of external raw memory. Smalloc exposes that functionality.
 * @constructor
 */
smalloc.smalloc = function() {}

/**
 * Returns receiver with allocated external array data. If no receiver is
 * passed then a new Object will be created and returned.
 * @param length {Number}
 * @param receiver=`new Object` {Object}
 * @param type=`Uint8` {Enum}
 * @returns receiver with allocated external array data
 */
smalloc.smalloc.prototype.alloc = function(length, receiver, type) {}

/**
 * Free memory that has been allocated to an object via smalloc.alloc.
 * @param obj
 */
smalloc.smalloc.prototype.dispose = function(obj) {}

/**
 * Returns true if the obj has externally allocated memory.
 * @param obj {Object}
 * @returns true if the obj has externally allocated memory
 */
smalloc.smalloc.prototype.hasExternalData = function(obj) {}

/**
 * Size of maximum allocation. This is also applicable to Buffer creation.
 */
smalloc.smalloc.prototype.kMaxLength = 0;

/**
 * Enum of possible external array types. Contains:
 */
smalloc.smalloc.prototype.Types = 0;

exports = smalloc;

