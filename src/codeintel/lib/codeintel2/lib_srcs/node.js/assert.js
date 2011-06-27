/**
 * This module is used for writing unit tests for your applications, you
 * can access it with require('assert').
 */
var assert = {};

/**
 * Tests shallow, coercive non-equality with the not equal comparison
 * operator ( != ).
 * @param [message]
 * @param actual
 * @param expected
 */
assert.notEqual = function(actual, expected, message) {}

/**
 * Expects block not to throw an error, see assert.throws for details.
 * @param [error]
 * @param [message]
 * @param block
 */
assert.doesNotThrow = function(block, error, message) {}

/**
 * Tests if value is a true value, it is equivalent to assert.equal(true,
 * value, message);
 * @param [message]
 * @param value
 */
assert.ok = function(value, message) {}

/**
 * Tests if value is not a false value, throws if it is a true value.
 * Useful when testing the first argument, error in callbacks.
 * @param value
 */
assert.ifError = function(value) {}

/**
 * Tests shallow, coercive equality with the equal comparison operator ( ==
 * ).
 * @param [message]
 * @param actual
 * @param expected
 */
assert.equal = function(actual, expected, message) {}

/**
 * Tests for any deep inequality.
 * @param [message]
 * @param actual
 * @param expected
 */
assert.notDeepEqual = function(actual, expected, message) {}

/**
 * Tests strict non-equality, as determined by the strict not equal
 * operator ( !== )
 * @param [message]
 * @param actual
 * @param expected
 */
assert.notStrictEqual = function(actual, expected, message) {}

/**
 * Tests if actual is equal to expected using the operator provided.
 * @param actual
 * @param expected
 * @param message
 * @param operator
 */
assert.fail = function(actual, expected, message, operator) {}

/**
 * Expects block to throw an error. error can be constructor, regexp or
 * validation function.
 * @param [error]
 * @param [message]
 * @param block
 */
assert.throws = function(block, error, message) {}

/**
 * Tests strict equality, as determined by the strict equality operator (
 * === )
 * @param [message]
 * @param actual
 * @param expected
 */
assert.strictEqual = function(actual, expected, message) {}

/**
 * Tests for deep equality.
 * @param [message]
 * @param actual
 * @param expected
 */
assert.deepEqual = function(actual, expected, message) {}


exports = assert;

